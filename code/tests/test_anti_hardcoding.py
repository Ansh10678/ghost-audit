import os
import re
from pathlib import Path

CODE_SRC = Path(__file__).resolve().parent.parent / "src"


def test_no_hardcoded_case_ids():
    """Verify no case_01, case_02, etc. appear in core source logic."""
    for root, _, files in os.walk(CODE_SRC):
        for f in files:
            if f.endswith(".py"):
                fpath = Path(root) / f
                with open(fpath, "r", encoding="utf-8") as fp:
                    content = fp.read()
                    matches = re.findall(r"\bcase_\d+\b", content)
                    assert not matches, f"Found hardcoded case IDs {matches} in {fpath}"


def test_no_hardcoded_user_emails():
    """Verify no specific mock customer emails are hardcoded in core source logic."""
    suspicious_patterns = [
        r"amina\.elmasri",
        r"mateo\.rios",
        r"thandiwe\.n",
        r"leila\.haddad",
        r"novak\.tomasz",
    ]
    for root, _, files in os.walk(CODE_SRC):
        for f in files:
            if f.endswith(".py"):
                fpath = Path(root) / f
                with open(fpath, "r", encoding="utf-8") as fp:
                    content = fp.read()
                    for pat in suspicious_patterns:
                        assert not re.search(
                            pat, content
                        ), f"Found hardcoded email pattern {pat} in {fpath}"
