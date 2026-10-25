from pydantic import BaseModel, Field


class SubjectIdentity(BaseModel):
    user_id: str
    name: str | None = None
    current_email: str
    historical_emails: set[str] = Field(default_factory=set)
    phones: set[str] = Field(default_factory=set)
    email_hashes: set[str] = Field(default_factory=set)
    account_ids: set[str] = Field(default_factory=set)

    @property
    def all_emails(self) -> set[str]:
        emails = {self.current_email.lower()}
        for e in self.historical_emails:
            emails.add(e.lower())
        return emails

    def matches_email(self, email: str) -> bool:
        if not email:
            return False
        return email.strip().lower() in self.all_emails

    def matches_phone(self, phone: str) -> bool:
        if not phone:
            return False
        p_clean = "".join(ch for ch in phone if ch.isdigit())
        for p in self.phones:
            if "".join(ch for ch in p if ch.isdigit()) == p_clean:
                return True
        return False
