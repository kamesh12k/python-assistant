import fitz  # PyMuPDF
import os
import re


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    doc = fitz.open(pdf_path)
    text = ""
    for page_num in range(len(doc)):
        page = doc[page_num]
        text += f"\n--- Page {page_num + 1} ---\n"
        text += page.get_text()
    doc.close()
    return text


def chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list:
    """
    Split text into overlapping chunks for embedding.
    Returns a list of dicts with 'text' and 'metadata'.
    """
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)

    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []
    current_length = 0

    for sentence in sentences:
        sentence_len = len(sentence.split())
        if current_length + sentence_len > chunk_size and current_chunk:
            chunk_text_str = ' '.join(current_chunk)
            chunks.append({'text': chunk_text_str, 'length': current_length})

            overlap_sentences = []
            overlap_len = 0
            for s in reversed(current_chunk):
                s_len = len(s.split())
                if overlap_len + s_len <= overlap:
                    overlap_sentences.insert(0, s)
                    overlap_len += s_len
                else:
                    break

            current_chunk = overlap_sentences
            current_length = overlap_len

        current_chunk.append(sentence)
        current_length += sentence_len

    if current_chunk:
        chunks.append({'text': ' '.join(current_chunk), 'length': current_length})

    return chunks


def get_pdf_metadata(pdf_path: str) -> dict:
    """Extract basic metadata from a PDF."""
    doc = fitz.open(pdf_path)
    meta = doc.metadata
    page_count = len(doc)
    doc.close()

    return {
        'title': meta.get('title', os.path.basename(pdf_path)),
        'author': meta.get('author', 'Unknown'),
        'page_count': page_count,
        'filename': os.path.basename(pdf_path)
    }
