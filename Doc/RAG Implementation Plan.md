# RAG Implementation Plan — TechAssist Knowledge Base

**Status:** Planned — not yet implemented
**Estimated build time:** 3–4 hours
**Complexity:** Medium
**Risk:** Low — purely additive, nothing existing breaks

---

## What This Adds

Right now Vishnu searches the open internet (Tavily) when he needs documentation.

After this implementation, Vishnu will first search **your internal knowledge base** — IT runbooks, company guides, past resolved tickets, FAQs — before touching the internet. The result is company-specific, accurate answers instead of generic web results.

**Answer quality chain after RAG:**
```
1. Your internal documents (RAG)   ← highest trust
2. Tavily web search               ← fallback if no internal match
3. Claude's own training knowledge ← last resort
```

---

## Folder Structure After Implementation

```
backend/
├── rag/
│   ├── __init__.py
│   ├── embedder.py          ← converts text to vectors using Anthropic embeddings
│   ├── retriever.py         ← searches ChromaDB for relevant chunks
│   ├── ingestor.py          ← reads uploaded files, chunks them, stores in DB
│   └── chroma_db/           ← local vector database (auto-created, gitignored)
├── services/
│   ├── claude.py            ← unchanged
│   ├── search.py            ← unchanged
│   └── rag_service.py       ← NEW: orchestrates RAG lookup, called before Tavily
├── routers/
│   ├── messages.py          ← small addition: call rag_service before Claude
│   └── knowledge.py         ← NEW: upload/list/delete knowledge base documents
├── models/
│   └── knowledge.py         ← NEW: SQLAlchemy model to track uploaded documents
└── uploads/
    └── knowledge/           ← uploaded PDFs, DOCXs, TXTs stored here

frontend/src/
└── pages/
    └── Admin.jsx            ← add "Knowledge Base" tab with upload UI
```

---

## Part 1 — Dependencies

Add these to `requirements.txt`:

```
chromadb==0.5.0
sentence-transformers==3.0.1
pypdf2==3.0.1
python-docx==1.1.0
```

**What each does:**

| Package | Purpose |
|---|---|
| `chromadb` | Local vector database. Stores and searches embeddings. No external service, runs on your machine. |
| `sentence-transformers` | Converts text to vectors (embeddings). Uses a small local model — no API cost. |
| `pypdf2` | Reads PDF files so their text can be extracted and embedded. |
| `python-docx` | Reads Word (.docx) files same way. |

**Why not Anthropic embeddings?**
Anthropic's embedding API costs money per call. `sentence-transformers` runs a small model locally for free and is accurate enough for IT support documents. You can swap to Anthropic embeddings later if you want higher accuracy.

---

## Part 2 — The Vector Database (ChromaDB)

ChromaDB is a local database that stores text as vectors (number arrays that capture meaning).

### How it works:

```
"Outlook crashes on startup Windows 11"
         ↓  sentence-transformers model
[0.23, 0.87, 0.12, 0.54, 0.91, ...]   ← 384 numbers representing meaning
         ↓
Stored in ChromaDB with the original text attached
```

When a user asks a question:
```
"My email app won't open"
         ↓  same model
[0.21, 0.89, 0.14, 0.51, 0.88, ...]
         ↓
ChromaDB finds stored chunks with similar number patterns
         ↓
Returns: "Outlook crashes on startup Windows 11" chunk  ← close enough
```

This is why it finds matches even when the words are different. It's matching **meaning**, not words.

### ChromaDB collection structure:

```python
# One collection for all knowledge base documents
collection_name = "techassist_knowledge"

# Each chunk stored with:
{
    "id": "doc_001_chunk_003",
    "embedding": [0.23, 0.87, ...],   # 384-dim vector
    "document": "The actual text of this chunk...",
    "metadata": {
        "source_file": "VPN Setup Guide.pdf",
        "doc_id": 1,
        "chunk_index": 3,
        "category": "Network",
        "uploaded_at": "2026-03-14"
    }
}
```

---

## Part 3 — File: `rag/embedder.py`

Responsible for converting text into vectors.

```python
from sentence_transformers import SentenceTransformer
from functools import lru_cache

MODEL_NAME = "all-MiniLM-L6-v2"   # 80MB model, fast, accurate enough for IT docs

@lru_cache(maxsize=1)
def get_model() -> SentenceTransformer:
    """Load model once, reuse forever."""
    return SentenceTransformer(MODEL_NAME)

def embed_text(text: str) -> list[float]:
    """Convert a string to a vector."""
    model = get_model()
    return model.encode(text, normalize_embeddings=True).tolist()

def embed_batch(texts: list[str]) -> list[list[float]]:
    """Convert a list of strings to vectors in one batch (faster)."""
    model = get_model()
    return model.encode(texts, normalize_embeddings=True).tolist()
```

**Why `all-MiniLM-L6-v2`?**
- 80MB download (happens once on first run)
- 384-dimensional vectors — good balance of accuracy vs speed
- Designed for semantic similarity tasks — exactly what RAG needs
- Runs on CPU, no GPU needed

---

## Part 4 — File: `rag/ingestor.py`

Responsible for reading uploaded files, splitting into chunks, and storing in ChromaDB.

### Chunking strategy:

Why chunk? Because you can't embed an entire 50-page PDF as one vector — the meaning gets diluted. You split it into small pieces (chunks) so each chunk has a focused meaning.

```
"VPN Setup Guide.pdf"  (50 pages)
         ↓  split into chunks
Chunk 1: "VPN Overview - TechAssist uses Cisco AnyConnect 4.10..."
Chunk 2: "Installation - Download the installer from IT Portal..."
Chunk 3: "Certificate Error - If you see 'Untrusted Server'..."
Chunk 4: "Split Tunneling - To enable split tunneling, go to..."
...
Chunk 47: "Troubleshooting - Common errors and their fixes..."
```

Each chunk is 300–500 words with 50-word overlap between chunks so context isn't cut off at boundaries.

### The ingestor code plan:

```python
import chromadb
from pathlib import Path
from rag.embedder import embed_batch

CHROMA_PATH = Path(__file__).parent / "chroma_db"
CHUNK_SIZE = 400    # words per chunk
CHUNK_OVERLAP = 50  # words overlap between chunks

def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name="techassist_knowledge",
        metadata={"hnsw:space": "cosine"}   # cosine similarity for text
    )

def ingest_file(file_path: Path, doc_id: int, category: str = "General") -> int:
    """
    Read a file, chunk it, embed all chunks, store in ChromaDB.
    Returns number of chunks created.
    """
    text = _extract_text(file_path)
    chunks = _chunk_text(text, CHUNK_SIZE, CHUNK_OVERLAP)
    embeddings = embed_batch(chunks)

    collection = get_collection()
    collection.add(
        ids=[f"doc_{doc_id}_chunk_{i}" for i in range(len(chunks))],
        embeddings=embeddings,
        documents=chunks,
        metadatas=[{
            "doc_id": doc_id,
            "source_file": file_path.name,
            "chunk_index": i,
            "category": category,
        } for i in range(len(chunks))]
    )
    return len(chunks)

def delete_document(doc_id: int):
    """Remove all chunks for a document (when user deletes it from admin)."""
    collection = get_collection()
    results = collection.get(where={"doc_id": doc_id})
    if results["ids"]:
        collection.delete(ids=results["ids"])

def _extract_text(file_path: Path) -> str:
    suffix = file_path.suffix.lower()
    if suffix == ".pdf":
        return _read_pdf(file_path)
    elif suffix == ".docx":
        return _read_docx(file_path)
    elif suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")

def _chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    words = text.split()
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))
        start += chunk_size - overlap
    return [c for c in chunks if len(c.strip()) > 50]  # skip tiny chunks
```

---

## Part 5 — File: `rag/retriever.py`

Responsible for searching ChromaDB at runtime when a user sends a message.

```python
import chromadb
from pathlib import Path
from rag.embedder import embed_text
from config import get_settings

CHROMA_PATH = Path(__file__).parent / "chroma_db"
settings = get_settings()

def retrieve(query: str, n_results: int = 3, category: str = None) -> list[dict]:
    """
    Search the knowledge base for chunks relevant to `query`.

    Returns list of dicts:
        [{"text": "...", "source": "VPN Guide.pdf", "score": 0.87}, ...]

    Returns [] if knowledge base is empty or no good match found.
    """
    try:
        client = chromadb.PersistentClient(path=str(CHROMA_PATH))
        collection = client.get_collection("techassist_knowledge")
    except Exception:
        return []   # collection doesn't exist yet — no docs uploaded

    query_embedding = embed_text(query)

    where_filter = {"category": category} if category else None

    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results,
        where=where_filter,
        include=["documents", "metadatas", "distances"]
    )

    output = []
    for i, doc in enumerate(results["documents"][0]):
        distance = results["distances"][0][i]
        score = 1 - distance           # cosine distance → similarity score
        if score >= settings.rag_match_threshold:   # only return good matches
            output.append({
                "text": doc,
                "source": results["metadatas"][0][i]["source_file"],
                "score": round(score, 3),
            })

    return output
```

**Score threshold (configurable in `.env`):**

| Score | Meaning |
|---|---|
| 0.90+ | Near-identical match |
| 0.75–0.90 | Strong match — use it |
| 0.60–0.75 | Weak match — borderline |
| < 0.60 | Unrelated — skip it |

Default threshold: `0.70` — good balance between recall and precision.

---

## Part 6 — Wiring RAG into the Message Flow

This is the key change in `routers/messages.py`. It sits between "build conversation history" and "call Claude":

**Before RAG (current flow):**
```python
# Build claude_history from DB messages
claude_history = [...]

# Check solution memory (keyword match)
matched = find_matching_solution(...)

# Call Claude
result = process_chat_turn(claude_history, ticket.failed_attempts)
```

**After RAG (new flow):**
```python
# Build claude_history from DB messages
claude_history = [...]

# 1. Check RAG knowledge base (semantic search — highest priority)
rag_results = retrieve(req.content, n_results=3, category=ticket.category)
if rag_results:
    rag_block = _build_rag_context(rag_results)
    claude_history[0]["content"] += rag_block

# 2. Check solution memory (keyword match — second priority)
# (existing code, unchanged)
matched = find_matching_solution(...)

# 3. Call Claude (Tavily search still happens inside claude.py if needed)
result = process_chat_turn(claude_history, ticket.failed_attempts)
```

**The `_build_rag_context` helper:**
```python
def _build_rag_context(results: list[dict]) -> str:
    block = "\n\n[INTERNAL KNOWLEDGE BASE — use this before searching the web]\n"
    for r in results:
        block += f"\nSource: {r['source']} (relevance: {r['score']})\n"
        block += f"{r['text']}\n"
    block += "[/INTERNAL KNOWLEDGE BASE]"
    return block
```

Vishnu sees the internal docs in his context and uses them first. If the docs answer the question, the `[SEARCH: ...]` token never appears and Tavily is never called.

---

## Part 7 — New Config Settings

Add to `config.py`:

```python
rag_match_threshold: float = 0.70     # minimum similarity score to use a chunk
rag_max_results: int = 3              # max chunks to inject per message
rag_enabled: bool = True              # kill switch — set False to disable RAG
```

Add to `.env`:
```
RAG_MATCH_THRESHOLD=0.70
RAG_MAX_RESULTS=3
RAG_ENABLED=true
```

---

## Part 8 — New Database Model: `models/knowledge.py`

Tracks what documents have been uploaded (metadata only — the actual vectors live in ChromaDB):

```python
class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id          = Column(Integer, primary_key=True, autoincrement=True)
    filename    = Column(String(255), nullable=False)
    original_name = Column(String(255), nullable=False)
    category    = Column(String(50), default="General")
    chunk_count = Column(Integer, default=0)
    file_size   = Column(Integer)           # bytes
    uploaded_by = Column(String(100))
    uploaded_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_active   = Column(Boolean, default=True)
```

---

## Part 9 — New Router: `routers/knowledge.py`

Endpoints for the Admin page to manage the knowledge base:

| Method | Endpoint | What it does |
|---|---|---|
| `POST` | `/api/v1/knowledge/upload` | Upload a PDF/DOCX/TXT, ingest into ChromaDB |
| `GET` | `/api/v1/knowledge/documents` | List all uploaded documents |
| `DELETE` | `/api/v1/knowledge/documents/{id}` | Delete document + remove its vectors |
| `GET` | `/api/v1/knowledge/search?q=...` | Test search — see what RAG would return for a query |

**Upload endpoint logic:**
```
1. Accept file (PDF, DOCX, TXT, MD — max 10MB)
2. Save to uploads/knowledge/
3. Create KnowledgeDocument record in SQLite
4. Call ingestor.ingest_file() → chunks and embeds
5. Update chunk_count on the DB record
6. Return { id, filename, chunk_count, status: "embedded" }
```

---

## Part 10 — Frontend: Admin Page Knowledge Base Tab

Add a new tab to the existing Admin page at `frontend/src/pages/Admin.jsx`:

```
Admin Page
├── Analytics Tab (existing)
├── Solutions Tab (existing)
└── Knowledge Base Tab (NEW)
    ├── Upload Section
    │   ├── Drag-and-drop / file picker
    │   ├── Category dropdown (Network / Software / Hardware / Access / General)
    │   └── Upload button
    │
    ├── Documents Table
    │   ├── Filename | Category | Chunks | Uploaded | Actions
    │   ├── "VPN Setup Guide.pdf" | Network | 47 chunks | 2026-03-14 | [Delete]
    │   └── "Outlook Troubleshooting.docx" | Software | 32 chunks | 2026-03-14 | [Delete]
    │
    └── Test Search (optional but useful)
        ├── Input: "wifi not connecting"
        └── Shows what RAG would return → validates your knowledge base
```

---

## Part 11 — What Documents to Upload (Examples)

When you're ready to use this, these are the kinds of documents that give the best results:

| Document type | Example | Why it helps |
|---|---|---|
| IT runbooks | `VPN Setup for Remote Staff.pdf` | Company-specific VPN config, not generic Cisco docs |
| Known issue guides | `Common Outlook Issues and Fixes.docx` | Covers the top 20 issues you see every month |
| Software setup guides | `Onboarding - New Laptop Setup.pdf` | Exact steps for your environment |
| Network docs | `Office WiFi and Network Info.docx` | Your SSIDs, DNS servers, proxy settings |
| Policy docs | `Password Policy and MFA Setup.pdf` | Exact requirements for your org |
| Past ticket exports | `Resolved Tickets Q1 2026.txt` | Real solutions that worked for real users |

---

## Part 12 — Implementation Order (Step by Step)

When you're ready to build this, do it in this exact order to avoid breaking anything:

```
Step 1 — Install dependencies
  pip install chromadb sentence-transformers pypdf2 python-docx
  Add to requirements.txt

Step 2 — Create rag/ folder and files
  rag/__init__.py
  rag/embedder.py
  rag/ingestor.py
  rag/retriever.py

Step 3 — Add config settings
  config.py — add rag_match_threshold, rag_max_results, rag_enabled
  .env — add RAG_ variables

Step 4 — Add database model
  models/knowledge.py
  database.py — init_db() already imports all models, just add the import

Step 5 — Add knowledge router
  routers/knowledge.py
  main.py — include_router(knowledge.router)

Step 6 — Wire RAG into messages.py
  Import retrieve from rag.retriever
  Add 5 lines before the Claude call

Step 7 — Frontend Admin tab
  Admin.jsx — add Knowledge Base tab
  Add upload/list/delete API calls to client.js

Step 8 — Test
  Upload a test document
  Ask a question that matches its content
  Confirm Vishnu uses the document content
  Confirm Tavily is NOT called when RAG answers the question
```

---

## Part 13 — What Does NOT Change

- `claude.py` — completely unchanged
- `search.py` (Tavily) — still runs, just runs less often
- All existing endpoints — unchanged
- The database schema for tickets/messages — unchanged
- The system prompt — unchanged (Vishnu already knows to use internal docs from context)
- All existing frontend pages — only Admin.jsx gets a new tab

RAG is purely additive. You can turn it off any time with `RAG_ENABLED=false` in `.env`.

---

## Summary

| | Before RAG | After RAG |
|---|---|---|
| Answer source | Tavily (internet) + Claude training | Your docs → Tavily → Claude training |
| Company-specific accuracy | Low | High |
| Hallucination risk | Medium | Low (grounded in real docs) |
| Answer for "our VPN config" | Generic Cisco docs | Your exact IT runbook |
| Cost | Tavily API per search | One-time embedding + free retrieval |
| Setup needed | None | Upload your documents once |
