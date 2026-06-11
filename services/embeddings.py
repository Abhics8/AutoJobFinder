"""Embedding service: lazy model load, resume pre-computation, caching."""
import pickle
from pathlib import Path

import numpy as np

import config

_model = None


def get_model():
    global _model
    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(config.EMBEDDING_MODEL)
    return _model


def embed_text(text: str) -> np.ndarray:
    """Embed a document: chunk by paragraphs, mean-pool, L2-normalize."""
    chunks = [c.strip() for c in text.split("\n") if len(c.strip()) > 30]
    if not chunks:
        chunks = [text[:2000]]
    vecs = get_model().encode(chunks, normalize_embeddings=True)
    mean = vecs.mean(axis=0)
    return mean / np.linalg.norm(mean)


def extract_pdf_text(pdf_path: Path) -> str:
    from pypdf import PdfReader
    return "\n".join(page.extract_text() or "" for page in PdfReader(pdf_path).pages)


def precompute_resumes(force: bool = False) -> dict[str, np.ndarray]:
    """Embed each resume PDF in data/, cache to embeddings/*.pkl."""
    vectors = {}
    for variant, filename in config.resume_variants().items():
        pdf = config.DATA_DIR / filename
        cache = config.EMBEDDINGS_DIR / f"resume_{variant}.pkl"
        if not pdf.exists():
            print(f"  [skip] {filename} not found in data/")
            continue
        if cache.exists() and not force and cache.stat().st_mtime > pdf.stat().st_mtime:
            vectors[variant] = pickle.loads(cache.read_bytes())
            continue
        text = extract_pdf_text(pdf)
        vec = embed_text(text)
        cache.write_bytes(pickle.dumps(vec))
        # Cache raw text too, for skill matching
        (config.EMBEDDINGS_DIR / f"resume_{variant}.txt").write_text(text)
        vectors[variant] = vec
        print(f"  [ok] embedded {variant}")
    return vectors


def load_resume_vectors() -> dict[str, np.ndarray]:
    vectors = {}
    for variant in config.resume_variants():
        cache = config.EMBEDDINGS_DIR / f"resume_{variant}.pkl"
        if cache.exists():
            vectors[variant] = pickle.loads(cache.read_bytes())
    return vectors


def load_resume_text(variant: str) -> str:
    txt = config.EMBEDDINGS_DIR / f"resume_{variant}.txt"
    return txt.read_text() if txt.exists() else ""
