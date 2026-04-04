# ── app/routes/upload.py ─────────────────────────────────────
#
# POST /api/upload
# Accepts PDF files or Jupyter notebooks (.ipynb),
# splits them into chunks, embeds them, and stores in ChromaDB.
# Each file is tagged with a week number so the RAG agent can
# retrieve only content relevant to the current lesson.

import os
import json
import tempfile
from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from fastapi.responses import JSONResponse

from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings

router = APIRouter()

# ── ChromaDB path ─────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CHROMA_DIR = os.path.join(BASE_DIR, "data", "chroma")
os.makedirs(CHROMA_DIR, exist_ok=True)

# ── Embeddings model ──────────────────────────────────────────
# all-MiniLM-L6-v2: small (80MB), fast, runs locally, free.
# Downloads once on first use, cached after that.
def get_embeddings():
    return HuggingFaceEmbeddings(
        model_name="all-MiniLM-L6-v2",
        model_kwargs={"device": "cpu"},
        encode_kwargs={"normalize_embeddings": True},
    )

# ── Text splitter ─────────────────────────────────────────────
# Splits documents into overlapping chunks.
# chunk_size=800: large enough to contain a complete concept
# chunk_overlap=100: overlap ensures context isn't lost at boundaries
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
    separators=["\n\n", "\n", ".", " "],
)


def get_vectorstore():
    """Returns the ChromaDB vector store."""
    return Chroma(
        persist_directory=CHROMA_DIR,
        embedding_function=get_embeddings(),
        collection_name="quantummind_course",
    )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    week: int = Form(...),
    # week: which week this content belongs to (1-13)
    # Used to filter retrieval — when on Week 3, only retrieve Week 3 docs
):
    """
    Upload a PDF or Jupyter notebook for a specific course week.

    The file is:
    1. Saved to a temp location
    2. Loaded and split into chunks
    3. Each chunk tagged with week number as metadata
    4. Embedded and stored in ChromaDB

    After uploading, the RAG agent can retrieve this content
    when a student asks questions in that week's lesson.
    """
    allowed_types = ["application/pdf", "application/octet-stream", "text/plain"]
    allowed_extensions = [".pdf", ".ipynb", ".py", ".md"]

    filename = file.filename or ""
    ext = os.path.splitext(filename)[1].lower()

    if ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type: {ext}. Allowed: {allowed_extensions}"
        )

    # Save uploaded file to temp location
    with tempfile.NamedTemporaryFile(
        delete=False, suffix=ext
    ) as tmp:
        content = await file.read()
        tmp.write(content)
        tmp_path = tmp.name

    try:
        # Load document based on file type
        if ext == ".pdf":
            docs = load_pdf(tmp_path)
        elif ext == ".ipynb":
            docs = load_notebook(tmp_path)
        elif ext in (".py", ".md"):
            docs = load_text(tmp_path, filename)
        else:
            docs = []

        if not docs:
            raise HTTPException(status_code=400, detail="No text could be extracted from the file.")

        # Split into chunks
        chunks = text_splitter.split_documents(docs)

        # Tag each chunk with week metadata
        for chunk in chunks:
            chunk.metadata["week"]     = week
            chunk.metadata["filename"] = filename
            chunk.metadata["source"]   = f"Week {week}: {filename}"

        # Store in ChromaDB
        vectorstore = get_vectorstore()
        vectorstore.add_documents(chunks)

        print(f"[Upload] Week {week} — {filename}: {len(chunks)} chunks stored")

        return JSONResponse({
            "status":   "success",
            "filename": filename,
            "week":     week,
            "chunks":   len(chunks),
            "message":  f"Successfully ingested {len(chunks)} chunks from {filename}",
        })

    except Exception as e:
        print(f"[Upload] Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        os.unlink(tmp_path)


def load_pdf(path: str):
    """Load and extract text from a PDF file."""
    loader = PyPDFLoader(path)
    return loader.load()


def load_notebook(path: str):
    """
    Extract text from a Jupyter notebook (.ipynb).

    Notebooks are JSON files. We extract:
    - Markdown cells → theory content
    - Code cells → Qiskit examples
    """
    from langchain_core.documents import Document

    with open(path, encoding="utf-8") as f:
        nb = json.load(f)

    docs = []
    for i, cell in enumerate(nb.get("cells", [])):
        cell_type = cell.get("cell_type", "")
        source    = "".join(cell.get("source", []))

        if not source.strip():
            continue

        # Tag cell type in metadata — useful for filtering later
        docs.append(Document(
            page_content=source,
            metadata={
                "cell_type":  cell_type,
                "cell_index": i,
            }
        ))

    return docs


def load_text(path: str, filename: str):
    """Load plain text files (.py, .md)."""
    from langchain_core.documents import Document

    with open(path, encoding="utf-8") as f:
        text = f.read()

    return [Document(page_content=text, metadata={"filename": filename})]


@router.get("/upload/status")
async def upload_status():
    """Returns how many documents are in the vector store."""
    try:
        vectorstore = get_vectorstore()
        count = vectorstore._collection.count()
        return {"status": "ok", "total_chunks": count, "chroma_dir": CHROMA_DIR}
    except Exception as e:
        return {"status": "error", "error": str(e)}