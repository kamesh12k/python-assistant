# AI Research Assistant

Upload PDF research papers and ask questions — powered by Claude + RAG (Retrieval-Augmented Generation).

## Features

- **PDF Ingestion & Parsing**: Extracts text and metadata cleanly from uploaded research papers using PyMuPDF.
- **Smart Chunking & Embeddings**: Splits text into context-aware chunks embedded with `sentence-transformers/all-MiniLM-L6-v2`.
- **Fast Similarity Search**: In-memory FAISS vector indexing for high-speed retrieval of relevant context.
- **Real-Time Streaming Responses**: Powered by Anthropic Claude with Server-Sent Events (SSE) streaming and citation support.
- **Modern Web Interface**: Intuitive UI for uploading documents, monitoring indexed files, and interactive chat.

## Stack

| Layer | Tech |
|---|---|
| LLM | Anthropic Claude (claude-opus-4-6) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | FAISS (in-memory) |
| PDF parsing | PyMuPDF (fitz) |
| Backend | Flask + Flask-CORS + SSE streaming |
| Frontend | Vanilla HTML/CSS/JS |

## Project Structure

```
python_assistant/
├── backend/
│   ├── app.py                # Flask application & API routes
│   ├── pdf_processor.py      # PDF text extraction and chunking
│   ├── rag.py                # FAISS vector store & retrieval logic
│   ├── requirements.txt      # Python dependencies
│   └── .env.example          # Environment variables template
├── frontend/
│   ├── index.html            # User interface
│   └── README.md
├── .gitignore
└── README.md
```

## Getting Started

### 1. Clone & Install Dependencies

```bash
git clone https://github.com/kamesh12k/python-assistant.git
cd python-assistant/backend
python -m venv venv
# On Windows:
.\venv\Scripts\activate
# On Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables

Copy the example environment file and set your Anthropic API key:

```bash
cp .env.example .env
```

Edit `backend/.env`:
```env
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 3. Run the Backend Server

```bash
python app.py
```

The Flask server will start at `http://localhost:5000`.

### 4. Run the Frontend

Open `frontend/index.html` directly in your browser or run a simple HTTP server:

```bash
cd ../frontend
python -m http.server 8080
```

Open `http://localhost:8080` in your web browser.

## API Endpoints

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Health check & document count |
| POST | `/api/upload` | Upload a PDF document |
| GET | `/api/documents` | List uploaded documents |
| DELETE | `/api/documents/<filename>` | Delete a document |
| POST | `/api/query` | Ask a question (SSE stream) |

## Notes

- Documents are stored in `/uploads/` and re-indexed on restart if re-uploaded.
- The vector index is **in-memory** — it resets on server restart.
- Maximum file size: 20 MB.
- Supports querying across multiple PDFs simultaneously.
