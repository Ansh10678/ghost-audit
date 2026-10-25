# Discovery Findings — HackerRank Orchestrate (Oct 2026): Ghost Data Still Exists

## 1. Specifications & Contract Extraction

### 1.1 Source of Truth Hierarchy
Per project instructions, `problem_statement.md` is the primary source of truth, supported by `AGENTS.md` for execution/logging contracts and `README.md` for run instructions.

### 1.2 Input Schema (`dataset/deletion_requests.csv` and `sample_deletion_requests.csv`)
Columns in exact order:
1. `case_id` (string, e.g. `case_01`, `case_33`): Unique request and output identifier.
2. `email` (string): Subject identity provided at request time. May be a current or historical email address.
3. `requested_at` (ISO-8601 string, UTC): Timestamp when user submitted deletion request.
4. `reported_status` (enum: `COMPLETE`, `PARTIALLY_COMPLETE`, `NOT_STARTED`): Claim made by the internal deletion workflow. Must be treated as a claim, not ground truth.
5. `reported_at` (ISO-8601 string, UTC): Timestamp when the deletion workflow claim was recorded.
6. `audit_at` (ISO-8601 string, UTC): Cutoff timestamp for determining the audited ground truth state. Any evidence created after `audit_at` must be strictly ignored for that case.
7. `request_text` (string): Verbatim message text from user. Can be in multiple languages (English, Spanish, French, Korean, Japanese, Portuguese, German, etc.). Must be evaluated to determine if the user actually authorized deletion.

### 1.3 Required Output Schema (`output.csv`)
The output must be written to `output.csv` at the repository root.
Columns in exact order:
```text
case_id,deletion_status,steps_json
```

- Exactly 518 data rows matching the 518 requests in `dataset/deletion_requests.csv`.
- Sorted strictly by `case_id` in ascending order.
- `deletion_status` enum:
  - `COMPLETE`: Deletion is fully accomplished across all systems, retained records conform to policy, and no active recreation path exists at `audit_at`.
  - `INCOMPLETE`: Unlawfully retained records, exposed PII, active sync flows, or restore risks exist at `audit_at`.
  - `NOT_APPLICABLE`: The user's `request_text` does not authorize deletion (e.g., access, export, update, correction, marketing unsubscribe).
- `steps_json`: Valid JSON array representing ordered steps.
  - For `NOT_APPLICABLE`: strictly `[]` (empty JSON array).
  - For `COMPLETE`: verification steps only, citing valid `evidence_id` (`file_id`, `activity_id`, or `audit_id`).
  - For `INCOMPLETE`: complete set of `FINDING` steps (with valid `evidence_id`), followed by `REMEDIATION` steps (`evidence_id: ""`), followed by post-remediation `VERIFICATION` steps (`evidence_id: ""`).

### 1.4 Step Object Schema & Ordering Rules
Each step object in `steps_json` contains:
```json
{
  "step_no": 1,
  "phase": "FINDING",
  "system_id": "account_service",
  "resource_id": "account_005",
  "operation": "REPORT_REMAINING_RECORD",
  "state": "PRESENT",
  "evidence_id": "evidence_54"
}
```

#### Allowed Phases, Operations, and States:
1. **`FINDING` Phase**:
   - `REPORT_REMAINING_RECORD` | `PRESENT` (priority 1)
   - `REPORT_EXPOSED_PII` | `PRESENT` (priority 2)
   - `REPORT_ACTIVE_DATA_FLOW` | `ACTIVE` (priority 3)
   - `REPORT_RESTORE_RISK` | `ACTIVE` (priority 4)
2. **`REMEDIATION` Phase**:
   - `DISABLE_DATA_FLOW` | `DISABLED` (priority 1)
   - `BLOCK_RESTORE` | `BLOCKED` (priority 2)
   - `DELETE_RECORD` | `ABSENT` (priority 3)
   - `REDACT_RECORD` | `REDACTED` (priority 4)
   - `ANONYMIZE_RECORD` | `ANONYMIZED` (priority 5)
3. **`VERIFICATION` Phase**:
   - `VERIFY_RECORD_ABSENT` | `ABSENT` (priority 1)
   - `VERIFY_RECORD_PRESENT` | `PRESENT` (priority 2)
   - `VERIFY_RECORD_REDACTED` | `REDACTED` (priority 3)
   - `VERIFY_RECORD_ANONYMIZED` | `ANONYMIZED` (priority 4)
   - `VERIFY_DATA_FLOW_DISABLED` | `DISABLED` (priority 5)
   - `VERIFY_RESTORE_BLOCKED` | `BLOCKED` (priority 6)

#### Deterministic Sorting Hierarchy:
Verified against 100% of sample cases:
1. `phase` order: `FINDING` -> `REMEDIATION` -> `VERIFICATION`
2. `operation` order: Priority index defined in the canonical table above
3. `system_id` order: Lexicographical ascending
4. `resource_id` order: Lexicographical ascending
`step_no` is assigned sequentially from 1 to N after sorting.

### 1.5 Chat Transcript Logging Requirements (`log.txt`)
- Lives in repo root: `<repo_root>/log.txt`.
- Append-only UTF-8 format.
- Starts with `## [ISO-8601] SESSION START` containing tool name, exact model identifier, repo root, branch, worktree, parent agent, language, and time remaining.
- Every user turn ends with a per-turn entry containing verbatim prompt (secrets redacted), 2-5 sentence agent response summary, actions list, and context block.
- Mandatory check: `tool=` and `model=` must never be blank, unknown, or generic.

---

## 2. Dataset Inventory & Relationships

### 2.1 File Inventory Summary
| Location / File | Type | Count / Rows | Key Schema / Purpose |
|---|---|---|---|
| `dataset/deletion_requests.csv` | CSV | 518 rows | Full evaluation set (case_33 to case_550) |
| `dataset/sample_deletion_requests.csv` | CSV | 32 rows | Development / training sample set (case_01 to case_32) |
| `dataset/sample_output.csv` | CSV | 32 rows | Ground truth answers for the 32 sample cases |
| `dataset/output.csv` | CSV | 0 rows (header only) | Submission template |
| `dataset/user_identities.csv` | CSV | 850 rows | Current snapshot: `user_id`, `name`, `email`, `phone`, `email_hash`, `updated_at` |
| `dataset/user_audit_log.csv` | CSV | 306 rows | Historical changes: `audit_id`, `user_id`, `event_time`, `field_name` (`email`, `phone`, `email_hash`), `old_value`, `new_value` |
| `dataset/system_activity.csv` | CSV | 4,011 rows | Event log: `activity_id`, `event_time`, `event_type`, `source_system`, `target_system`, `resource_id`, `reported_result`, `details` |
| `dataset/deletion_rules.csv` | CSV | 15 rows | Deletion policy rules mapping category & condition to action |
| `dataset/evidence_files.csv` | CSV | 94 rows | Manifest: `file_id`, `file_path`, `origin`, `captured_at` |
| `dataset/evidence/databases/` | SQL | 24 files | SQLite DDL & INSERT statements representing DB snapshots & replicas |
| `dataset/evidence/documents/` | PDF | 4 files | Digital multi-page PDF documents |
| `dataset/evidence/images/` | PNG | 11 files | Admin & portal UI screenshots (1500x920 to 1800x1200) |
| `dataset/evidence/logs/` | LOG | 26 files | System runtime, syslog, service readback, trace logs |
| `dataset/evidence/records/` | JSON/TXT | 29 files (28 JSON, 1 TXT) | Snapshot bundles, connectors, resource exports, handover notes |

### 2.2 Complete Policy Rules Breakdown (`dataset/deletion_rules.csv`)
1. `rule_01`: `USER_PROFILE` | Condition: `Always` -> `DELETE`
2. `rule_02`: `SECONDARY_IDENTIFIER` | Condition: `Always` -> `DELETE`
3. `rule_03`: `SEARCH_INDEX_ENTRY` | Condition: `Always` -> `DELETE`
4. `rule_04`: `CACHE_ENTRY` | Condition: `Always` -> `DELETE`
5. `rule_05`: `SUPPORT_MESSAGE` | Condition: `Conversation contains shared customer, agent, or order context that must be retained` -> `REDACT`
6. `rule_06`: `SUPPORT_ATTACHMENT` | Condition: `Attachment belongs only to the deletion subject` -> `DELETE`
7. `rule_07`: `ANALYTICS_PROFILE` | Condition: `Record is still attributable to a user` -> `ANONYMIZE`
8. `rule_08`: `PRODUCT_TELEMETRY` | Condition: `Record is still attributable to a user` -> `ANONYMIZE`
9. `rule_09`: `USER_EXPORT` | Condition: `Always` -> `DELETE`
10. `rule_10`: `MARKETING_PROFILE` | Condition: `Always` -> `DELETE`
11. `rule_11`: `EMAIL_DELIVERY_LOG` | Condition: `Log contains a user email address` -> `REDACT`
12. `rule_12`: `SECURITY_AUDIT_LOG` | Condition: `Record is within the supplied retention period` -> `RETAIN`
13. `rule_13`: `LEGAL_HOLD_RECORD` | Condition: `A supplied legal hold is active` -> `RETAIN`
14. `rule_14`: `BACKUP_ARCHIVE` | Condition: `Restore access can be blocked` -> `RETAIN` (with `BLOCK_RESTORE`)
15. `rule_15`: `ACCOUNT_TOMBSTONE` | Condition: `Account is deleted and only a stable internal user_id is needed to preserve references to retained records` -> `REDACT`

---

## 3. Media & Multimodal Evidence Deep Dive

All media files were opened and structurally analyzed:

### 3.1 PDF Documents (`dataset/evidence/documents/`)
1. `account_history_report_20260718.pdf` (evidence_18):
   - Type: Statement NST-2026-0718-1842
   - PII Extracted: Customer `Customer A`, `user_18`, `user18@example.com`, Order `ORD-20261260`, Address `24 Example Way, 7010 Trondheim, Norway`, Visa ending 4821.
2. `delivery_correction_attachment.pdf` (evidence_37):
   - Type: Support Ticket Attachment CS-4827 / `support_001`
   - PII Extracted: `Customer B`, `user37@example.com`, `+91 98765 00000`, Order `ORD-20264827`, apartment change request, SwiftShip.
3. `legal_retention_register_20260529.pdf` (evidence_27):
   - Type: Disputed Orders & Tax Records Register (Legal Hold)
   - Content: Disputed orders with user IDs `user_08`, `user_12`, `user_17`, `user_21`, `user_24`, `user_29`, Retain-until dates in 2033.
4. `security_retention_extract.pdf` (evidence_36):
   - Type: Compliance Journal Signed Record Extract Reference CJX-20260905-0630
   - Content: `audit_record_003`, Subject `user_03`, Event: Account closure recorded, retain until 25 Aug 2027.

### 3.2 UI Screenshots (`dataset/evidence/images/`)
1. `account_admin_console_20260926.png` (evidence_04):
   - Portal: Northstar Customer Operations
   - User: `Customer C`, `user_11`, `account_5762`, `user11@example.com`, `+81 90 0000 0000`, Orders `ORD-20265762`, `ORD-20265518`, Address in Tokyo.
2. `analytics_profile_view_20260713.png` (evidence_19):
   - Portal: Pulse Analytics
   - User: `Customer D`, `user_20`, `analytics_7438`, `user20@example.com`, Sessions: 12, Revenue: $167.42.
3. `backup_restore_console_20260429.png` (evidence_32):
   - Portal: Vault Recovery Manager
   - Active Archives: `backup_9291` (`user_arch_a@example.com`), `backup_9287` (`user_arch_b@example.com`), S3 tar.zst path, retention end 26 Jul 2026.
4. `connector_management_console_20260807.png` (evidence_14):
   - Portal: BridgeOps Connections
   - Active Continuous Sync: `data_flow_1121` targeting `customer_analytics_warehouse` for selector `sync_user_a@example.com`; `data_flow_9846` for `sync_user_b@example.com`.
5. `customer_export_console_20260618.png` (evidence_23):
   - Portal: Customer Download Center
   - Active/Ready Export: `export_1260` (`customer_export_1260.zip`), owner `user18@example.com`, expires 25 Jun 2026.
6. `deleted_account_reference_20260310.png` (evidence_35):
   - Portal: Customer Reference Registry
   - Status: Tombstone `user_17` (Retained reference). All direct PII removed, only internal reference preserved.
7. `marketing_profile_console.png` (evidence_55):
   - Portal: Audience Operations
   - User: `Customer E` (Live), `marketing_001`, `user_mktg@example.com`, `+82 10-0000-0000`, Email opt-in: Yes.
8. `object_storage_browser_20260213.png` (evidence_41):
   - Portal: Nimbus Object Storage
   - Objects: `delivery_confirmation_19.pdf`, `customer_export_2026-02-10.zip`, etc.
9. `search_index_inspector_20260901.png` (evidence_09):
   - Portal: Search Console
   - Query: `email:user13@example.com`, Hit: `search_428` (`Customer F`, `user_13`).
10. `security_audit_explorer_20260905.png` (evidence_38):
    - Portal: Sentinel Account Events
    - Filter: `user_03`, Events: `audit_record_001` through `audit_record_006`.
11. `support_ticket_console_20260524.png` (evidence_28):
    - Portal: Helpline Console
    - Ticket: `CS-5034` / `support_1034`, Customer: `Customer G`, `user_support@example.com`.

---

## 4. Key Discovery Findings & Edge Cases

1. **`NOT_APPLICABLE` Cases Identified in Data**:
   - In `dataset/deletion_requests.csv`, several cases contain requests for non-deletion intents (e.g. `case_533` updating mobile number, `case_534` stopping promo emails, `case_535` downloading data export, `case_537` name typo correction, `case_540` invoice request, `case_541` change email).
   - These MUST yield `NOT_APPLICABLE` with `steps_json: "[]"`.
2. **Historical vs Current Email Matching**:
   - Users may request deletion using an old email found only in `user_audit_log.csv` (`old_value`) where `field_name == 'email'`.
   - The identity resolver must map the input email to the canonical `user_id`, and then recover ALL associated emails, phones, names, and hashes.
3. **Temporal Cutoff Enforcement (`audit_at`)**:
   - Evidence files, logs, and activity events have capture/event timestamps.
   - Any evidence file captured strictly after `audit_at` must not influence the state determination at `audit_at`.
4. **Account Tombstones**:
   - `ACCOUNT_TOMBSTONE` requires retaining `user_id` while removing name, email, phone, and email hash.
   - If direct PII remains in a tombstone, it is a finding (`REPORT_EXPOSED_PII`) requiring `REDACT_RECORD`.
5. **Recreation Paths**:
   - Active connectors (`REPORT_ACTIVE_DATA_FLOW`) and scheduled backup restores (`REPORT_RESTORE_RISK`) recreate deleted data.
   - Remediation must first disable the data flow / block restore before addressing data records.

