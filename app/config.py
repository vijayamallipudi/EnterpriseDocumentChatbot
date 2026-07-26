from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.2:1b"
    ollama_embed_model: str = "nomic-embed-text"
    ollama_num_ctx: int = 8192

    chroma_dir: str = "data/chroma"
    upload_dir: str = "data/uploads"
    document_registry: str = "data/documents.json"

    chunk_size: int = 1000
    chunk_overlap: int = 150

    retriever_k: int = 4

    @property
    def chroma_path(self) -> Path:
        path = BASE_DIR / self.chroma_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def upload_path(self) -> Path:
        path = BASE_DIR / self.upload_dir
        path.mkdir(parents=True, exist_ok=True)
        return path

    @property
    def registry_path(self) -> Path:
        path = BASE_DIR / self.document_registry
        path.parent.mkdir(parents=True, exist_ok=True)
        return path


settings = Settings()
