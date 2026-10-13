# AI Research Assistant

Upload PDF research papers and ask questions — powered by Google Gemini + RAG (Retrieval-Augmented Generation).

## How it works

1. **Upload** a PDF → text is extracted, chunked, and embedded into a FAISS vector index
2. **Ask a question** → the top-5 most relevant chunks are retrieved and sent to Gemini as context
3. **Gemini answers** with a streamed, cited, markdown-formatted response

## Stack

| Layer | Tech |
|---|---|
| LLM | Google Gemini (gemini-2.5-flash) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | FAISS (in-memory) |
| PDF parsing | PyMuPDF (fitz) |
| Backend | Flask + SSE streaming |
| Frontend | Vanilla HTML/CSS/JS |

## Setup

### 1. Clone & install

```bash
cd backend
pip install -r requirements.txt
```

### 2. Set your API key

```bash
export GEMINI_API_KEY=your_gemini_api_key
```

Or create a `.env` file in `/backend`:
```
GEMINI_API_KEY=your_gemini_api_key
```

### 3. Run the backend

```bash
cd backend
python app.py
```

Backend starts at `http://localhost:5000`.

### 4. Open the frontend

Open `frontend/index.html` in your browser (or serve it):

```bash
cd frontend
python -m http.server 8080
# then open http://localhost:8080
```

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check |
| POST | `/api/upload` | Upload a PDF |
| GET | `/api/documents` | List uploaded docs |
| DELETE | `/api/documents/<filename>` | Remove a document |
| POST | `/api/query` | Ask a question (SSE stream) |

## Notes

- Documents are stored in `/uploads/` and re-indexed on restart if re-uploaded
- The vector index is **in-memory** — it resets on server restart
- Max file size: 20 MB
- Supports multiple PDFs simultaneously
