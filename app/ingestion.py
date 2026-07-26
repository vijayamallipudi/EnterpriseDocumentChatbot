import uuid
from datetime import datetime, timezone
from pathlib import Path

from langchain_community.document_loaders import Docx2txtLoader, PyPDFLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.config import settings
from app.models import DocumentInfo
from app.registry import add_document, remove_document
from app.vectorstore import get_vectorstore

_LOADERS = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
    ".md": TextLoader,
}


class UnsupportedFileType(ValueError):
    pass


def _chunk_ids(document_id: str, chunk_count: int) -> list[str]:
    return [f"{document_id}-{i}" for i in range(chunk_count)]


def ingest_document(file_path: Path, filename: str) -> DocumentInfo:
    suffix = Path(filename).suffix.lower()
    loader_cls = _LOADERS.get(suffix)
    if loader_cls is None:
        raise UnsupportedFileType(f"Unsupported file type: {suffix}")

    raw_docs = loader_cls(str(file_path)).load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
    )
    chunks = splitter.split_documents(raw_docs)
    if not chunks:
        raise ValueError("No extractable text found in document")

    document_id = uuid.uuid4().hex
    for i, chunk in enumerate(chunks):
        chunk.metadata["document_id"] = document_id
        chunk.metadata["filename"] = filename
        chunk.metadata["chunk_index"] = i

    ids = _chunk_ids(document_id, len(chunks))
    get_vectorstore().add_documents(chunks, ids=ids)

    info = DocumentInfo(
        id=document_id,
        filename=filename,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        chunk_count=len(chunks),
    )
    add_document(info)
    return info


def delete_document(document_id: str, chunk_count: int) -> None:
    ids = _chunk_ids(document_id, chunk_count)
    get_vectorstore().delete(ids=ids)
    remove_document(document_id)
