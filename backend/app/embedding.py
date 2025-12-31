from typing import Optional, List
from sentence_transformers import SentenceTransformer

_model: Optional[SentenceTransformer] = None

def get_embedding_model(model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    global _model
    if _model is None:
        _model = SentenceTransformer(model_name)
    return _model

def embed_text(text: Optional[str], model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
    if text is None:
        return None
    t = text.strip()
    if not t:
        return None
    model = get_embedding_model(model_name)
    vec = model.encode([t], normalize_embeddings = True)[0]
    return vec.tolist()
