# Enterprise Document Chatbot (Local RAG)

Upload a PDF, DOCX, or text file and ask questions about it in plain English.
Answers are grounded in your documents and cite the source file — powered by a
retrieval-augmented generation (RAG) pipeline built with LangChain, and running
**entirely locally**: no OpenAI or Pinecone accounts, no API keys, no per-query cost.

- **LLM + embeddings**: [Ollama](https://ollama.com) (`llama3.2:1b` for chat, `nomic-embed-text` for embeddings)
- **Vector store**: [Chroma](https://www.trychroma.com/) (persisted to disk)
- **Orchestration**: LangChain
- **API**: FastAPI, with streaming responses
- **UI**: a minimal static chat + upload page
- **Answers are source-grounded**: every response cites the filename(s) it drew from, and the model is instructed to say when it doesn't know rather than guess

## Prerequisites

1. [Ollama](https://ollama.com) installed and running.
2. Pull the models used by default:
   ```
   ollama pull llama3.2:1b
   ollama pull nomic-embed-text
   ```
   (Both are already installed on this machine.)
3. Python 3.11+

## Setup

```bash
cd enterprise-doc-chatbot
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # macOS/Linux

pip install -r requirements.txt
copy .env.example .env        # Windows: copy, macOS/Linux: cp
```

Edit `.env` if you want a different Ollama model or host.

> **Performance note:** on CPU-only machines (no GPU), the default `llama3.2:1b` model is noticeably faster than the full 3B `llama3.2`. If you have a GPU or don't mind slower, more capable answers, set `OLLAMA_CHAT_MODEL=llama3.2` in `.env` instead.

## Run

```bash
uvicorn app.main:app --reload --port 8000
```

Open http://localhost:8000 — upload a PDF/DOCX/TXT/MD file in the sidebar, then ask questions about it in the chat panel.

## API

- `POST /api/documents` — upload + ingest a document (multipart form field `file`)
- `GET /api/documents` — list ingested documents
- `DELETE /api/documents/{id}` — remove a document and its vectors
- `POST /api/chat` — `{ "question": "..." }` -> full answer + cited sources (waits for the whole response)
- `POST /api/chat/stream` — same request body, streams newline-delimited JSON events (`{"type": "sources", ...}`, `{"type": "token", "text": "..."}`, `{"type": "done"}`) as the model generates. The web UI uses this one so the answer appears incrementally instead of showing a long silent wait.

Each question is answered independently (no conversation memory) -- this is a deliberate choice: with a small local model, carrying prior turns in the prompt made it lose track of the current question and answer a previous one instead (see "Known limitations" below).

## How it works

1. **Ingest**: uploaded files are loaded (`PyPDFLoader` / `Docx2txtLoader` / `TextLoader`), split into ~1000-character overlapping chunks, embedded with `nomic-embed-text` via Ollama, and upserted into a local Chroma collection tagged with `document_id`/`filename` metadata.
2. **Chat**: the question is embedded and used to retrieve the top-k similar chunks from Chroma. Those chunks are sent to the chat model via Ollama with instructions to answer only from the provided context and cite filenames.
3. **Delete**: removing a document deletes its chunk vectors from Chroma by id and drops it from the local JSON document registry (`data/documents.json`).

## Known limitations

- **No conversation memory.** Each question is answered independently from retrieved context only. This was a deliberate fix: with `llama3.2:1b`, feeding prior Q&A turns back into the prompt made the model occasionally answer an *earlier* question instead of the current one (e.g. asking "what's the grading policy?" after "who's the professor?" returned a hallucinated professor email instead). If you switch to a larger/more capable model, re-adding history in `app/rag.py` (`_build_messages` / `ask` / `stream_ask`) would let follow-up questions like "what about its due date?" work, at the risk of this failure mode returning on weaker models.

## Swapping in cloud APIs later

The local stack was chosen to avoid API costs/keys. If you later want OpenAI + Pinecone instead:
- Replace `OllamaEmbeddings`/`ChatOllama` in `app/vectorstore.py` and `app/rag.py` with `OpenAIEmbeddings`/`ChatOpenAI` (`langchain-openai`).
- Replace `Chroma` in `app/vectorstore.py` with `PineconeVectorStore` (`langchain-pinecone`), pointing at a Pinecone index.
- Everything else (ingestion, API routes, UI) stays the same.
