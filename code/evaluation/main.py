import json
import os
import sys
from pathlib import Path

import pandas as pd

# Add code/ to sys.path
CODE_DIR = Path(__file__).resolve().parent.parent
if str(CODE_DIR) not in sys.path:
    sys.path.insert(0, str(CODE_DIR))

from src.config import Config
from src.llm.client import global_usage
from src.pipeline import AuditPipeline


def run_evaluation(dataset_dir: str | None = None) -> None:
    dataset_dir = dataset_dir or str(Config.DATASET_DIR)
    sample_input = os.path.join(dataset_dir, "sample_deletion_requests.csv")
    sample_output = os.path.join(dataset_dir, "sample_output.csv")

    if not os.path.exists(sample_input) or not os.path.exists(sample_output):
        print(f"Error: Sample files not found in {dataset_dir}")
        return

    print("=== Running Evaluation Suite on 32 Sample Cases ===")
    pipeline = AuditPipeline(dataset_dir=dataset_dir)

    temp_out = os.path.join(str(Config.CACHE_DIR), "eval_temp_output.csv")
    pred_df = pipeline.process_file(input_csv=sample_input, output_csv=temp_out)
    truth_df = pd.read_csv(sample_output)

    # Merge predictions with truth
    merged = pd.merge(pred_df, truth_df, on="case_id", suffixes=("_pred", "_true"))

    total_cases = len(merged)
    correct_status = 0
    confusion_matrix = {
        "COMPLETE": {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0},
        "INCOMPLETE": {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0},
        "NOT_APPLICABLE": {"COMPLETE": 0, "INCOMPLETE": 0, "NOT_APPLICABLE": 0},
    }

    total_truth_steps = 0
    total_pred_steps = 0
    matching_steps = 0
    sequence_matches = 0
    mismatches = []

    for _, row in merged.iterrows():
        cid = row["case_id"]
        p_stat = row["deletion_status_pred"]
        t_stat = row["deletion_status_true"]

        confusion_matrix[t_stat][p_stat] = confusion_matrix[t_stat].get(p_stat, 0) + 1

        if p_stat == t_stat:
            correct_status += 1

        p_steps = json.loads(row["steps_json_pred"])
        t_steps = json.loads(row["steps_json_true"])

        total_truth_steps += len(t_steps)
        total_pred_steps += len(p_steps)

        p_tuples = [
            (s["phase"], s["operation"], s["system_id"], s["resource_id"], s["state"])
            for s in p_steps
        ]
        t_tuples = [
            (s["phase"], s["operation"], s["system_id"], s["resource_id"], s["state"])
            for s in t_steps
        ]

        p_set = set(p_tuples)
        t_set = set(t_tuples)

        common = p_set & t_set
        matching_steps += len(common)

        if p_tuples == t_tuples:
            sequence_matches += 1
        else:
            mismatches.append(
                {
                    "case_id": cid,
                    "status_pred": p_stat,
                    "status_true": t_stat,
                    "missing": list(t_set - p_set),
                    "extra": list(p_set - t_set),
                }
            )

    status_acc = (correct_status / total_cases) * 100 if total_cases else 0.0
    step_recall = (matching_steps / total_truth_steps) * 100 if total_truth_steps else 0.0
    step_precision = (matching_steps / total_pred_steps) * 100 if total_pred_steps else 0.0
    step_f1 = (
        (2 * step_precision * step_recall / (step_precision + step_recall))
        if (step_precision + step_recall)
        else 0.0
    )
    seq_acc = (sequence_matches / total_cases) * 100 if total_cases else 0.0

    print("\n" + "=" * 50)
    print("EVALUATION METRICS SUMMARY")
    print("=" * 50)
    print(f"Total Cases: {total_cases}")
    print(
        f"Case-Level Deletion Status Accuracy: {correct_status}/{total_cases} ({status_acc:.1f}%)"
    )
    print(f"Step Precision: {matching_steps}/{total_pred_steps} ({step_precision:.1f}%)")
    print(f"Step Recall:    {matching_steps}/{total_truth_steps} ({step_recall:.1f}%)")
    print(f"Step F1 Score:  {step_f1:.1f}%")
    print(f"Exact Sequence Accuracy: {sequence_matches}/{total_cases} ({seq_acc:.1f}%)")
    print("-" * 50)
    print("Confusion Matrix (Rows: Ground Truth, Columns: Prediction):")
    print("               Pred COMPLETE  Pred INCOMPLETE  Pred NOT_APPLICABLE")
    for true_k in ("COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"):
        cm = confusion_matrix[true_k]
        print(
            f"True {true_k:<12}: {cm.get('COMPLETE', 0):<14} {cm.get('INCOMPLETE', 0):<16} {cm.get('NOT_APPLICABLE', 0)}"
        )
    print("=" * 50)

    # Write evaluation_report.md
    eval_report_path = CODE_DIR / "evaluation" / "evaluation_report.md"
    eval_report_content = f"""# Deletion Audit Agent Evaluation Report

## 1. Executive Summary
- **Case-Level Deletion Status Accuracy**: {status_acc:.1f}% ({correct_status}/{total_cases} sample cases)
- **Step-Level Precision**: {step_precision:.1f}% ({matching_steps}/{total_pred_steps} predicted steps)
- **Step-Level Recall**: {step_recall:.1f}% ({matching_steps}/{total_truth_steps} ground-truth steps)
- **Step-Level F1 Score**: {step_f1:.1f}%
- **Sequence Accuracy**: {seq_acc:.1f}% ({sequence_matches}/{total_cases} exact array matches)

## 2. Confusion Matrix
| Ground Truth \\ Prediction | Pred COMPLETE | Pred INCOMPLETE | Pred NOT_APPLICABLE |
|---|---|---|---|
| **True COMPLETE** | {confusion_matrix["COMPLETE"]["COMPLETE"]} | {confusion_matrix["COMPLETE"]["INCOMPLETE"]} | {confusion_matrix["COMPLETE"]["NOT_APPLICABLE"]} |
| **True INCOMPLETE** | {confusion_matrix["INCOMPLETE"]["COMPLETE"]} | {confusion_matrix["INCOMPLETE"]["INCOMPLETE"]} | {confusion_matrix["INCOMPLETE"]["NOT_APPLICABLE"]} |
| **True NOT_APPLICABLE** | {confusion_matrix["NOT_APPLICABLE"]["COMPLETE"]} | {confusion_matrix["NOT_APPLICABLE"]["INCOMPLETE"]} | {confusion_matrix["NOT_APPLICABLE"]["NOT_APPLICABLE"]} |

## 3. Custom Evaluation Cases Created by Participant
The following 3 synthetic test cases were designed and verified to stress-test edge-case boundaries:

### Custom Case 1: `custom_case_01` (Tombstone Anonymization & Partial Deletion)
- **Request**: Subject requested complete account erasure after previous support inquiries.
- **Scenario**: Database records were removed, but account tombstone in `identity_service` retained exposed phone and full name.
- **Expected Status**: `INCOMPLETE`
- **Expected Steps**: Finding of exposed PII on tombstone (`REPORT_EXPOSED_PII`), remediation (`REDACT_RECORD`), and verification of redaction (`VERIFY_RECORD_REDACTED`).

### Custom Case 2: `custom_case_02` (Active Connector Recreation Risk)
- **Request**: Deletion completed in customer profile database with status reported as `COMPLETE`.
- **Scenario**: An active connector in `integration_service` (`data_flow_sync_99`) remains enabled on a 6-hour cron schedule syncing marketing data.
- **Expected Status**: `INCOMPLETE`
- **Expected Steps**: Finding of active sync flow (`REPORT_ACTIVE_DATA_FLOW`), remediation (`DISABLE_DATA_FLOW`), and verification (`VERIFY_DATA_FLOW_DISABLED`).

### Custom Case 3: `custom_case_03` (Non-Deletion Access Request Trap)
- **Request**: User submitted query stating: "Je souhaite recevoir une copie de l'ensemble de mes données personnelles et factures conformément au RGPD article 15."
- **Scenario**: GDPR Article 15 Data Subject Access Request (DSAR / Export), NOT a deletion request (Article 17).
- **Expected Status**: `NOT_APPLICABLE`
- **Expected Steps**: `steps_json: []`

## 4. Failures Found and Improvements Made
1. **Trace Grouping in Telemetry Logs**:
   - *Failure*: Initial parsing treated individual log lines independently. When `lookup_key` appeared on an initiation event and `resource_id` on a completion event, identifiers were detached.
   - *Fix*: Implemented transaction trace grouping by `trace_id` / `requestId`, correlating all resources and identifiers within the execution context.
2. **Database Replicas Nested JSON Payloads**:
   - *Failure*: Regional SQL replica dumps stored attributes inside serialized `record_json` columns rather than relational fields.
   - *Fix*: Added dynamic JSON payload extraction, deserializing and indexing customer references and hashed credentials.
3. **Multi-Column Column Names**:
   - *Failure*: `backup_restore_entries` table in SQL dumps named columns `customer_email` and `customer_reference` rather than generic `email` and `user_id`.
   - *Fix*: Standardized column alias normalization across all database tables.
"""
    with open(eval_report_path, "w", encoding="utf-8") as f:
        f.write(eval_report_content)
    print(f"Saved evaluation report to: {eval_report_path}")

    # Write usage_report.md
    usage = global_usage.summary()
    usage_report_path = CODE_DIR / "evaluation" / "usage_report.md"
    usage_report_content = f"""# LLM & Token Usage Report

## 1. Overview
Summary of model invocations, token consumption, and cost estimates for the complete evaluation dataset run:

| Metric | Value |
|---|---|
| **Model Provider** | Google Cloud / Gemini API |
| **Model Name** | {Config.GEMINI_MODEL} |
| **Total Model Invocations** | {usage["call_count"]} |
| **Prompt Tokens** | {usage["prompt_tokens"]} |
| **Completion Tokens** | {usage["completion_tokens"]} |
| **Total Tokens** | {usage["total_tokens"]} |
| **Average Tokens per Request** | {round(usage["total_tokens"] / max(total_cases, 1), 1)} |
| **Estimated Total Cost (USD)** | ${usage["estimated_cost_usd"]:.4f} |
| **Estimated Cost per Request (USD)** | ${usage["estimated_cost_usd"] / max(total_cases, 1):.6f} |

## 2. Architecture Trade-offs
- **Deterministic Core**: In accordance with the system specification, 100% of identity graph resolution, evidence scanning, SQL/JSON parsing, rule evaluation, and step serialization are executed deterministically.
- **LLM Role**: LLMs are reserved for unstructured intent ambiguity resolution and multilingual request classification with on-disk caching, keeping token consumption minimal and deterministic.
"""
    with open(usage_report_path, "w", encoding="utf-8") as f:
        f.write(usage_report_content)
    print(f"Saved usage report to: {usage_report_path}")


if __name__ == "__main__":
    run_evaluation()
