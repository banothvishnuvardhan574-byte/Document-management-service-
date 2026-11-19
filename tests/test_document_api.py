from __future__ import annotations

import sys

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    db_path = tmp_path / "documents.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("UPLOAD_DIR", str(tmp_path / "uploads"))

    for module_name in [
        "app.config",
        "app.database",
        "app.models",
        "app.dependencies",
        "app.services.document_service",
        "app.services.file_service",
        "app.routers.documents",
        "app.main",
    ]:
        sys.modules.pop(module_name, None)

    import app.main  # noqa: F401

    with TestClient(app.main.app) as test_client:
        yield test_client


def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["success"] is True
    assert payload["message"] == "Service is healthy"

    docs_response = client.get("/docs")
    openapi_response = client.get("/openapi.json")
    assert docs_response.status_code == 200
    assert openapi_response.status_code == 200
    paths = openapi_response.json()["paths"]
    assert "/api/documents/upload" in paths
    assert "/api/documents/{document_id}/file" in paths
    assert "/api/documents/{document_id}/status" in paths


def test_dashboard_is_served(client):
    response = client.get("/")
    assert response.status_code == 200
    assert "Document workspace" in response.text
    assert "Add document" in response.text


def test_document_lifecycle(client):
    create_response = client.post(
        "/api/documents/",
        json={
            "title": "Quarterly Report",
            "description": "Q4 financial summary",
            "category": "finance",
            "source": "manual",
            "document_date": "2026-10-15T00:00:00",
        },
    )

    assert create_response.status_code == 201, create_response.text
    document = create_response.json()
    assert document["title"] == "Quarterly Report"
    assert document["status"] == "RECEIVED"

    list_response = client.get("/api/documents/")
    assert list_response.status_code == 200
    payload = list_response.json()
    assert len(payload) == 1
    assert payload[0]["id"] == document["id"]

    status_response = client.patch(
        f"/api/documents/{document['id']}/status",
        json={"status": "PROCESSING"},
    )
    assert status_response.status_code == 200, status_response.text
    assert status_response.json()["status"] == "PROCESSING"

    delete_response = client.delete(f"/api/documents/{document['id']}")
    assert delete_response.status_code == 200
    assert delete_response.json()["success"] is True


def test_document_persists_after_database_connection_reopen(client):
    created = client.post(
        "/api/documents/",
        json={"title": "Persistent record", "category": "finance", "source": "manual"},
    )
    assert created.status_code == 201

    import app.database as database_module

    database_module.engine.dispose()
    reloaded = client.get(f"/api/documents/{created.json()['id']}")
    assert reloaded.status_code == 200
    assert reloaded.json()["title"] == "Persistent record"


def test_upload_filter_download_and_validation(client):
    upload_response = client.post(
        "/api/documents/upload",
        data={
            "title": "Team Notes",
            "description": "Meeting notes",
            "category": "operations",
            "source": "email",
            "document_date": "2026-11-17T10:00:00",
        },
        files={"file": ("notes.txt", b"Meeting notes", "text/plain")},
    )
    assert upload_response.status_code == 201, upload_response.text
    document = upload_response.json()
    assert document["original_filename"] == "notes.txt"
    assert document["stored_filename"]
    assert document["file_size"] == len(b"Meeting notes")

    filtered = client.get("/api/documents/", params={"category": "operations", "status": "received"})
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()] == [document["id"]]

    download = client.get(f"/api/documents/{document['id']}/file")
    assert download.status_code == 200
    assert download.content == b"Meeting notes"

    invalid_transition = client.patch(
        f"/api/documents/{document['id']}/status",
        json={"status": "ARCHIVED"},
    )
    assert invalid_transition.status_code == 400
    assert "Invalid status transition" in invalid_transition.json()["detail"]

    invalid_status = client.patch(
        f"/api/documents/{document['id']}/status",
        json={"status": "UNKNOWN"},
    )
    assert invalid_status.status_code == 422
    assert "Status must be one of" in invalid_status.json()["detail"][0]["msg"]

    unsupported_upload = client.post(
        "/api/documents/upload",
        data={"title": "Bad upload", "category": "operations", "source": "email"},
        files={"file": ("malware.exe", b"not allowed", "application/octet-stream")},
    )
    assert unsupported_upload.status_code == 400
    assert "not supported" in unsupported_upload.json()["detail"]


def test_missing_document_and_invalid_metadata_are_clear(client):
    missing = client.get("/api/documents/999")
    assert missing.status_code == 404
    assert "No document exists with ID 999" in missing.json()["detail"]

    invalid_document = client.post(
        "/api/documents/",
        json={"title": "  ", "category": "finance", "source": "manual"},
    )
    assert invalid_document.status_code == 422

    invalid_date = client.post(
        "/api/documents/upload",
        data={
            "title": "Bad date",
            "category": "finance",
            "source": "email",
            "document_date": "not-a-date",
        },
        files={"file": ("notes.txt", b"content", "text/plain")},
    )
    assert invalid_date.status_code == 400
    assert invalid_date.json()["detail"] == "document_date must be ISO-8601 formatted."
