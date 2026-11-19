from __future__ import annotations

import mimetypes
import os
import shutil
import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile

from app.config import ALLOWED_EXTENSIONS, MAX_FILE_SIZE_BYTES, UPLOAD_DIR
from app.exceptions import UnsupportedFileFormatError, UploadValidationError


class FileService:
    """Validate, secure, and persist uploaded document files."""

    SUPPORTED_EXTENSIONS = {".pdf", ".doc", ".docx", ".txt", ".rtf"}
    SUPPORTED_MIME_TYPES = {
        ".pdf": "application/pdf",
        ".doc": "application/msword",
        ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ".txt": "text/plain",
        ".rtf": "application/rtf",
    }

    @classmethod
    def validate_file(cls, file: UploadFile) -> tuple[str, str, int, str]:
        if not file or not file.filename:
            raise UploadValidationError("Missing uploaded file.")

        original_name = file.filename
        safe_name = Path(original_name).name
        if safe_name != original_name or ".." in Path(original_name).parts:
            raise UploadValidationError("Invalid file name provided.")

        extension = Path(safe_name).suffix.lower()
        allowed_exts = {ext if ext.startswith(".") else f".{ext}" for ext in ALLOWED_EXTENSIONS}
        if extension not in allowed_exts or extension not in cls.SUPPORTED_EXTENSIONS:
            raise UnsupportedFileFormatError(safe_name)

        mime_type = file.content_type or mimetypes.guess_type(safe_name)[0] or ""
        expected_mime = cls.SUPPORTED_MIME_TYPES.get(extension)
        if mime_type and expected_mime and mime_type.lower() != expected_mime.lower():
            raise UnsupportedFileFormatError(safe_name)

        file.file.seek(0, os.SEEK_END)
        size = file.file.tell()
        file.file.seek(0)
        if size <= 0:
            raise UploadValidationError("Uploaded file is empty.")
        if size > MAX_FILE_SIZE_BYTES:
            raise UploadValidationError(
                f"File exceeds the maximum allowed size of {MAX_FILE_SIZE_BYTES // (1024 * 1024)} MB."
            )

        return safe_name, extension, size, mime_type or expected_mime

    @classmethod
    def save_upload(cls, file: UploadFile) -> dict[str, str | int]:
        original_name, extension, size, mime_type = cls.validate_file(file)
       
        upload_dir = UPLOAD_DIR.resolve()
        upload_dir.mkdir(parents=True, exist_ok=True)

        stored_name = f"{uuid.uuid4().hex}{extension}"
        destination = upload_dir / stored_name
        while destination.exists():
            stored_name = f"{uuid.uuid4().hex}{extension}"
            destination = upload_dir / stored_name

        with destination.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "original_filename": original_name,
            "stored_filename": stored_name,
            "file_path": str(destination),
            "file_size": size,
            "mime_type": mime_type,
        }

    @staticmethod
    def get_upload_path(file_path: str | None) -> Path:
        if not file_path:
            raise HTTPException(status_code=404, detail="This document has no associated file.")

        target = Path(file_path).resolve()
        base_dir = UPLOAD_DIR.resolve()
        if not target.is_relative_to(base_dir):
            raise UploadValidationError("Refusing to access files outside the upload directory.")
        if not target.is_file():
            raise HTTPException(status_code=404, detail="The document file is missing from storage.")
        return target

    @staticmethod
    def delete_file(file_path: str | None) -> None:
        if not file_path:
            return
        target = Path(file_path).resolve()
        base_dir = UPLOAD_DIR.resolve()
        if not target.is_relative_to(base_dir):
            raise UploadValidationError("Refusing to delete files outside the upload directory.")
        if target.exists() and target.is_file():
            target.unlink()
