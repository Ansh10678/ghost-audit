from src.models.step import StepOperation, StepPhase
from src.rules.engine import RuleEngine


def test_user_profile_found():
    res = RuleEngine.evaluate(
        "account_service", "account_001", "USER_PROFILE", "FOUND", "evidence_54"
    )
    assert res.finding is not None
    assert res.finding.phase == StepPhase.FINDING
    assert res.finding.operation == StepOperation.REPORT_REMAINING_RECORD
    assert res.remediation is not None
    assert res.remediation.operation == StepOperation.DELETE_RECORD
    assert res.verification is not None
    assert res.verification.operation == StepOperation.VERIFY_RECORD_ABSENT


def test_support_message_identifiable():
    res = RuleEngine.evaluate(
        "support_platform", "support_101", "SUPPORT_MESSAGE", "IDENTIFIABLE", "evidence_28"
    )
    assert res.finding is not None
    assert res.finding.operation == StepOperation.REPORT_EXPOSED_PII
    assert res.remediation is not None
    assert res.remediation.operation == StepOperation.REDACT_RECORD
    assert res.verification is not None
    assert res.verification.operation == StepOperation.VERIFY_RECORD_REDACTED


def test_data_flow_active():
    res = RuleEngine.evaluate(
        "integration_service", "data_flow_01", "DATA_FLOW", "ACTIVE", "evidence_14"
    )
    assert res.finding is not None
    assert res.finding.operation == StepOperation.REPORT_ACTIVE_DATA_FLOW
    assert res.remediation is not None
    assert res.remediation.operation == StepOperation.DISABLE_DATA_FLOW
    assert res.verification is not None
    assert res.verification.operation == StepOperation.VERIFY_DATA_FLOW_DISABLED


def test_security_audit_log_present():
    res = RuleEngine.evaluate(
        "security_service", "audit_record_01", "SECURITY_AUDIT_LOG", "PRESENT", "evidence_38"
    )
    assert res.finding is None
    assert res.remediation is None
    assert res.verification is not None
    assert res.verification.operation == StepOperation.VERIFY_RECORD_PRESENT
