from typing import Any

from ..models.step import AuditStep, StepOperation, StepPhase, StepState


class RuleEvaluationResult:
    def __init__(
        self,
        finding: AuditStep | None = None,
        remediation: AuditStep | None = None,
        verification: AuditStep | None = None,
    ):
        self.finding = finding
        self.remediation = remediation
        self.verification = verification

    @property
    def is_violation(self) -> bool:
        return self.finding is not None


class RuleEngine:
    @staticmethod
    def evaluate(
        system_id: str,
        resource_id: str,
        category: str,
        status: str,
        evidence_id: str = "",
        details: dict[str, Any] | None = None,
    ) -> RuleEvaluationResult:
        """
        Maps (system_id, category, status) to finding, remediation, and verification steps.
        """
        details = details or {}
        cat = category.upper()
        stat = status.upper()

        # 1. USER_PROFILE, SEARCH_INDEX_ENTRY, USER_EXPORT, SUPPORT_ATTACHMENT, MARKETING_PROFILE
        if cat in (
            "USER_PROFILE",
            "SEARCH_INDEX_ENTRY",
            "USER_EXPORT",
            "SUPPORT_ATTACHMENT",
            "MARKETING_PROFILE",
            "CACHE_ENTRY",
            "SECONDARY_IDENTIFIER",
        ):
            if stat in ("FOUND", "PRESENT", "ACTIVE", "EXISTS"):
                return RuleEvaluationResult(
                    finding=AuditStep(
                        phase=StepPhase.FINDING,
                        operation=StepOperation.REPORT_REMAINING_RECORD,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.PRESENT,
                        evidence_id=evidence_id,
                    ),
                    remediation=AuditStep(
                        phase=StepPhase.REMEDIATION,
                        operation=StepOperation.DELETE_RECORD,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.ABSENT,
                        evidence_id="",
                    ),
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RECORD_ABSENT,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.ABSENT,
                        evidence_id=evidence_id,
                    ),
                )
            else:
                # Compliant absent record
                return RuleEvaluationResult(
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RECORD_ABSENT,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.ABSENT,
                        evidence_id=evidence_id,
                    )
                )

        # 2. SUPPORT_MESSAGE (Rule 5: REDACT)
        elif cat == "SUPPORT_MESSAGE":
            if stat in ("IDENTIFIABLE", "EXPOSED", "PRESENT", "FOUND"):
                return RuleEvaluationResult(
                    finding=AuditStep(
                        phase=StepPhase.FINDING,
                        operation=StepOperation.REPORT_EXPOSED_PII,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.PRESENT,
                        evidence_id=evidence_id,
                    ),
                    remediation=AuditStep(
                        phase=StepPhase.REMEDIATION,
                        operation=StepOperation.REDACT_RECORD,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.REDACTED,
                        evidence_id="",
                    ),
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RECORD_REDACTED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.REDACTED,
                        evidence_id=evidence_id,
                    ),
                )
            else:
                # Already redacted
                return RuleEvaluationResult(
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RECORD_REDACTED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.REDACTED,
                        evidence_id=evidence_id,
                    )
                )

        # 3. ANALYTICS_PROFILE / PRODUCT_TELEMETRY (Rule 7, 8: ANONYMIZE)
        elif cat in ("ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"):
            if stat in ("IDENTIFIABLE", "EXPOSED", "PRESENT", "FOUND"):
                return RuleEvaluationResult(
                    finding=AuditStep(
                        phase=StepPhase.FINDING,
                        operation=StepOperation.REPORT_EXPOSED_PII,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.PRESENT,
                        evidence_id=evidence_id,
                    ),
                    remediation=AuditStep(
                        phase=StepPhase.REMEDIATION,
                        operation=StepOperation.ANONYMIZE_RECORD,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.ANONYMIZED,
                        evidence_id="",
                    ),
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RECORD_ANONYMIZED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.ANONYMIZED,
                        evidence_id=evidence_id,
                    ),
                )
            else:
                # Compliant anonymized record
                return RuleEvaluationResult(
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RECORD_ANONYMIZED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.ANONYMIZED,
                        evidence_id=evidence_id,
                    )
                )

        # 4. ACCOUNT_TOMBSTONE (Rule 15: REDACT)
        elif cat == "ACCOUNT_TOMBSTONE":
            if stat in ("IDENTIFIABLE", "EXPOSED", "PRESENT"):
                return RuleEvaluationResult(
                    finding=AuditStep(
                        phase=StepPhase.FINDING,
                        operation=StepOperation.REPORT_EXPOSED_PII,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.PRESENT,
                        evidence_id=evidence_id,
                    ),
                    remediation=AuditStep(
                        phase=StepPhase.REMEDIATION,
                        operation=StepOperation.REDACT_RECORD,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.REDACTED,
                        evidence_id="",
                    ),
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RECORD_REDACTED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.REDACTED,
                        evidence_id=evidence_id,
                    ),
                )
            else:
                return RuleEvaluationResult(
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RECORD_REDACTED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.REDACTED,
                        evidence_id=evidence_id,
                    )
                )

        # 5. DATA_FLOW (Integration connector)
        elif cat in ("DATA_FLOW", "CONNECTOR"):
            if stat in ("ACTIVE", "ENABLED", "1", "TRUE"):
                return RuleEvaluationResult(
                    finding=AuditStep(
                        phase=StepPhase.FINDING,
                        operation=StepOperation.REPORT_ACTIVE_DATA_FLOW,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.ACTIVE,
                        evidence_id=evidence_id,
                    ),
                    remediation=AuditStep(
                        phase=StepPhase.REMEDIATION,
                        operation=StepOperation.DISABLE_DATA_FLOW,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.DISABLED,
                        evidence_id="",
                    ),
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_DATA_FLOW_DISABLED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.DISABLED,
                        evidence_id=evidence_id,
                    ),
                )
            else:
                return RuleEvaluationResult(
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_DATA_FLOW_DISABLED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.DISABLED,
                        evidence_id=evidence_id,
                    )
                )

        # 6. BACKUP_ARCHIVE (Rule 14: RETAIN with restore blocked)
        elif cat in ("BACKUP_ARCHIVE", "BACKUP"):
            if stat in ("ACTIVE", "ALLOWED", "1", "TRUE"):
                return RuleEvaluationResult(
                    finding=AuditStep(
                        phase=StepPhase.FINDING,
                        operation=StepOperation.REPORT_RESTORE_RISK,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.ACTIVE,
                        evidence_id=evidence_id,
                    ),
                    remediation=AuditStep(
                        phase=StepPhase.REMEDIATION,
                        operation=StepOperation.BLOCK_RESTORE,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.BLOCKED,
                        evidence_id="",
                    ),
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RESTORE_BLOCKED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.BLOCKED,
                        evidence_id=evidence_id,
                    ),
                )
            else:
                return RuleEvaluationResult(
                    verification=AuditStep(
                        phase=StepPhase.VERIFICATION,
                        operation=StepOperation.VERIFY_RESTORE_BLOCKED,
                        system_id=system_id,
                        resource_id=resource_id,
                        state=StepState.BLOCKED,
                        evidence_id=evidence_id,
                    )
                )

        # 7. SECURITY_AUDIT_LOG & LEGAL_HOLD_RECORD (Rule 12, 13: RETAIN)
        elif cat in ("SECURITY_AUDIT_LOG", "LEGAL_HOLD_RECORD", "AUDIT_RECORD"):
            return RuleEvaluationResult(
                verification=AuditStep(
                    phase=StepPhase.VERIFICATION,
                    operation=StepOperation.VERIFY_RECORD_PRESENT,
                    system_id=system_id,
                    resource_id=resource_id,
                    state=StepState.PRESENT,
                    evidence_id=evidence_id,
                )
            )

        # Default fallback
        return RuleEvaluationResult()
