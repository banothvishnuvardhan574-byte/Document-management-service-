from __future__ import annotations


def validate_document_title(title: str) -> str:
    if not title or not title.strip():
        raise ValueError("Title is required and cannot be empty.")
    return title.strip()
