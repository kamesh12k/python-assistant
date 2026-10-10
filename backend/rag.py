import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any
import os

# Load embedding model once
_model = None

def get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer('all-MiniLM-L6-v2')
    return _model


class RAGEngine:
    """
    Retrieval-Augmented Generation engine.
    Stores document chunks as embeddings in a FAISS index
    and retrieves the most relevant chunks for a query.
    """

    def __init__(self):
        self.index = None
        self.chunks: List[Dict[str, Any]] = []  # {text, doc_name, chunk_id}
        self.dimension = 384  # all-MiniLM-L6-v2 output dimension

    def _init_index(self):
        self.index = faiss.IndexFlatL2(self.dimension)

    def add_document(self, chunks: List[Dict], doc_name: str):
        """Embed and add chunks from a document to the index."""
        model = get_model()

        texts = [c['text'] for c in chunks]
        embeddings = model.encode(texts, convert_to_numpy=True)
        embeddings = embeddings.astype(np.float32)

        if self.index is None:
            self._init_index()

        start_id = len(self.chunks)
        for i, (chunk, emb) in enumerate(zip(chunks, embeddings)):
            self.chunks.append({
                'text': chunk['text'],
                'doc_name': doc_name,
                'chunk_id': start_id + i
            })

        self.index.add(embeddings)
        return len(texts)

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict]:
        """Retrieve the most relevant chunks for a query."""
        if self.index is None or len(self.chunks) == 0:
            return []

        model = get_model()
        query_emb = model.encode([query], convert_to_numpy=True).astype(np.float32)

        k = min(top_k, len(self.chunks))
        distances, indices = self.index.search(query_emb, k)

        results = []
        for dist, idx in zip(distances[0], indices[0]):
            if idx >= 0:
                chunk = self.chunks[idx].copy()
                chunk['score'] = float(dist)
                results.append(chunk)

        return results

    def remove_document(self, doc_name: str):
        """Remove all chunks for a given document (rebuilds index)."""
        self.chunks = [c for c in self.chunks if c['doc_name'] != doc_name]
        self._rebuild_index()

    def _rebuild_index(self):
        """Rebuild the FAISS index from remaining chunks."""
        if not self.chunks:
            self.index = None
            return

        model = get_model()
        texts = [c['text'] for c in self.chunks]
        embeddings = model.encode(texts, convert_to_numpy=True).astype(np.float32)

        self._init_index()
        self.index.add(embeddings)

    def get_document_names(self) -> List[str]:
        return list(set(c['doc_name'] for c in self.chunks))

    def has_documents(self) -> bool:
        return len(self.chunks) > 0
