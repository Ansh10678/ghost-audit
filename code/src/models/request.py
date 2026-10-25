from pydantic import BaseModel


class DeletionRequest(BaseModel):
    case_id: str
    email: str
    requested_at: str
    reported_status: str
    reported_at: str
    audit_at: str
    request_text: str
