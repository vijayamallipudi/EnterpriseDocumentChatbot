from functools import lru_cache

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from app.config import settings


@lru_cache
def get_embeddings() -> OllamaEmbeddings:
    return OllamaEmbeddings(
        model=settings.ollama_embed_model,
        base_url=settings.ollama_base_url,
    )


@lru_cache
def get_vectorstore() -> Chroma:
    return Chroma(
        collection_name="enterprise_documents",
        embedding_function=get_embeddings(),
        persist_directory=str(settings.chroma_path),
    )
