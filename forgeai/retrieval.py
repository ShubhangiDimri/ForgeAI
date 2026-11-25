import os
import faiss
import numpy as np
from .schema import Passage, Settings


class Index:
    def __init__(self, passages: list[Passage], settings: Settings, embedding: str, encoder=None):
        if encoder is None:
            os.environ.setdefault("USE_TF", "0")
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer(embedding, local_files_only=True, device="cpu", trust_remote_code=False)
        self.encoder, self.settings, self.passages = encoder, settings, passages
        vectors = self.encode([p.text for p in passages])
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.ascontiguousarray(self.encoder.encode(texts), dtype="float32")
        faiss.normalize_L2(vectors)
        return vectors

    def search(self, query: str) -> list[Passage]:
        scores, ids = self.index.search(self.encode([query]), self.settings.top_k)
        return [self.passages[i] for i, score in zip(ids[0], scores[0])
                if i >= 0 and score >= self.settings.min_score]

