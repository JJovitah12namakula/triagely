from datetime import datetime
from pydantic import BaseModel, Field

class FindingCreate(BaseModel):
    title: str
    description: str = ""
    severity: str = "medium"
    tool: str = "manual"
    rule_id: str = ""
    file_path: str = ""
    fingerprint: str = ""
    evidence: dict = Field(default_factory=dict)

class FindingOut(BaseModel):
    id: int
    title: str
    description: str
    severity: str
    status: str
    tool: str
    rule_id: str
    file_path: str
    fingerprint: str
    evidence: dict
    created_at: datetime
    resolved_at: datetime | None
    class Config:
        from_attributes = True

class NoteCreate(BaseModel):
    author: str = "Reviewer"
    body: str

class NoteOut(BaseModel):
    id: int
    finding_id: int
    author: str
    body: str
    created_at: datetime
    class Config:
        from_attributes = True

class StatusUpdate(BaseModel):
    status: str
