# Northstar Shop — Deletion Audit Agent

AI-powered deletion-audit agent built for **HackerRank Orchestrate (October 2026): Ghost Data Still Exists**.

Challenge & Submission URL: https://www.hackerrank.com/contests/hackerrank-orchestrate-october26/challenges/ghost-data-still-exists

---

## 1. Overview
The **Northstar Shop Deletion Audit Agent** evaluates account and data deletion requests against enterprise evidence stores (relational databases, regional replicas, search indices, analytics profiles, support records, user exports, continuous integration connectors, backup catalogs, and audit logs).

It performs:
1. **Request Intent Classification**: Detects whether the subject actually requested erasure or submitted a non-deletion request (DSAR export, rectification, marketing opt-out, explicit retention).
2. **Deterministic Identity Resolution**: Reconstructs current and historical identifiers (`user_id`, emails, phone numbers, SHA-256 email hashes) from `user_identities.csv` and `user_audit_log.csv`.
3. **Cross-System Evidence Auditing**: Scans all 94 evidence files under `dataset/evidence/` up to the case cutoff `captured_at <= audit_at`.
4. **Recreation Risk Detection**: Identifies active continuous data flows and backup restore access capable of repopulating purged data.
5. **Deterministic Remediation Planning**: Implements the canonical 4-tuple ordering rule:
   `Phase Priority -> Operation Priority -> system_id -> resource_id`.
6. **Ground-Truth Verification**: Outputs compliant verification steps citing grounded evidence IDs for `COMPLETE` cases.

---

## 2. Requirements & Setup

### Environment
- Python 3.10+
- Dependencies listed in `requirements.txt`:
  - `pandas`
  - `pydantic`
  - `python-dotenv`
  - `pytest`
  - `google-genai`

### Installation
```bash
# Clone the repository
git clone https://github.com/interviewstreet/hackerrank-orchestrate-october26.git
cd hackerrank-orchestrate-october26

# Install dependencies
pip install -r code/requirements.txt
```

### Configuration (Optional)
Copy `.env.example` to `.env` if using Gemini API for multimodal extraction or intent fallback:
```bash
cp code/.env.example code/.env
```

---

## 3. Running the Audit Agent

### Full Dataset Run (Produces Root `output.csv`)
To audit all 518 evaluation requests and produce the submission file `output.csv` at the repository root:
```bash
python code/main.py run --input dataset/deletion_requests.csv --output output.csv
```

### Evaluation Benchmark
To run the evaluation suite against the 32 labeled benchmark cases in `sample_deletion_requests.csv` and generate `evaluation/evaluation_report.md` and `evaluation/usage_report.md`:
```bash
python code/main.py eval
```

### Running Unit & Anti-Hardcoding Tests
```bash
pytest code/tests -v
```

---

## 4. Output Contract
The generated `output.csv` conforms strictly to the challenge schema:
```text
case_id,deletion_status,steps_json
```
- Exactly 518 rows, sorted by `case_id`.
- `deletion_status`: `COMPLETE`, `INCOMPLETE`, or `NOT_APPLICABLE`.
- `steps_json`: valid JSON array of objects with keys `step_no`, `phase`, `system_id`, `resource_id`, `operation`, `state`, `evidence_id`.
- Ordered by `FINDING` -> `REMEDIATION` -> `VERIFICATION`.
- Numbered consecutively from `1`.

