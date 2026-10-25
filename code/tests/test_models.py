from src.models.step import AuditStep, StepOperation, StepPhase, StepState, sort_and_renumber_steps


def test_audit_step_model():
    step = AuditStep(
        step_no=1,
        phase=StepPhase.FINDING,
        system_id="account_service",
        resource_id="account_001",
        operation=StepOperation.REPORT_REMAINING_RECORD,
        state=StepState.PRESENT,
        evidence_id="evidence_54",
    )
    assert step.step_no == 1
    assert step.phase == StepPhase.FINDING
    d = step.to_dict()
    assert d["phase"] == "FINDING"
    assert d["operation"] == "REPORT_REMAINING_RECORD"
    assert d["state"] == "PRESENT"
    assert d["evidence_id"] == "evidence_54"


def test_canonical_sorting():
    steps = [
        AuditStep(
            step_no=99,
            phase=StepPhase.VERIFICATION,
            system_id="account_service",
            resource_id="account_001",
            operation=StepOperation.VERIFY_RECORD_ABSENT,
            state=StepState.ABSENT,
            evidence_id="evidence_54",
        ),
        AuditStep(
            step_no=99,
            phase=StepPhase.FINDING,
            system_id="account_service",
            resource_id="account_001",
            operation=StepOperation.REPORT_REMAINING_RECORD,
            state=StepState.PRESENT,
            evidence_id="evidence_54",
        ),
        AuditStep(
            step_no=99,
            phase=StepPhase.REMEDIATION,
            system_id="account_service",
            resource_id="account_001",
            operation=StepOperation.DELETE_RECORD,
            state=StepState.ABSENT,
            evidence_id="",
        ),
    ]

    sorted_steps = sort_and_renumber_steps(steps)
    assert len(sorted_steps) == 3
    assert sorted_steps[0].phase == StepPhase.FINDING
    assert sorted_steps[0].step_no == 1
    assert sorted_steps[1].phase == StepPhase.REMEDIATION
    assert sorted_steps[1].step_no == 2
    assert sorted_steps[2].phase == StepPhase.VERIFICATION
    assert sorted_steps[2].step_no == 3
