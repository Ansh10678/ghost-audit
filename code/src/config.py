import os
from pathlib import Path

from dotenv import load_dotenv

# Find project roots
# Path of this file: <repo>/code/src/config.py
SRC_DIR = Path(__file__).resolve().parent
CODE_DIR = SRC_DIR.parent
REPO_ROOT = CODE_DIR.parent

# Load .env if present
load_dotenv(CODE_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")


class Config:
    REPO_ROOT: Path = REPO_ROOT
    CODE_DIR: Path = CODE_DIR

    # Dataset path configurable via environment variable or default
    DATASET_DIR: Path = Path(os.environ.get("DATASET_DIR", REPO_ROOT / "dataset")).resolve()

    # Default input and output paths
    DEFAULT_INPUT: Path = DATASET_DIR / "deletion_requests.csv"
    DEFAULT_SAMPLE_INPUT: Path = DATASET_DIR / "sample_deletion_requests.csv"
    DEFAULT_SAMPLE_OUTPUT: Path = DATASET_DIR / "sample_output.csv"
    DEFAULT_OUTPUT: Path = REPO_ROOT / "output.csv"

    # Manifest and policy files
    RULES_CSV: Path = DATASET_DIR / "deletion_rules.csv"
    IDENTITIES_CSV: Path = DATASET_DIR / "user_identities.csv"
    AUDIT_LOG_CSV: Path = DATASET_DIR / "user_audit_log.csv"
    ACTIVITY_CSV: Path = DATASET_DIR / "system_activity.csv"
    EVIDENCE_FILES_CSV: Path = DATASET_DIR / "evidence_files.csv"
    EVIDENCE_DIR: Path = DATASET_DIR / "evidence"

    # Cache and evaluation
    CACHE_DIR: Path = CODE_DIR / ".cache"
    EVAL_REPORTS_DIR: Path = CODE_DIR / "eval_reports"
    LOG_TXT: Path = REPO_ROOT / "log.txt"

    # LLM Settings
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY", ""))
    GEMINI_MODEL: str = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
    TEMPERATURE: float = 0.0


Config.CACHE_DIR.mkdir(parents=True, exist_ok=True)
Config.EVAL_REPORTS_DIR.mkdir(parents=True, exist_ok=True)
