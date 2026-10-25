import tempfile
from pathlib import Path

from src.models.request import DeletionRequest
from src.pipeline import AuditPipeline


def test_synthetic_pipeline_end_to_end():
    fixture_dir = Path(__file__).parent / "fixtures" / "synthetic_dataset"
    assert fixture_dir.exists(), f"Synthetic dataset directory not found at {fixture_dir}"

    # Initialize pipeline on synthetic dataset
    pipeline = AuditPipeline(dataset_dir=str(fixture_dir))

    # 1. Audit individual cases directly via auditor
    req_alice = DeletionRequest(
        case_id="case_syn_001",
        email="alice.smith@example.com",
        requested_at="2026-06-01T10:00:00Z",
        reported_status="COMPLETE",
        reported_at="2026-06-05T10:00:00Z",
        audit_at="2026-06-10T10:00:00Z",
        request_text="Please delete my account and erase all my personal data.",
    )
    res_alice = pipeline.auditor.audit_case(req_alice)
    assert (
        res_alice.deletion_status.value == "COMPLETE"
    ), f"Expected COMPLETE for Alice, got {res_alice.deletion_status}"

    req_bob = DeletionRequest(
        case_id="case_syn_002",
        email="bob.jones@example.com",
        requested_at="2026-06-01T10:00:00Z",
        reported_status="COMPLETE",
        reported_at="2026-06-05T10:00:00Z",
        audit_at="2026-06-10T10:00:00Z",
        request_text="I want my personal data deleted from all systems.",
    )
    res_bob = pipeline.auditor.audit_case(req_bob)
    assert (
        res_bob.deletion_status.value == "INCOMPLETE"
    ), f"Expected INCOMPLETE for Bob, got {res_bob.deletion_status}"
    assert len(res_bob.steps) > 0, "Expected findings/remediation steps for Bob"

    # Verify phases for Bob
    phases = [s.phase.value if hasattr(s.phase, "value") else s.phase for s in res_bob.steps]
    assert "FINDING" in phases
    assert "REMEDIATION" in phases
    assert "VERIFICATION" in phases

    req_charlie = DeletionRequest(
        case_id="case_syn_003",
        email="charlie.brown@example.com",
        requested_at="2026-06-01T10:00:00Z",
        reported_status="NOT_STARTED",
        reported_at="2026-06-05T10:00:00Z",
        audit_at="2026-06-10T10:00:00Z",
        request_text="Please stop the promotional emails. I still need the account and my order history, so I am not asking for deletion.",
    )
    res_charlie = pipeline.auditor.audit_case(req_charlie)
    assert (
        res_charlie.deletion_status.value == "NOT_APPLICABLE"
    ), f"Expected NOT_APPLICABLE for Charlie, got {res_charlie.deletion_status}"
    assert res_charlie.steps == [], "Steps must be empty for NOT_APPLICABLE"

    # 2. Test full process_file execution writing output CSV
    with tempfile.TemporaryDirectory() as tmpdir:
        out_csv = Path(tmpdir) / "output.csv"
        df_out = pipeline.process_file(
            input_csv=str(fixture_dir / "deletion_requests.csv"), output_csv=str(out_csv)
        )
        assert out_csv.exists()
        assert len(df_out) == 3
        assert list(df_out.columns) == ["case_id", "deletion_status", "steps_json"]
        assert df_out.iloc[0]["deletion_status"] == "COMPLETE"
        assert df_out.iloc[1]["deletion_status"] == "INCOMPLETE"
        assert df_out.iloc[2]["deletion_status"] == "NOT_APPLICABLE"
