from typing import Any

from pydantic import BaseModel


class EvidenceFile(BaseModel):
    file_id: str
    file_path: str
    origin: str
    captured_at: str


class DiscoveredItem(BaseModel):
    system_id: str
    resource_id: str
    data_category: str
    evidence_id: str
    observed_at: str
    status: str  # e.g. "FOUND", "NOT_FOUND", "IDENTIFIABLE", "ANONYMIZED", "REDACTED", "ACTIVE", "DISABLED", "BLOCKED"
    identifiers_found: dict[str, Any] = {}
