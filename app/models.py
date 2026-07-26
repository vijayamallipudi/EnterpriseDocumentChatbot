from pydantic import BaseModel


class DocumentInfo(BaseModel):
    id: str
    filename: str
    uploaded_at: str
    chunk_count: int


class UploadResponse(BaseModel):
    document: DocumentInfo


class ChatRequest(BaseModel):
    question: str


class SourceChunk(BaseModel):
    document_id: str
    filename: str
    snippet: str


class ChatResponse(BaseModel):
    answer: str
    sources: list[SourceChunk]
