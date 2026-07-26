from collections.abc import Iterator

from langchain_core.documents import Document
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_ollama import ChatOllama

from app.config import settings
from app.models import ChatResponse, SourceChunk
from app.vectorstore import get_vectorstore

SYSTEM_PROMPT = (
    "You are an enterprise document assistant. Answer the user's question using "
    "ONLY the context excerpts provided below. If the context does not contain "
    "the answer, say you don't have enough information in the uploaded documents "
    "-- do not make anything up. Be concise and cite sources by filename."
)


def _get_llm() -> ChatOllama:
    return ChatOllama(
        model=settings.ollama_chat_model,
        base_url=settings.ollama_base_url,
        temperature=0.2,
        num_ctx=settings.ollama_num_ctx,
    )


def _retrieve(question: str) -> list[Document]:
    retriever = get_vectorstore().as_retriever(search_kwargs={"k": settings.retriever_k})
    return retriever.invoke(question)


def _build_messages(question: str, docs: list[Document]) -> list[BaseMessage]:
    if docs:
        context = "\n\n".join(
            f"[Source: {d.metadata.get('filename', 'unknown')}]\n{d.page_content}" for d in docs
        )
    else:
        context = "(no relevant documents found)"

    return [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"Context excerpts:\n{context}\n\nQuestion: {question}"),
    ]


def _to_sources(docs: list[Document]) -> list[SourceChunk]:
    return [
        SourceChunk(
            document_id=d.metadata.get("document_id", ""),
            filename=d.metadata.get("filename", "unknown"),
            snippet=d.page_content[:280],
        )
        for d in docs
    ]


def ask(question: str) -> ChatResponse:
    docs = _retrieve(question)
    messages = _build_messages(question, docs)

    result = _get_llm().invoke(messages)
    answer = result.content if isinstance(result.content, str) else str(result.content)

    return ChatResponse(answer=answer, sources=_to_sources(docs))


def stream_ask(question: str) -> Iterator[dict]:
    """Yields {"type": "sources", ...}, then {"type": "token", "text": ...} chunks, then {"type": "done"}."""
    docs = _retrieve(question)
    messages = _build_messages(question, docs)

    yield {"type": "sources", "sources": [s.model_dump() for s in _to_sources(docs)]}

    for part in _get_llm().stream(messages):
        text = part.content if isinstance(part.content, str) else str(part.content)
        if text:
            yield {"type": "token", "text": text}

    yield {"type": "done"}
