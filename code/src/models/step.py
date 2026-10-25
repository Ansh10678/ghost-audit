import json
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class StepPhase(str, Enum):
    FINDING = "FINDING"
    REMEDIATION = "REMEDIATION"
    VERIFICATION = "VERIFICATION"


class StepOperation(str, Enum):
    # Findings
    REPORT_REMAINING_RECORD = "REPORT_REMAINING_RECORD"
    REPORT_EXPOSED_PII = "REPORT_EXPOSED_PII"
    REPORT_ACTIVE_DATA_FLOW = "REPORT_ACTIVE_DATA_FLOW"
    REPORT_RESTORE_RISK = "REPORT_RESTORE_RISK"

    # Remediation
    DISABLE_DATA_FLOW = "DISABLE_DATA_FLOW"
    BLOCK_RESTORE = "BLOCK_RESTORE"
    DELETE_RECORD = "DELETE_RECORD"
    REDACT_RECORD = "REDACT_RECORD"
    ANONYMIZE_RECORD = "ANONYMIZE_RECORD"

    # Verification
    VERIFY_RECORD_ABSENT = "VERIFY_RECORD_ABSENT"
    VERIFY_RECORD_PRESENT = "VERIFY_RECORD_PRESENT"
    VERIFY_RECORD_REDACTED = "VERIFY_RECORD_REDACTED"
    VERIFY_RECORD_ANONYMIZED = "VERIFY_RECORD_ANONYMIZED"
    VERIFY_DATA_FLOW_DISABLED = "VERIFY_DATA_FLOW_DISABLED"
    VERIFY_RESTORE_BLOCKED = "VERIFY_RESTORE_BLOCKED"


class StepState(str, Enum):
    PRESENT = "PRESENT"
    ACTIVE = "ACTIVE"
    DISABLED = "DISABLED"
    BLOCKED = "BLOCKED"
    ABSENT = "ABSENT"
    REDACTED = "REDACTED"
    ANONYMIZED = "ANONYMIZED"


class DeletionStatus(str, Enum):
    COMPLETE = "COMPLETE"
    INCOMPLETE = "INCOMPLETE"
    NOT_APPLICABLE = "NOT_APPLICABLE"


# Canonical phase priority
PHASE_PRIORITY: dict[StepPhase, int] = {
    StepPhase.FINDING: 1,
    StepPhase.REMEDIATION: 2,
    StepPhase.VERIFICATION: 3,
}

# Canonical operation priority
OP_PRIORITY: dict[StepOperation, int] = {
    # Findings
    StepOperation.REPORT_REMAINING_RECORD: 1,
    StepOperation.REPORT_EXPOSED_PII: 2,
    StepOperation.REPORT_ACTIVE_DATA_FLOW: 3,
    StepOperation.REPORT_RESTORE_RISK: 4,
    # Remediation
    StepOperation.DISABLE_DATA_FLOW: 1,
    StepOperation.BLOCK_RESTORE: 2,
    StepOperation.DELETE_RECORD: 3,
    StepOperation.REDACT_RECORD: 4,
    StepOperation.ANONYMIZE_RECORD: 5,
    # Verification
    StepOperation.VERIFY_RECORD_ABSENT: 1,
    StepOperation.VERIFY_RECORD_PRESENT: 2,
    StepOperation.VERIFY_RECORD_REDACTED: 3,
    StepOperation.VERIFY_RECORD_ANONYMIZED: 4,
    StepOperation.VERIFY_DATA_FLOW_DISABLED: 5,
    StepOperation.VERIFY_RESTORE_BLOCKED: 6,
}


class AuditStep(BaseModel):
    step_no: int = Field(default=1)
    phase: StepPhase
    system_id: str
    resource_id: str
    operation: StepOperation
    state: StepState
    evidence_id: str = Field(default="")

    def to_dict(self) -> dict[str, Any]:
        return {
            "step_no": self.step_no,
            "phase": self.phase.value,
            "system_id": self.system_id,
            "resource_id": self.resource_id,
            "operation": self.operation.value,
            "state": self.state.value,
            "evidence_id": self.evidence_id,
        }


def step_sort_key(step: AuditStep) -> tuple[int, int, str, str]:
    return (
        PHASE_PRIORITY.get(step.phase, 99),
        OP_PRIORITY.get(step.operation, 99),
        step.system_id,
        step.resource_id,
    )


def sort_and_renumber_steps(steps: list[AuditStep]) -> list[AuditStep]:
    """
    Sorts steps according to canonical specifications:
    1. Phase order (FINDING -> REMEDIATION -> VERIFICATION)
    2. Operation order defined in problem_statement.md table
    3. system_id ascending
    4. resource_id ascending
    Deduplicates on (phase, system_id, resource_id, operation) and assigns consecutive step_no starting at 1.
    """
    if not steps:
        return []

    dedup: dict[tuple[str, str, str, str], AuditStep] = {}
    for s in steps:
        key = (s.phase.value, s.system_id, s.resource_id, s.operation.value)
        # Prefer retaining non-empty evidence_id if duplicate exists
        if key not in dedup or (not dedup[key].evidence_id and s.evidence_id):
            dedup[key] = s

    sorted_steps = sorted(dedup.values(), key=step_sort_key)

    for idx, s in enumerate(sorted_steps, start=1):
        s.step_no = idx

    return sorted_steps


class AuditDecision(BaseModel):
    case_id: str
    deletion_status: DeletionStatus
    steps: list[AuditStep] = Field(default_factory=list)

    def to_row(self) -> dict[str, str]:
        if self.deletion_status == DeletionStatus.NOT_APPLICABLE:
            steps_serialized = "[]"
        else:
            steps_list = [s.to_dict() for s in self.steps]
            steps_serialized = json.dumps(steps_list, separators=(",", ":"))
        return {
            "case_id": self.case_id,
            "deletion_status": self.deletion_status.value,
            "steps_json": steps_serialized,
        }
