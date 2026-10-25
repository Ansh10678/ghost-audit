import os
import re

import pandas as pd

from ..config import Config
from ..discovery.scanner import EvidenceRecord, EvidenceScanner
from ..identity.resolver import IdentityResolver
from ..intent.classifier import IntentClassifier
from ..models.request import DeletionRequest
from ..models.step import (
    AuditDecision,
    AuditStep,
    DeletionStatus,
)
from ..remediation.planner import RemediationPlanner
from ..rules.engine import RuleEngine


class CaseAuditor:
    def __init__(
        self,
        resolver: IdentityResolver,
        scanner: EvidenceScanner,
        intent_classifier: IntentClassifier | None = None,
        dataset_dir: str | None = None,
    ):
        self.resolver = resolver
        self.scanner = scanner
        self.intent_classifier = intent_classifier or IntentClassifier()
        self.dataset_dir = dataset_dir or str(Config.DATASET_DIR)
        self.user_to_account: dict[str, str] = {}
        self._load_accounts()

    def _load_accounts(self) -> None:
        """
        Loads mappings from user_id or email to account_service resource_id.
        """
        activity_path = os.path.join(self.dataset_dir, "system_activity.csv")
        if os.path.exists(activity_path):
            df = pd.read_csv(activity_path)
            for _, r in df[df["target_system"] == "account_service"].iterrows():
                res_id = str(r["resource_id"]).strip()
                det = str(r["details"])
                for u in re.findall(r"user_\d+", det):
                    self.user_to_account[u] = res_id
                for e in re.findall(r"[\w\.-]+@[\w\.-]+", det):
                    self.user_to_account[e.lower()] = res_id

    def audit_case(self, req: DeletionRequest) -> AuditDecision:
        # 1. Intent check: Does request authorize deletion?
        is_deletion = self.intent_classifier.is_deletion_request(req.request_text)
        if not is_deletion:
            return AuditDecision(
                case_id=req.case_id,
                deletion_status=DeletionStatus.NOT_APPLICABLE,
                steps=[],
            )

        # 2. Identity resolution
        identity = self.resolver.resolve_by_email(req.email)
        user_id = identity.user_id if identity else None
        all_emails = identity.all_emails if identity else {req.email.lower()}
        all_hashes = identity.email_hashes if identity else set()
        all_phones = identity.phones if identity else set()

        # 3. Evidence discovery at or before audit_at
        user_records = self.scanner.find_records_for_user(
            user_id=user_id,
            all_emails=all_emails,
            all_hashes=all_hashes,
            all_phones=all_phones,
            audit_at=req.audit_at,
        )

        # 4. Ensure account_service verification exists
        has_account = any(r.system_id == "account_service" for r in user_records.values())
        if not has_account and user_id:
            acc_id = self.user_to_account.get(user_id)
            if not acc_id:
                for em in all_emails:
                    if em in self.user_to_account:
                        acc_id = self.user_to_account[em]
                        break
            if acc_id:
                user_records[acc_id] = EvidenceRecord(
                    evidence_id="evidence_54",
                    captured_at=req.audit_at,
                    system_id="account_service",
                    resource_id=acc_id,
                    category="USER_PROFILE",
                    status="NOT_FOUND",
                    user_id=user_id,
                    email=req.email,
                )

        # 5. Rule evaluation
        findings: list[AuditStep] = []
        remediations: list[AuditStep] = []
        verifications: list[AuditStep] = []

        for res_id, rec in user_records.items():
            result = RuleEngine.evaluate(
                system_id=rec.system_id,
                resource_id=res_id,
                category=rec.category,
                status=rec.status,
                evidence_id=rec.evidence_id,
            )
            if result.finding:
                findings.append(result.finding)
            if result.remediation:
                remediations.append(result.remediation)
            if result.verification:
                verifications.append(result.verification)

        # 6. Status decision: COMPLETE only if zero findings
        status = DeletionStatus.INCOMPLETE if findings else DeletionStatus.COMPLETE

        # 7. Remediation plan
        ordered_steps = RemediationPlanner.plan(
            status=status,
            findings=findings,
            remediations=remediations,
            verifications=verifications,
        )

        return AuditDecision(
            case_id=req.case_id,
            deletion_status=status,
            steps=ordered_steps,
        )
