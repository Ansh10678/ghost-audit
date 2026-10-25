from ..discovery.scanner import EvidenceRecord
from ..models.step import AuditStep, StepOperation, StepPhase, StepState


class RecreationDetector:
    """
    Detects continuous synchronization paths and backup restore configurations
    that can repopulate or recreate deleted customer data.
    """

    @staticmethod
    def analyze_records(records: dict[str, EvidenceRecord]) -> list[AuditStep]:
        risk_steps: list[AuditStep] = []
        for res_id, rec in records.items():
            cat = rec.category.upper()
            stat = rec.status.upper()
            sys_id = rec.system_id

            if cat == "DATA_FLOW" or sys_id == "integration_service":
                if stat in ("ACTIVE", "ENABLED", "TRUE"):
                    risk_steps.append(
                        AuditStep(
                            phase=StepPhase.FINDING,
                            operation=StepOperation.REPORT_ACTIVE_DATA_FLOW,
                            system_id=sys_id,
                            resource_id=res_id,
                            state=StepState.ACTIVE,
                            evidence_id=rec.evidence_id,
                        )
                    )

            elif cat == "BACKUP_ARCHIVE" or sys_id == "backup_service":
                if stat in ("ACTIVE", "ALLOWED", "TRUE"):
                    risk_steps.append(
                        AuditStep(
                            phase=StepPhase.FINDING,
                            operation=StepOperation.REPORT_RESTORE_RISK,
                            system_id=sys_id,
                            resource_id=res_id,
                            state=StepState.ACTIVE,
                            evidence_id=rec.evidence_id,
                        )
                    )
        return risk_steps
