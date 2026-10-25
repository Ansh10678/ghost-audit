# Changelog

All notable changes to the Ghost Data Deletion Audit Agent will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2026-10-25

### Added
- **Identity Graph Resolution**: Transitive closure resolver mapping current and historical user identities (emails, aliases, phones, hashed tokens) with anti-collision validation.
- **Multimodal Evidence Scanner**: Ingestion engine parsing SQL databases and replica dumps (including nested JSON columns), distributed trace logs, structured records, and OCR/VLM visual evidence.
- **Dynamic Deletion Rule Engine**: Comprehensive policy compliance engine supporting `DELETE`, `REDACT`, `ANONYMIZE`, and statutory `RETAIN` rules with tombstone preservation and over-deletion safeguards.
- **Recreation Path Detection**: Vector analysis detecting continuous sync data flows and unmasked backup restore vulnerabilities that re-populate erased personal data.
- **Deterministic Remediation Planner**: Topological dependency planner emitting ordered remediation actions (`DISABLE_DATA_FLOW`, `BLOCK_RESTORE`, `DELETE_RECORD`, etc.) alongside post-remediation verification checks.
- **Intent Classifier**: Multilingual natural language intent engine distinguishing genuine erasure authorizations from DSAR access, marketing opt-out, and rectification requests.
- **Standalone Synthetic Test Suite**: Complete synthetic dataset and end-to-end test suite (`code/tests/`) enabling offline verification without third-party dependencies.
- **Continuous Integration**: GitHub Actions workflow testing formatting, linting, and synthetic test suites across multiple Python versions.
