from typing import List, Tuple
import numpy as np
from .llm import get_embedding

class InMemoryVectorStore:
    def __init__(self, texts: List[str]):
        self.texts = texts[:]
        self.embs = None
        if texts:
            embs = [get_embedding(t) for t in texts]
            self.embs = np.vstack(embs).astype(float)
        else:
            self.embs = np.zeros((0, 1), dtype=float)

    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        if self.embs.shape[0] == 0:
            return []
        q = get_embedding(query).astype(float)
        sims = self.embs @ q
        idx = np.argsort(-sims)[:k]
        return [(self.texts[i], float(sims[i])) for i in idx]
