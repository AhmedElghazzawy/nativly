import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.writing.feedback import WritingFeedback
from app.writing.models import MistakeCategory


class SubmissionRequest(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


class SubmissionRead(BaseModel):
    id: uuid.UUID
    task_slug: str
    text: str
    word_count: int
    feedback: WritingFeedback
    created_at: datetime


class MistakeRead(BaseModel):
    category: MistakeCategory
    original: str
    correction: str
    explanation: str
    count: int
    last_seen_at: datetime
