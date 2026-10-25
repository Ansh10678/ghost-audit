# Contributing to Ghost Audit

We welcome contributions to the Ghost Data Deletion Audit Agent! This guide outlines how to submit bug reports, feature requests, and pull requests.

## Development Setup

1. **Clone the repository**:
   ```bash
   git clone https://github.com/<your-username>/ghost-audit.git
   cd ghost-audit
   ```

2. **Create and activate a virtual environment**:
   ```bash
   python -m venv venv
   # On macOS/Linux:
   source venv/bin/activate
   # On Windows:
   .\venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Run tests**:
   ```bash
   pytest code/tests -v
   ```

## Code Quality Standards

- **Formatting & Linting**: We use `ruff` and `black`. Before opening a pull request, run:
  ```bash
  ruff check code
  black --check code
  ```
- **Zero Hardcoding**: Never commit code with hardcoded user IDs, emails, request identifiers, or target labels. The pipeline must derive all decisions dynamically from the data and rule engines.
- **Privacy & Safety**: Never commit real customer personal data, API tokens, or secrets. All unit tests must use the synthetic fixtures located in `code/tests/fixtures/synthetic_dataset`.
- **Determinism**: Sorting and serialization of audit outputs must remain deterministic across Python runtimes and operating systems.

## Submitting Pull Requests

1. Create a feature branch (`git checkout -b feature/your-feature-name`).
2. Implement your changes and add corresponding unit tests under `code/tests/`.
3. Verify that all tests pass (`pytest code/tests -v`).
4. Commit with descriptive, logical messages following conventional commits (`feat:`, `fix:`, `docs:`, `test:`).
5. Open a Pull Request with a clear summary of your motivation, architecture impact, and testing proof.
