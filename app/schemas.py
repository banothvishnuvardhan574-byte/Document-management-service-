from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.config import VALID_STATUSES

class DocumentBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    source: str = Field(..., min_length=1, max_length=150)
    document_date: Optional[datetime] = None

    @field_validator("title", "category", "source", mode="before")
    @classmethod
    def strip_required_text(cls, value: str) -> str:
        return value.strip() if isinstance(value, str) else value


class DocumentCreate(DocumentBase):
    pass


class DocumentUpdate(BaseModel):
    title: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    category: Optional[str] = Field(default=None, min_length=1, max_length=100)
    source: Optional[str] = Field(default=None, min_length=1, max_length=150)
    document_date: Optional[datetime] = None

    @field_validator("title", "category", "source", mode="before")
    @classmethod
    def strip_optional_text(cls, value: str | None) -> str | None:
        return value.strip() if isinstance(value, str) else value


class DocumentStatusUpdate(BaseModel):
    status: str = Field(..., min_length=1, max_length=50)

    @field_validator("status", mode="before")
    @classmethod
    def validate_status(cls, value: str) -> str:
        if not isinstance(value, str):
            return value
        normalized = value.strip().upper()
        if normalized not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}.")
        return normalized


class DocumentRead(DocumentBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    original_filename: Optional[str] = None
    stored_filename: Optional[str] = None
    file_path: Optional[str] = None
    file_size: Optional[int] = None
    mime_type: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime


class ApiResponse(BaseModel):
    success: bool
    message: str
    data: Optional[dict[str, Any]] = None
    detail: Optional[str] = None


class HealthResponse(BaseModel):
    success: bool = True
    message: str = "Service is healthy"
    version: str = "0.1.0"
