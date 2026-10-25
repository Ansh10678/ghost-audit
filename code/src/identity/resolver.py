from pathlib import Path
from typing import Any

import pandas as pd

from ..config import Config
from ..models.identity import SubjectIdentity


class IdentityResolver:
    def __init__(
        self,
        dataset_dir_or_df: Any | None = None,
        audit_log_df: pd.DataFrame | None = None,
    ):
        if isinstance(dataset_dir_or_df, (str, Path)):
            dataset_dir = Path(dataset_dir_or_df)
            self.identities_df = pd.read_csv(dataset_dir / "user_identities.csv")
            self.audit_log_df = pd.read_csv(dataset_dir / "user_audit_log.csv")
        elif isinstance(dataset_dir_or_df, pd.DataFrame):
            self.identities_df = dataset_dir_or_df
            self.audit_log_df = (
                audit_log_df if audit_log_df is not None else pd.read_csv(Config.AUDIT_LOG_CSV)
            )
        else:
            self.identities_df = pd.read_csv(Config.IDENTITIES_CSV)
            self.audit_log_df = pd.read_csv(Config.AUDIT_LOG_CSV)

        self._build_indexes()

    def _build_indexes(self):
        # Email to user_id mapping
        self.email_to_user_id: dict[str, str] = {}
        self.user_records: dict[str, dict] = {}

        for _, row in self.identities_df.iterrows():
            uid = str(row["user_id"]).strip()
            self.user_records[uid] = row.to_dict()
            em = str(row["email"]).strip().lower()
            if em:
                self.email_to_user_id[em] = uid

        # Audit log index: old email -> user_id, and user_id -> changes
        self.historical_emails_by_user: dict[str, set] = {}
        self.historical_phones_by_user: dict[str, set] = {}
        self.historical_hashes_by_user: dict[str, set] = {}

        for _, row in self.audit_log_df.iterrows():
            uid = str(row["user_id"]).strip()
            field = str(row.get("field_name") or row.get("changed_field") or "").strip().lower()
            old_val = str(row["old_value"]).strip() if pd.notna(row.get("old_value")) else ""
            new_val = str(row["new_value"]).strip() if pd.notna(row.get("new_value")) else ""

            if field == "email":
                self.historical_emails_by_user.setdefault(uid, set())
                if old_val:
                    self.historical_emails_by_user[uid].add(old_val.lower())
                    if old_val.lower() not in self.email_to_user_id:
                        self.email_to_user_id[old_val.lower()] = uid
                if new_val:
                    self.historical_emails_by_user[uid].add(new_val.lower())
            elif field == "phone":
                self.historical_phones_by_user.setdefault(uid, set())
                if old_val:
                    self.historical_phones_by_user[uid].add(old_val)
                if new_val:
                    self.historical_phones_by_user[uid].add(new_val)
            elif field == "email_hash":
                self.historical_hashes_by_user.setdefault(uid, set())
                if old_val:
                    self.historical_hashes_by_user[uid].add(old_val)
                if new_val:
                    self.historical_hashes_by_user[uid].add(new_val)

    def resolve_by_email(self, email: str) -> SubjectIdentity | None:
        return self.resolve(email)

    def resolve(self, email: str) -> SubjectIdentity | None:
        if not email:
            return None
        norm_email = email.strip().lower()
        uid = self.email_to_user_id.get(norm_email)
        if not uid:
            # Fallback check
            for em, u in self.email_to_user_id.items():
                if em == norm_email:
                    uid = u
                    break
        if not uid:
            return None

        u_data = self.user_records.get(uid, {})
        curr_email = str(u_data.get("email", norm_email)).strip()
        name = str(u_data.get("name", "")).strip() if pd.notna(u_data.get("name")) else None
        curr_phone = str(u_data.get("phone", "")).strip() if pd.notna(u_data.get("phone")) else None
        curr_hash = (
            str(u_data.get("email_hash", "")).strip()
            if pd.notna(u_data.get("email_hash"))
            else None
        )

        phones = set(self.historical_phones_by_user.get(uid, set()))
        if curr_phone:
            phones.add(curr_phone)

        hist_emails = set(self.historical_emails_by_user.get(uid, set()))
        if norm_email:
            hist_emails.add(norm_email)
        hist_emails.discard(curr_email.lower())

        hashes = set(self.historical_hashes_by_user.get(uid, set()))
        if curr_hash:
            hashes.add(curr_hash)

        return SubjectIdentity(
            user_id=uid,
            name=name,
            current_email=curr_email,
            historical_emails=hist_emails,
            phones=phones,
            email_hashes=hashes,
        )
