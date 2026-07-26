import json
import threading
from typing import Optional

from app.config import settings
from app.models import DocumentInfo

_lock = threading.Lock()


def _read_all() -> list[dict]:
    path = settings.registry_path
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _write_all(records: list[dict]) -> None:
    path = settings.registry_path
    with path.open("w", encoding="utf-8") as f:
        json.dump(records, f, indent=2)


def list_documents() -> list[DocumentInfo]:
    with _lock:
        return [DocumentInfo(**r) for r in _read_all()]


def get_document(doc_id: str) -> Optional[DocumentInfo]:
    for doc in list_documents():
        if doc.id == doc_id:
            return doc
    return None


def add_document(info: DocumentInfo) -> None:
    with _lock:
        records = _read_all()
        records.append(info.model_dump())
        _write_all(records)


def remove_document(doc_id: str) -> bool:
    with _lock:
        records = _read_all()
        remaining = [r for r in records if r["id"] != doc_id]
        removed = len(remaining) != len(records)
        _write_all(remaining)
        return removed
