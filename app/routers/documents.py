from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.dependencies import get_session
from app.schemas import DocumentCreate, DocumentRead, DocumentStatusUpdate, DocumentUpdate
from app.services.document_service import DocumentService
from app.services.file_service import FileService

router = APIRouter(prefix="/api/documents", tags=["documents"])


@router.get("/", response_model=list[DocumentRead])
def list_documents(
    category: str | None = None,
    status: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
    db: Session = Depends(get_session),
):
    documents = DocumentService(db).list_documents(skip=skip, limit=limit, category=category, status=status)
    return documents


@router.get("/{document_id}", response_model=DocumentRead)
def get_document(document_id: int, db: Session = Depends(get_session)):
    return DocumentService(db).get_document(document_id)


@router.post("/", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
def create_document(payload: DocumentCreate, db: Session = Depends(get_session)):
    document = DocumentService(db).create_document(payload)
    return document


@router.post("/upload", response_model=DocumentRead, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    title: str = Form(...),
    description: str | None = Form(default=None),
    category: str = Form(...),
    source: str = Form(...),
    document_date: str | None = Form(default=None),
    db: Session = Depends(get_session),
):
    try:
        parsed_document_date = datetime.fromisoformat(document_date) if document_date else None
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="document_date must be ISO-8601 formatted.") from exc

    payload = DocumentCreate(
        title=title,
        description=description,
        category=category,
        source=source,
        document_date=parsed_document_date,
    )
    file_metadata = FileService.save_upload(file)
    try:
        document = DocumentService(db).create_document(payload, file_metadata=file_metadata)
    except Exception:
        FileService.delete_file(file_metadata["file_path"])
        raise
    return document


@router.get("/{document_id}/file", response_class=FileResponse)
def download_document_file(document_id: int, db: Session = Depends(get_session)):
    document = DocumentService(db).get_document(document_id)
    file_path = FileService.get_upload_path(document.file_path)
    return FileResponse(
        path=file_path,
        media_type=document.mime_type or "application/octet-stream",
        filename=document.original_filename or file_path.name,
    )


@router.put("/{document_id}", response_model=DocumentRead)
def update_document(document_id: int, payload: DocumentUpdate, db: Session = Depends(get_session)):
    return DocumentService(db).update_document(document_id, payload)


@router.patch("/{document_id}/status", response_model=DocumentRead)
def update_document_status(
    document_id: int,
    payload: DocumentStatusUpdate,
    db: Session = Depends(get_session),
):
    return DocumentService(db).update_status(document_id, payload.status)


@router.delete("/{document_id}", status_code=status.HTTP_200_OK)
def delete_document(document_id: int, db: Session = Depends(get_session)):
    DocumentService(db).delete_document(document_id)
    return {"success": True, "message": f"Document {document_id} deleted successfully."}
