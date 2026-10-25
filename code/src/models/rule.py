from enum import Enum

from pydantic import BaseModel


class RuleAction(str, Enum):
    DELETE = "DELETE"
    REDACT = "REDACT"
    ANONYMIZE = "ANONYMIZE"
    RETAIN = "RETAIN"


class DeletionRule(BaseModel):
    rule_id: str
    data_category: str
    condition: str
    required_action: RuleAction
