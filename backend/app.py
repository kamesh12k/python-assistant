import os
import json
from flask import Flask, request, jsonify, stream_with_context, Response
from flask_cors import CORS
from werkzeug.utils import secure_filename
from google import genai
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

from pdf_processor import extract_text_from_pdf, chunk_text, get_pdf_metadata
from rag import RAGEngine

app = Flask(__name__)
CORS(app)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', 'uploads')
ALLOWED_EXTENSIONS = {'pdf'}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Global state
rag_engine = RAGEngine()
document_store: dict = {}  # filename -> metadata

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash")
client = None


def get_gemini_client():
    """Lazily load or return Google GenAI client."""
    global client
    if client is not None:
        return client
    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if api_key:
        client = genai.Client(api_key=api_key)
    return client


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'documents': len(document_store)})


@app.route('/api/upload', methods=['POST'])
def upload_pdf():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Only PDF files are allowed'}), 400

    filename = secure_filename(file.filename)
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    file.save(filepath)

    try:
        # Extract text and metadata
        text = extract_text_from_pdf(filepath)
        metadata = get_pdf_metadata(filepath)
        chunks = chunk_text(text, chunk_size=400, overlap=40)

        # Add to RAG engine
        num_chunks = rag_engine.add_document(chunks, filename)

        # Store metadata
        document_store[filename] = {
            **metadata,
            'filename': filename,
            'chunk_count': num_chunks,
            'filepath': filepath
        }

        return jsonify({
            'message': f'Successfully processed {filename}',
            'document': document_store[filename]
        })

    except Exception as e:
        os.remove(filepath)
        return jsonify({'error': f'Failed to process PDF: {str(e)}'}), 500


@app.route('/api/documents', methods=['GET'])
def list_documents():
    return jsonify({'documents': list(document_store.values())})


@app.route('/api/documents/<filename>', methods=['DELETE'])
def delete_document(filename):
    if filename not in document_store:
        return jsonify({'error': 'Document not found'}), 404

    filepath = document_store[filename].get('filepath', '')
    rag_engine.remove_document(filename)
    del document_store[filename]

    if os.path.exists(filepath):
        os.remove(filepath)

    return jsonify({'message': f'Deleted {filename}'})


@app.route('/api/query', methods=['POST'])
def query():
    data = request.get_json()
    if not data or 'question' not in data:
        return jsonify({'error': 'No question provided'}), 400

    question = data['question'].strip()
    if not question:
        return jsonify({'error': 'Question cannot be empty'}), 400

    if not rag_engine.has_documents():
        return jsonify({'error': 'No documents uploaded yet. Please upload a PDF first.'}), 400

    # Retrieve relevant chunks
    relevant_chunks = rag_engine.retrieve(question, top_k=5)

    if not relevant_chunks:
        return jsonify({'error': 'Could not find relevant context in the documents.'}), 400

    # Build context
    context_parts = []
    sources = set()
    for chunk in relevant_chunks:
        context_parts.append(f"[From: {chunk['doc_name']}]\n{chunk['text']}")
        sources.add(chunk['doc_name'])

    context = "\n\n---\n\n".join(context_parts)

    system_prompt = """You are an expert research assistant. Your job is to answer questions 
based ONLY on the provided document context. Be precise, cite the source document when relevant, 
and acknowledge if the context does not contain enough information to fully answer the question.
Format your response in clear, well-structured markdown."""

    user_message = f"""Context from uploaded documents:

{context}

---

Question: {question}

Please answer based on the context above."""

    gemini_client = get_gemini_client()
    if not gemini_client:
        return jsonify({'error': 'GEMINI_API_KEY is not set. Please add it to your backend/.env file.'}), 500

    def generate():
        try:
            response_stream = gemini_client.models.generate_content_stream(
                model=GEMINI_MODEL,
                contents=user_message,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                ),
            )
            for chunk in response_stream:
                if chunk.text:
                    yield f"data: {json.dumps({'text': chunk.text})}\n\n"

            yield f"data: {json.dumps({'done': True, 'sources': list(sources)})}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'error': str(e)})}\n\n"

    return Response(
        stream_with_context(generate()),
        mimetype='text/event-stream',
        headers={
            'Cache-Control': 'no-cache',
            'X-Accel-Buffering': 'no'
        }
    )


if __name__ == '__main__':
    print("Starting AI Research Assistant backend...")
    print(f"Upload folder: {UPLOAD_FOLDER}")
    app.run(debug=True, port=5000)
