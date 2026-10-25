from pathlib import Path

import pandas as pd

from .config import Config
from .decision.auditor import CaseAuditor
from .discovery.scanner import EvidenceScanner
from .identity.resolver import IdentityResolver
from .intent.classifier import IntentClassifier
from .models.request import DeletionRequest


class AuditPipeline:
    def __init__(self, dataset_dir: str | None = None):
        self.dataset_dir = dataset_dir or str(Config.DATASET_DIR)
        print("Initializing AuditPipeline components...")
        self.resolver = IdentityResolver(self.dataset_dir)
        self.scanner = EvidenceScanner(self.dataset_dir)
        self.intent_classifier = IntentClassifier()

        print("Building Evidence Index across all multimodal stores...")
        self.scanner.build_index()
        print(f"Evidence index ready with {len(self.scanner.records)} indexed entries.")

        self.auditor = CaseAuditor(
            resolver=self.resolver,
            scanner=self.scanner,
            intent_classifier=self.intent_classifier,
            dataset_dir=self.dataset_dir,
        )

    def process_file(self, input_csv: str, output_csv: str) -> pd.DataFrame:
        print(f"Reading requests from: {input_csv}")
        df_in = pd.read_csv(input_csv)
        total_rows = len(df_in)
        print(f"Total requests to audit: {total_rows}")

        results: list[dict] = []
        for idx, row in df_in.iterrows():
            req = DeletionRequest(
                case_id=str(row["case_id"]).strip(),
                email=str(row["email"]).strip(),
                requested_at=str(row["requested_at"]).strip(),
                reported_status=str(row["reported_status"]).strip(),
                reported_at=str(row["reported_at"]).strip(),
                audit_at=str(row["audit_at"]).strip(),
                request_text=str(row.get("request_text", "")).strip(),
            )

            decision = self.auditor.audit_case(req)
            results.append(decision.to_row())

            if (idx + 1) % 50 == 0 or (idx + 1) == total_rows:
                print(f"Progress: [{idx + 1}/{total_rows}] cases processed.")

        # Build final DataFrame
        out_df = pd.DataFrame(results)

        # Sort by case_id
        out_df = out_df.sort_values("case_id").reset_index(drop=True)

        # Exact column order
        out_df = out_df[["case_id", "deletion_status", "steps_json"]]

        # Ensure parent directory exists
        out_path = Path(output_csv).resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Write output.csv with standard quoting
        out_df.to_csv(out_path, index=False, encoding="utf-8")
        print(f"Audit completed successfully! Saved {len(out_df)} rows to: {out_path}")
        return out_df
