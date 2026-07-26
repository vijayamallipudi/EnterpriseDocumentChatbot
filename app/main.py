import json
import shutil
import uuid
from pathlib import Path

from fastapi import FastAPI, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from app.config import BASE_DIR, settings
from app.ingestion import UnsupportedFileType, delete_document, ingest_document
from app.models import ChatRequest, ChatResponse, DocumentInfo, UploadResponse
from app.rag import ask, stream_ask
from app.registry import get_document, list_documents

app = FastAPI(title="Enterprise Document Chatbot")


@app.get("/api/documents", response_model=list[DocumentInfo])
def get_documents() -> list[DocumentInfo]:
    return list_documents()


@app.post("/api/documents", response_model=UploadResponse)
async def upload_document(file: UploadFile) -> UploadResponse:
    suffix = Path(file.filename or "").suffix.lower()
    if suffix not in {".pdf", ".docx", ".txt", ".md"}:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {suffix}")

    dest = settings.upload_path / f"{uuid.uuid4().hex}{suffix}"
    with dest.open("wb") as out:
        shutil.copyfileobj(file.file, out)

    try:
        info = ingest_document(dest, file.filename or dest.name)
    except UnsupportedFileType as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    return UploadResponse(document=info)


@app.delete("/api/documents/{document_id}")
def delete_document_endpoint(document_id: str) -> dict:
    doc = get_document(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    delete_document(document_id, doc.chunk_count)
    return {"deleted": document_id}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")
    return ask(request.question)


@app.post("/api/chat/stream")
def chat_stream(request: ChatRequest) -> StreamingResponse:
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question must not be empty")

    def generate():
        for event in stream_ask(request.question):
            yield json.dumps(event) + "\n"

    return StreamingResponse(generate(), media_type="application/x-ndjson")


app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(BASE_DIR / "static" / "index.html"))
