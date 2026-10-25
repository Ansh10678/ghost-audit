import re

# Explicit non-deletion patterns across multiple languages
NON_DELETION_PATTERNS = [
    # Explicit retention / keep account active
    r"leave\s+(?:the\s+)?account\s+active",
    r"keep\s+(?:the\s+)?account\s+as\s+it\s+is",
    r"not\s+asking\s+for\s+deletion",
    r"without\s+removing\s+any\s+(?:of\s+my\s+)?records",
    r"leave\s+my\s+profile.*?in\s+place",
    r"want\s+to\s+continue\s+using\s+(?:the\s+)?service",
    r"still\s+need\s+(?:the\s+)?account",
    r"ne\s+souhaite\s+pas\s+supprimer\s+mon\s+compte",
    r"garde[rz]\s+le\s+compte\s+actif",
    r"dejar\s+la\s+cuenta\s+activa",
    r"no\s+estoy\s+solicitando\s+la\s+eliminaci[oó]n",
    r"계정을\s*유지",
    r"삭제를\s*요청하지\s*않",
    r"アカウントを\s*維持",
    r"削除を\s*希望しません",
    # Marketing opt-out
    r"stop\s+(?:the\s+)?promotional\s+emails",
    r"unsubscribe\s+from\s+marketing",
    r"stop\s+sending\s+(?:promotional|marketing|newsletter)",
    # Access / Export / Invoices (DSAR / Art 15)
    r"download\s+my\s+account\s+information",
    r"copy\s+of\s+last\s+year'?s?\s+invoices",
    r"send\s+me\s+a\s+copy\s+of\s+my\s+invoices",
    r"export\s+my\s+(?:personal\s+)?data\s+without\s+delet",
    # Rectification / Correction (Art 16)
    r"misspelled\s+on\s+the\s+account.*?correct\s+it",
    r"replace\s+it\s+with\s+the\s+new\s+one\s+and\s+leave",
    r"change\s+the\s+email\s+address\s+used\s+for\s+this\s+account.*?continue",
    r"update\s+my\s+shipping\s+address.*?do\s+not\s+delete",
]


class IntentClassifier:
    @staticmethod
    def is_deletion_request(text: str) -> bool:
        """
        Determines whether the request authorizes account/personal-data deletion.
        A request for access, correction, export, marketing opt-out, or explicit retention
        returns False (NOT_APPLICABLE).
        """
        if not text:
            return True

        t_clean = text.strip()
        t_lower = t_clean.lower()

        # Check for explicit non-deletion patterns
        for pattern in NON_DELETION_PATTERNS:
            if re.search(pattern, t_lower):
                return False

        return True
