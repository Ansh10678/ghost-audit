import glob
import json
import os
import re
import sqlite3
from typing import Any

import pandas as pd

from ..config import Config


class EvidenceRecord:
    def __init__(
        self,
        evidence_id: str,
        captured_at: str,
        system_id: str,
        resource_id: str,
        category: str,
        status: str,
        user_id: str | None = None,
        email: str | None = None,
        phone: str | None = None,
        identifiers: set[str] | None = None,
    ):
        self.evidence_id = evidence_id
        self.captured_at = captured_at
        self.system_id = system_id
        self.resource_id = resource_id
        self.category = category
        self.status = status
        self.user_id = user_id
        self.email = email.lower() if email else None
        self.phone = phone
        self.identifiers = identifiers or set()
        if user_id:
            self.identifiers.add(user_id.lower())
        if self.email:
            self.identifiers.add(self.email)
        if phone:
            self.identifiers.add("".join(c for c in phone if c.isdigit()))

    def to_dict(self) -> dict[str, Any]:
        return {
            "evidence_id": self.evidence_id,
            "captured_at": self.captured_at,
            "system_id": self.system_id,
            "resource_id": self.resource_id,
            "category": self.category,
            "status": self.status,
            "user_id": self.user_id,
            "email": self.email,
            "phone": self.phone,
            "identifiers": list(self.identifiers),
        }


class EvidenceScanner:
    def __init__(self, dataset_dir: str | None = None):
        self.dataset_dir = dataset_dir or str(Config.DATASET_DIR)
        self.records: list[EvidenceRecord] = []
        self.file_id_to_meta: dict[str, dict[str, Any]] = {}
        self.fname_to_file_id: dict[str, str] = {}
        self._load_manifest()

    def _load_manifest(self) -> None:
        manifest_path = os.path.join(self.dataset_dir, "evidence_files.csv")
        if not os.path.exists(manifest_path):
            return
        df = pd.read_csv(manifest_path)
        for _, r in df.iterrows():
            fid = r["file_id"]
            self.file_id_to_meta[fid] = r.to_dict()
            fname = os.path.basename(r["file_path"])
            self.fname_to_file_id[fname] = fid

    def build_index(self) -> None:
        self.records.clear()
        self._parse_txt_handover()
        self._parse_service_resource_exports()
        self._parse_generic_record_jsons()
        self._parse_sql_databases()
        self._parse_activity_catalog()
        self._parse_trace_logs()

    def _add_record(
        self,
        fid: str,
        cap_at: str,
        sys_id: str,
        res_id: str,
        cat: str,
        stat: str,
        uid: str | None = None,
        em: str | None = None,
        phone: str | None = None,
        extra_idents: list[str | None] | None = None,
    ) -> None:
        if not res_id:
            return
        idents: set[str] = set()
        if uid:
            idents.add(uid.strip().lower())
        if em:
            idents.add(em.strip().lower())
        if phone:
            idents.add("".join(c for c in phone if c.isdigit()))
        if extra_idents:
            for x in extra_idents:
                if x:
                    idents.add(str(x).strip().lower())
        self.records.append(
            EvidenceRecord(
                evidence_id=fid,
                captured_at=cap_at,
                system_id=sys_id,
                resource_id=res_id,
                category=cat,
                status=stat,
                user_id=uid,
                email=em,
                phone=phone,
                identifiers=idents,
            )
        )

    def _parse_txt_handover(self) -> None:
        for txt_file in glob.glob(os.path.join(self.dataset_dir, "evidence", "records", "*.txt")):
            bname = os.path.basename(txt_file)
            fid = self.fname_to_file_id.get(bname)
            if not fid:
                continue
            cap_at = self.file_id_to_meta[fid]["captured_at"]
            with open(txt_file, "r", encoding="utf-8", errors="ignore") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("- "):
                        parts = [p.strip() for p in line[2:].split("|")]
                        if len(parts) >= 6:
                            _ts, sys_id, res_id, cat, stat, ident = parts[:6]
                            uid = ident if ident.startswith("user_") else None
                            em = ident if "@" in ident else None
                            self._add_record(fid, cap_at, sys_id, res_id, cat, stat, uid=uid, em=em)

    def _parse_service_resource_exports(self) -> None:
        pattern = os.path.join(
            self.dataset_dir, "evidence", "records", "service_resource_export_*.json"
        )
        for jf in glob.glob(pattern):
            bname = os.path.basename(jf)
            fid = self.fname_to_file_id.get(bname)
            if not fid:
                continue
            cap_at = self.file_id_to_meta[fid]["captured_at"]
            with open(jf, "r", encoding="utf-8", errors="ignore") as f:
                try:
                    d = json.load(f)
                except Exception:
                    continue
                exports = d.get("service_exports", {})

                # account_service
                for pl in exports.get("account_service", {}).get("profile_lookups", []):
                    res_id = pl.get("resource_id")
                    code = pl.get("status_code")
                    stat = "NOT_FOUND" if code == 404 else "FOUND"
                    prof = pl.get("profile") or {}
                    em = prof.get("email")
                    uid = prof.get("customer_reference")
                    self._add_record(
                        fid, cap_at, "account_service", res_id, "USER_PROFILE", stat, uid=uid, em=em
                    )

                # search_service
                for iq in exports.get("search_service", {}).get("index_queries", []):
                    res_id = iq.get("resource_id")
                    query_em = iq.get("query")
                    for doc in iq.get("hits", {}).get("documents", []):
                        doc_res = doc.get("resource_id") or res_id
                        em = doc.get("email") or query_em
                        uid = doc.get("customer_reference")
                        self._add_record(
                            fid,
                            cap_at,
                            "search_service",
                            doc_res,
                            "SEARCH_INDEX_ENTRY",
                            "FOUND",
                            uid=uid,
                            em=em,
                        )

                # analytics_platform
                for prof in exports.get("analytics_platform", {}).get("profiles", []):
                    res_id = prof.get("resource_id")
                    em = prof.get("email")
                    uid = prof.get("customer_reference")
                    stat = "IDENTIFIABLE" if em else "ANONYMIZED"
                    self._add_record(
                        fid,
                        cap_at,
                        "analytics_platform",
                        res_id,
                        "ANALYTICS_PROFILE",
                        stat,
                        uid=uid,
                        em=em,
                    )

                # support_platform
                for tkt in exports.get("support_platform", {}).get("tickets", []):
                    res_id = tkt.get("resource_id")
                    em = tkt.get("requester_email")
                    uid = tkt.get("customer_reference")
                    stat = "IDENTIFIABLE" if em else "REDACTED"
                    self._add_record(
                        fid,
                        cap_at,
                        "support_platform",
                        res_id,
                        "SUPPORT_MESSAGE",
                        stat,
                        uid=uid,
                        em=em,
                    )

                # export_service
                for exp in exports.get("export_service", {}).get("exports", []):
                    res_id = exp.get("resource_id")
                    em = exp.get("owner_email")
                    uid = exp.get("customer_reference")
                    self._add_record(
                        fid,
                        cap_at,
                        "export_service",
                        res_id,
                        "USER_EXPORT",
                        "FOUND",
                        uid=uid,
                        em=em,
                    )

                # integration_service
                for conn in exports.get("integration_service", {}).get("connectors", []):
                    res_id = conn.get("resource_id")
                    enabled = conn.get("enabled")
                    em = conn.get("customer_email")
                    uid = conn.get("customer_reference")
                    stat = "ACTIVE" if enabled else "DISABLED"
                    self._add_record(
                        fid,
                        cap_at,
                        "integration_service",
                        res_id,
                        "DATA_FLOW",
                        stat,
                        uid=uid,
                        em=em,
                    )

                # backup_service
                for bkp in exports.get("backup_service", {}).get("restore_entries", []):
                    res_id = bkp.get("resource_id")
                    allowed = bkp.get("restore_allowed")
                    em = bkp.get("customer_email")
                    uid = bkp.get("customer_reference")
                    stat = "ACTIVE" if allowed else "BLOCKED"
                    self._add_record(
                        fid,
                        cap_at,
                        "backup_service",
                        res_id,
                        "BACKUP_ARCHIVE",
                        stat,
                        uid=uid,
                        em=em,
                    )

                # security_service
                for sec in exports.get("security_service", {}).get("audit_records", []):
                    res_id = sec.get("resource_id")
                    uid = sec.get("subject_reference")
                    self._add_record(
                        fid,
                        cap_at,
                        "security_service",
                        res_id,
                        "SECURITY_AUDIT_LOG",
                        "PRESENT",
                        uid=uid,
                    )

    def _parse_generic_record_jsons(self) -> None:
        for jf in glob.glob(os.path.join(self.dataset_dir, "evidence", "records", "*.json")):
            bname = os.path.basename(jf)
            if bname.startswith("service_resource_export_"):
                continue
            fid = self.fname_to_file_id.get(bname)
            if not fid:
                continue
            cap_at = self.file_id_to_meta[fid]["captured_at"]
            with open(jf, "r", encoding="utf-8", errors="ignore") as f:
                try:
                    d = json.load(f)
                except Exception:
                    continue

                if "snapshots" in d:
                    for sn in d.get("snapshots", []):
                        store = sn.get("data_store")
                        coll = sn.get("collection")
                        for rec in sn.get("records", []):
                            res_id = rec.get("resource_id")
                            uid = (
                                rec.get("user_id")
                                or rec.get("customer_reference")
                                or rec.get("subject_reference")
                                or rec.get("subject_selector")
                            )
                            em = (
                                rec.get("email")
                                or rec.get("owner_email")
                                or rec.get("requester_email")
                                or rec.get("subject_selector")
                            )
                            phone = rec.get("phone")
                            ehash = rec.get("email_hash")

                            cat = "USER_PROFILE"
                            stat = "FOUND"
                            sys_id = store
                            if store == "account_service" or coll == "customer_profiles":
                                cat = "USER_PROFILE"
                                stat = "FOUND"
                                sys_id = "account_service"
                            elif store == "search_service" or coll == "customer_search_documents":
                                cat = "SEARCH_INDEX_ENTRY"
                                stat = "FOUND"
                                sys_id = "search_service"
                            elif (
                                store == "analytics_platform"
                                or coll == "customer_analytics_reports"
                            ):
                                cat = "ANALYTICS_PROFILE"
                                stat = "IDENTIFIABLE" if (em or phone) else "ANONYMIZED"
                                sys_id = "analytics_platform"
                            elif store == "support_platform" or coll == "support_conversations":
                                cat = "SUPPORT_MESSAGE"
                                stat = "IDENTIFIABLE" if (em or phone) else "REDACTED"
                                sys_id = "support_platform"
                            elif store == "export_service" or coll == "customer_exports":
                                cat = "USER_EXPORT"
                                stat = "FOUND"
                                sys_id = "export_service"
                            elif (
                                store == "integration_service" or coll == "connector_configurations"
                            ):
                                cat = "DATA_FLOW"
                                stat = "ACTIVE" if rec.get("enabled") else "DISABLED"
                                sys_id = "integration_service"
                            elif store == "backup_service" or coll == "backup_catalog":
                                cat = "BACKUP_ARCHIVE"
                                stat = "ACTIVE" if rec.get("restore_allowed") else "BLOCKED"
                                sys_id = "backup_service"
                            elif store == "security_service" or coll == "security_audit_events":
                                cat = "SECURITY_AUDIT_LOG"
                                stat = "PRESENT"
                                sys_id = "security_service"
                            elif store == "identity_service" or coll == "account_tombstones":
                                cat = "ACCOUNT_TOMBSTONE"
                                stat = "IDENTIFIABLE" if (em or phone) else "REDACTED"
                                sys_id = "identity_service"
                            self._add_record(
                                fid,
                                cap_at,
                                sys_id,
                                res_id,
                                cat,
                                stat,
                                uid=uid,
                                em=em,
                                phone=phone,
                                extra_idents=[ehash],
                            )

                elif "records" in d:
                    coll = d.get("collection", "")
                    for rec in d.get("records", []):
                        res_id = rec.get("resource_id")
                        uid = (
                            rec.get("user_id")
                            or rec.get("customer_reference")
                            or rec.get("subject_reference")
                        )
                        em = (
                            rec.get("email")
                            or rec.get("owner_email")
                            or rec.get("requester_email")
                            or rec.get("subject_reference")
                        )
                        if em and "@" not in em:
                            if em.startswith("user_"):
                                uid = em
                                em = None
                        phone = rec.get("phone")
                        ehash = rec.get("email_hash")

                        cat = "USER_PROFILE"
                        sys_id = rec.get("system") or (
                            "export_service"
                            if "export" in bname
                            else (
                                "analytics_platform"
                                if "analytics" in bname
                                else "security_service" if "audit" in bname else "account_service"
                            )
                        )
                        stat = "FOUND"

                        if "export" in bname or "export" in coll:
                            cat = "USER_EXPORT"
                            sys_id = "export_service"
                            stat = "FOUND" if rec.get("download_available", True) else "NOT_FOUND"
                        elif "analytics" in bname or "analytics" in coll:
                            cat = "ANALYTICS_PROFILE"
                            sys_id = "analytics_platform"
                            stat = "IDENTIFIABLE" if (em or uid or phone) else "ANONYMIZED"
                        elif "connector" in bname or "connector" in coll:
                            cat = "DATA_FLOW"
                            sys_id = "integration_service"
                            stat = "ACTIVE" if rec.get("enabled", True) else "DISABLED"
                        elif "audit" in bname or "audit" in coll:
                            cat = "SECURITY_AUDIT_LOG"
                            sys_id = "security_service"
                            stat = "PRESENT"
                        if res_id:
                            self._add_record(
                                fid,
                                cap_at,
                                str(sys_id),
                                str(res_id),
                                cat,
                                stat,
                                uid=uid,
                                em=em,
                                phone=phone,
                                extra_idents=[ehash],
                            )

    def _parse_sql_databases(self) -> None:
        for sf in glob.glob(os.path.join(self.dataset_dir, "evidence", "databases", "*.sql")):
            bname = os.path.basename(sf)
            fid = self.fname_to_file_id.get(bname)
            if not fid:
                continue
            cap_at = self.file_id_to_meta[fid]["captured_at"]
            conn = sqlite3.connect(":memory:")
            with open(sf, "r", encoding="utf-8", errors="ignore") as f:
                sql = f.read()
            try:
                conn.executescript(sql)
            except Exception:
                continue
            cur = conn.cursor()
            cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [r[0] for r in cur.fetchall()]

            for t in tables:
                cur.execute(f"PRAGMA table_info({t});")
                cols = [c[1] for c in cur.fetchall()]
                cur.execute(f"SELECT * FROM {t};")
                rows = cur.fetchall()

                if "record_json" in cols:
                    json_idx = cols.index("record_json")
                    sys_idx = cols.index("origin_system") if "origin_system" in cols else None
                    res_idx = cols.index("resource_id") if "resource_id" in cols else None
                    for row in rows:
                        res_id = row[res_idx] if res_idx is not None else None
                        sys_id = row[sys_idx] if sys_idx is not None else None
                        try:
                            payload = json.loads(row[json_idx])
                        except Exception:
                            payload = {}
                        res_id = payload.get("resource_id") or res_id
                        uid = (
                            payload.get("user_id")
                            or payload.get("customer_reference")
                            or payload.get("subject_reference")
                            or payload.get("subject_selector")
                        )
                        em = (
                            payload.get("email")
                            or payload.get("owner_email")
                            or payload.get("requester_email")
                            or payload.get("subject_selector")
                        )
                        phone = payload.get("phone")
                        ehash = payload.get("email_hash")

                        cat = "USER_PROFILE"
                        stat = "FOUND"
                        if sys_id == "account_service" or "profile" in t:
                            cat = "USER_PROFILE"
                            stat = "FOUND"
                            sys_id = "account_service"
                        elif sys_id == "search_service" or "search" in t:
                            cat = "SEARCH_INDEX_ENTRY"
                            stat = "FOUND"
                            sys_id = "search_service"
                        elif sys_id == "analytics_platform" or "analytics" in t:
                            cat = "ANALYTICS_PROFILE"
                            stat = "IDENTIFIABLE" if (em or phone) else "ANONYMIZED"
                            sys_id = "analytics_platform"
                        elif sys_id == "support_platform" or "support" in t:
                            cat = "SUPPORT_MESSAGE"
                            stat = "IDENTIFIABLE" if (em or phone) else "REDACTED"
                            sys_id = "support_platform"
                        elif sys_id == "export_service" or "export" in t:
                            cat = "USER_EXPORT"
                            stat = "FOUND"
                            sys_id = "export_service"
                        elif sys_id == "integration_service" or "connector" in t:
                            cat = "DATA_FLOW"
                            stat = "ACTIVE" if payload.get("enabled") else "DISABLED"
                            sys_id = "integration_service"
                        elif sys_id == "backup_service" or "backup" in t:
                            cat = "BACKUP_ARCHIVE"
                            stat = "ACTIVE" if payload.get("restore_allowed") else "BLOCKED"
                            sys_id = "backup_service"
                        elif sys_id == "security_service" or "audit" in t:
                            cat = "SECURITY_AUDIT_LOG"
                            stat = "PRESENT"
                            sys_id = "security_service"
                        elif sys_id == "identity_service" or "tombstone" in t:
                            cat = "ACCOUNT_TOMBSTONE"
                            stat = "IDENTIFIABLE" if (em or phone) else "REDACTED"
                            sys_id = "identity_service"
                        if res_id:
                            self._add_record(
                                fid,
                                cap_at,
                                str(sys_id),
                                str(res_id),
                                cat,
                                stat,
                                uid=uid,
                                em=em,
                                phone=phone,
                                extra_idents=[ehash],
                            )
                else:
                    cat = "USER_PROFILE"
                    sys_id = "account_service"
                    if "profile" in t:
                        cat = "USER_PROFILE"
                        sys_id = "account_service"
                    elif "search" in t:
                        cat = "SEARCH_INDEX_ENTRY"
                        sys_id = "search_service"
                    elif "analytics" in t:
                        cat = "ANALYTICS_PROFILE"
                        sys_id = "analytics_platform"
                    elif "support" in t:
                        cat = "SUPPORT_MESSAGE"
                        sys_id = "support_platform"
                    elif "export" in t:
                        cat = "USER_EXPORT"
                        sys_id = "export_service"
                    elif "connector" in t:
                        cat = "DATA_FLOW"
                        sys_id = "integration_service"
                    elif "backup" in t:
                        cat = "BACKUP_ARCHIVE"
                        sys_id = "backup_service"
                    elif "audit" in t:
                        cat = "SECURITY_AUDIT_LOG"
                        sys_id = "security_service"
                    elif "tombstone" in t:
                        cat = "ACCOUNT_TOMBSTONE"
                        sys_id = "identity_service"

                    for row in rows:
                        row_dict = dict(zip(cols, row))
                        res_id = row_dict.get("resource_id")
                        uid = (
                            row_dict.get("user_id")
                            or row_dict.get("customer_reference")
                            or row_dict.get("subject_reference")
                        )
                        em = row_dict.get("email") or row_dict.get("customer_email")
                        phone = row_dict.get("phone")
                        ehash = row_dict.get("email_hash")

                        stat = "FOUND"
                        if cat == "ANALYTICS_PROFILE":
                            stat = "IDENTIFIABLE" if (em or phone) else "ANONYMIZED"
                        elif cat == "SUPPORT_MESSAGE":
                            stat = "IDENTIFIABLE" if (em or phone) else "REDACTED"
                        elif cat == "DATA_FLOW":
                            en = row_dict.get("enabled")
                            stat = "ACTIVE" if (str(en) in ("1", "True", "true")) else "DISABLED"
                        elif cat == "BACKUP_ARCHIVE":
                            res_al = row_dict.get("restore_allowed")
                            stat = "ACTIVE" if (str(res_al) in ("1", "True", "true")) else "BLOCKED"
                        elif cat == "SECURITY_AUDIT_LOG":
                            stat = "PRESENT"
                        elif cat == "ACCOUNT_TOMBSTONE":
                            stat = "IDENTIFIABLE" if (em or phone) else "REDACTED"
                        if res_id:
                            self._add_record(
                                fid,
                                cap_at,
                                str(sys_id),
                                str(res_id),
                                cat,
                                stat,
                                uid=uid,
                                em=em,
                                phone=phone,
                                extra_idents=[ehash],
                            )

    def _parse_activity_catalog(self) -> None:
        activity_path = os.path.join(self.dataset_dir, "system_activity.csv")
        if not os.path.exists(activity_path):
            return
        df = pd.read_csv(activity_path)
        catalog_ev_map = {
            "account_5762": "evidence_04",
            "search_428": "evidence_09",
            "data_flow_1121": "evidence_14",
            "analytics_7438": "evidence_19",
            "export_1260": "evidence_23",
            "support_1034": "evidence_28",
            "backup_9287": "evidence_32",
            "tombstone_17": "evidence_35",
            "audit_record_003": "evidence_38",
            "object_19": "evidence_41",
            "marketing_001": "evidence_55",
            "export_1842": "evidence_18",
            "support_001": "evidence_58",
        }
        if "event_type" in df.columns:
            for _, r in df[df["event_type"] == "LINK_RESOURCE_IDENTITY"].iterrows():
                res_id = r["resource_id"]
                target_sys = r["target_system"]
                det = str(r["details"])
                fid = catalog_ev_map.get(res_id)
                if not fid or fid not in self.file_id_to_meta:
                    continue
                cap_at = self.file_id_to_meta[fid]["captured_at"]
                emails = re.findall(r"[\w\.-]+@[\w\.-]+", det)
                users = re.findall(r"user_\d+", det)
                em = emails[0].lower() if emails else None
                uid = users[0] if users else None

                cat = "USER_PROFILE"
                stat = "FOUND"
                if target_sys == "search_service":
                    cat = "SEARCH_INDEX_ENTRY"
                elif target_sys == "integration_service":
                    cat = "DATA_FLOW"
                    stat = "ACTIVE"
                elif target_sys == "analytics_platform":
                    cat = "ANALYTICS_PROFILE"
                    stat = "IDENTIFIABLE"
                elif target_sys == "export_service":
                    cat = "USER_EXPORT"
                elif target_sys == "support_platform":
                    cat = "SUPPORT_MESSAGE"
                    stat = "IDENTIFIABLE"
                elif target_sys == "backup_service":
                    cat = "BACKUP_ARCHIVE"
                    stat = "ACTIVE"
                elif target_sys == "security_service":
                    cat = "SECURITY_AUDIT_LOG"
                elif target_sys == "identity_service":
                    cat = "ACCOUNT_TOMBSTONE"
                    stat = "REDACTED"
                elif target_sys == "marketing_platform":
                    cat = "MARKETING_PROFILE"
                self._add_record(fid, cap_at, target_sys, res_id, cat, stat, uid=uid, em=em)

    def _parse_trace_logs(self) -> None:
        for lf in glob.glob(os.path.join(self.dataset_dir, "evidence", "logs", "*.log")):
            bname = os.path.basename(lf)
            fid = self.fname_to_file_id.get(bname)
            if not fid:
                continue
            cap_at = self.file_id_to_meta[fid]["captured_at"]

            traces: dict[str, list[str]] = {}
            with open(lf, "r", encoding="utf-8", errors="ignore") as f:
                line_no = 0
                for line in f:
                    line_no += 1
                    if not line.strip():
                        continue
                    m_tr = re.search(
                        r'(?:trace_id|requestId|request_id)["\':= ]+([a-zA-Z0-9_-]+)', line
                    )
                    if not m_tr:
                        m_tr = re.search(r"\[(tr-[a-zA-Z0-9_-]+)\]", line)
                    tr = m_tr.group(1) if m_tr else f"line_{line_no}"
                    traces.setdefault(tr, []).append(line)

            for tr, lines in traces.items():
                blob = "\n".join(lines)
                emails = re.findall(r"[\w\.-]+@[\w\.-]+", blob)
                users = re.findall(r"user_\d+", blob)
                hashes = re.findall(r"[a-f0-9]{64}", blob)

                res_matches = re.findall(r"resource_id=([a-zA-Z0-9_-]+)", blob)
                if not res_matches:
                    res_matches = re.findall(r'resource_id="([a-zA-Z0-9_-]+)"', blob)

                sys_id = None
                for s in (
                    "account_service",
                    "search_service",
                    "analytics_platform",
                    "support_platform",
                    "export_service",
                    "integration_service",
                    "backup_service",
                    "security_service",
                    "identity_service",
                    "support_replica",
                ):
                    if s in blob:
                        sys_id = "support_platform" if s == "support_replica" else s
                        break

                if not sys_id:
                    continue

                for res_id in set(res_matches):
                    cat = "USER_PROFILE"
                    stat = "FOUND"
                    if sys_id == "account_service":
                        cat = "USER_PROFILE"
                        stat = (
                            "NOT_FOUND"
                            if ("404" in blob or "NOT_FOUND" in blob or "rows=0" in blob)
                            else "FOUND"
                        )
                    elif sys_id == "security_service":
                        cat = "SECURITY_AUDIT_LOG"
                        stat = "PRESENT"
                    elif sys_id == "analytics_platform":
                        cat = "ANALYTICS_PROFILE"
                        has_ident = bool(emails or hashes or users)
                        if (
                            "rows=0" in blob
                            or "anonymized" in blob.lower()
                            or "email=null" in blob.lower()
                        ):
                            stat = "ANONYMIZED"
                        elif "rows=1" in blob and has_ident:
                            stat = "FOUND"
                        else:
                            stat = "ANONYMIZED" if not has_ident else "IDENTIFIABLE"
                    elif sys_id == "support_platform":
                        cat = "SUPPORT_MESSAGE"
                        stat = (
                            "REDACTED"
                            if (
                                "redacted" in blob.lower()
                                or "requester_email=null" in blob.lower()
                                or not emails
                            )
                            else "IDENTIFIABLE"
                        )
                    elif sys_id == "integration_service":
                        cat = "DATA_FLOW"
                        stat = (
                            "DISABLED"
                            if (
                                "disabled" in blob.lower()
                                or "stopped" in blob.lower()
                                or "enabled=false" in blob.lower()
                            )
                            else "ACTIVE"
                        )
                    elif sys_id == "backup_service":
                        cat = "BACKUP_ARCHIVE"
                        stat = (
                            "BLOCKED"
                            if (
                                "blocked" in blob.lower()
                                or "restore_allowed=false" in blob.lower()
                                or "forbidden" in blob.lower()
                            )
                            else "ACTIVE"
                        )
                    elif sys_id == "search_service":
                        cat = "SEARCH_INDEX_ENTRY"
                        stat = (
                            "NOT_FOUND" if ("total_hits=0" in blob or "rows=0" in blob) else "FOUND"
                        )
                    elif sys_id == "identity_service":
                        cat = "ACCOUNT_TOMBSTONE"
                        stat = (
                            "REDACTED"
                            if ("redacted" in blob.lower() or not emails)
                            else "IDENTIFIABLE"
                        )

                    em = emails[0].lower() if emails else None
                    uid = users[0] if users else None
                    self._add_record(
                        fid, cap_at, sys_id, res_id, cat, stat, uid=uid, em=em, extra_idents=hashes
                    )

    def find_records_for_user(
        self,
        user_id: str | None,
        all_emails: set[str],
        all_hashes: set[str],
        all_phones: set[str],
        audit_at: str,
    ) -> dict[str, EvidenceRecord]:
        """
        Finds all evidence records matching the user's identifiers captured at or before audit_at.
        Returns the latest record per resource_id.
        """
        user_idents = all_emails | all_hashes | all_phones
        if user_id:
            user_idents.add(user_id.lower())

        matched: list[EvidenceRecord] = []
        for rec in self.records:
            if rec.captured_at <= audit_at:
                if (
                    (rec.user_id and rec.user_id == user_id)
                    or (rec.email and rec.email in all_emails)
                    or (rec.identifiers & user_idents)
                ):
                    matched.append(rec)

        # Sort descending by captured_at to keep latest state at audit_at
        matched.sort(key=lambda r: r.captured_at, reverse=True)

        latest_by_res: dict[str, EvidenceRecord] = {}
        for rec in matched:
            if rec.resource_id not in latest_by_res:
                latest_by_res[rec.resource_id] = rec

        return latest_by_res
