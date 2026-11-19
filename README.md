# Document Management Service

A FastAPI service for registering business documents, organizing them by category,
tracking status, and associating securely stored files. SQLite is the default
database; document metadata survives application restarts.

## Run locally

From the project directory in PowerShell:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) for the document
management dashboard, or [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
for the interactive Swagger UI. The dashboard supports filtering, registering,
uploading, editing, status changes, downloads, and deletion. By default,
metadata is stored in `documents.db` and uploaded files are stored under `uploads\`. Set `DATABASE_URL`, `UPLOAD_DIR`,
`MAX_FILE_SIZE_MB`, or `ALLOWED_EXTENSIONS` to customize these locations and
limits. Copy `.env.example` to `.env` to start configuring the service.

## Document lifecycle operations

| Operation | Endpoint | Purpose |
| --- | --- | --- |
| Register metadata | `POST /api/documents/` | Create a document record without a file |
| Register and upload | `POST /api/documents/upload` | Save an allowed file and its metadata |
| List and filter | `GET /api/documents/` | List records; optionally filter by `category` or `status` |
| Get details | `GET /api/documents/{document_id}` | Retrieve a record |
| Download file | `GET /api/documents/{document_id}/file` | Download the associated file |
| Update metadata | `PUT /api/documents/{document_id}` | Update title, description, category, source, or date |
| Change status | `PATCH /api/documents/{document_id}/status` | Advance a document through valid lifecycle states |
| Delete | `DELETE /api/documents/{document_id}` | Delete the record and its stored file |

Statuses are `RECEIVED`, `PROCESSING`, `AVAILABLE`, `ARCHIVED`, and `FAILED`.
Transitions are intentionally restricted: `RECEIVED` to `PROCESSING`,
`PROCESSING` to `AVAILABLE` or `FAILED`, and `AVAILABLE` to `ARCHIVED`.

Uploads accept `.pdf`, `.doc`, `.docx`, `.txt`, or `.rtf` files, subject to the
configured extension list and size limit. API input validation returns 422;
missing records/files return 404; invalid state transitions and unsupported
uploads return clear 400 responses.

## Database design

The `documents` table stores a record ID, title, description, category, source,
document date, lifecycle status, upload filename/path/size/MIME type, and
created/updated timestamps. The uploaded file itself lives in `uploads\`; the
database stores its generated storage name and path. SQLite's `documents.db`
persists the records across restarts.

Run the automated checks with:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

## Two-minute demo walkthrough

1. Start the server and open `/docs`; point out the generated OpenAPI operations.
2. Use `POST /api/documents/upload` with a small `.txt` file and its title,
   category, source, and optional ISO-8601 date. Show the returned ID and stored
   file details.
3. Use `GET /api/documents/` with a category filter, then retrieve that ID and
   download its associated file.
4. Update metadata, move its status from `RECEIVED` to `PROCESSING`, then list
   by status.
5. Show the `documents` table in `documents.db` using a SQLite viewer, then
   restart the server and fetch the same document again.
6. Submit a deliberately invalid status transition (for example
   `RECEIVED` to `ARCHIVED`) and show the clear 400 response.
