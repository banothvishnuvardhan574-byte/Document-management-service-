from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import VALID_STATUSES, VALID_STATUS_TRANSITIONS
from app.exceptions import DocumentNotFoundError, InvalidStatusTransitionError
from app.models import Document
from app.schemas import DocumentCreate, DocumentUpdate
from app.services.file_service import FileService
from app.utils.validators import validate_document_title


class DocumentService:
    """Service for document lifecycle operations."""

    def __init__(self, db: Session) -> None:
        self.db = db

    def list_documents(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
        category: str | None = None,
        status: str | None = None,
    ) -> list[Document]:
        stmt = select(Document)
        if category:
            stmt = stmt.where(Document.category == category)
        if status:
            stmt = stmt.where(Document.status == status.upper())
        stmt = stmt.order_by(Document.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.execute(stmt).scalars().all())

    def get_document(self, document_id: int) -> Document:
        document = self.db.get(Document, document_id)
        if document is None:
            raise DocumentNotFoundError(document_id)
        return document

    def create_document(
        self,
        document_data: DocumentCreate | dict[str, Any],
        file_metadata: dict[str, Any] | None = None,
    ) -> Document:
        payload = (
            document_data.model_dump(exclude_unset=True)
            if isinstance(document_data, DocumentCreate)
            else dict(document_data)
        )

        title = payload.get("title")
        if title is None:
            raise ValueError("Title is required.")
        validated_title = validate_document_title(title)

        document = Document(
            title=validated_title,
            description=payload.get("description"),
            category=payload.get("category") or "UNCATEGORIZED",
            source=payload.get("source") or "MANUAL",
            document_date=payload.get("document_date"),
            status=payload.get("status") or "RECEIVED",
            original_filename=file_metadata.get("original_filename") if file_metadata else None,
            stored_filename=file_metadata.get("stored_filename") if file_metadata else None,
            file_path=file_metadata.get("file_path") if file_metadata else None,
            file_size=file_metadata.get("file_size") if file_metadata else None,
            mime_type=file_metadata.get("mime_type") if file_metadata else None,
        )

        status = document.status.upper()
        if status not in VALID_STATUSES:
            raise ValueError(f"Status '{status}' is not valid.")

        self.db.add(document)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(document)
        return document

    def update_document(self, document_id: int, document_data: DocumentUpdate | dict[str, Any]) -> Document:
        document = self.get_document(document_id)
        payload = (
            document_data.model_dump(exclude_unset=True)
            if isinstance(document_data, DocumentUpdate)
            else dict(document_data)
        )

        if not payload:
            return document

        if "title" in payload and payload["title"] is not None:
            document.title = validate_document_title(payload["title"])
        if "description" in payload:
            document.description = payload["description"]
        if "category" in payload and payload["category"] is not None:
            document.category = payload["category"]
        if "source" in payload and payload["source"] is not None:
            document.source = payload["source"]
        if "document_date" in payload:
            document.document_date = payload["document_date"]

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(document)
        return document

    def update_status(self, document_id: int, new_status: str) -> Document:
        document = self.get_document(document_id)
        normalized_status = new_status.upper()
        current_status = document.status.upper()

        if normalized_status == current_status:
            return document

        if normalized_status not in VALID_STATUSES:
            raise ValueError(f"Status must be one of: {', '.join(VALID_STATUSES)}.")

        allowed_transitions = VALID_STATUS_TRANSITIONS.get(current_status, set())
        if normalized_status not in allowed_transitions:
            raise InvalidStatusTransitionError(current_status, normalized_status)

        document.status = normalized_status
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        self.db.refresh(document)
        return document

    def delete_document(self, document_id: int) -> None:
        document = self.get_document(document_id)
        FileService.delete_file(document.file_path)
        self.db.delete(document)
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
