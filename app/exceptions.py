from __future__ import annotations

from fastapi import HTTPException, status


class DocumentNotFoundError(HTTPException):
    def __init__(self, document_id: int):
        self.message = "Document not found"
        self.error_detail = f"No document exists with ID {document_id}"
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=self.error_detail,
        )


class InvalidStatusTransitionError(HTTPException):
    def __init__(self, current_status: str, next_status: str):
        self.message = "Invalid status transition"
        self.error_detail = f"Invalid status transition: '{current_status}' -> '{next_status}'"
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=self.error_detail,
        )


class UnsupportedFileFormatError(HTTPException):
    def __init__(self, filename: str):
        self.message = "Unsupported file format"
        self.error_detail = f"File type for '{filename}' is not supported."
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=self.error_detail,
        )


class UploadValidationError(HTTPException):
    def __init__(self, message: str):
        self.message = "Upload validation failed"
        self.error_detail = message
        super().__init__(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message,
        )
