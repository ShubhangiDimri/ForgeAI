import os
import re
from calendar import month_name
from datetime import date
import faiss
import numpy as np
from .schema import Passage, Settings


def _contains(query: str, value: str) -> bool:
    return bool(value and re.search(r"(?<!\w)" + re.escape(value) + r"(?!\w)", query, re.I))


def _dates(query: str) -> set[str]:
    candidates = set(re.findall(r"\b\d{4}-\d{2}-\d{2}\b", query))
    months = {alias: i for i, name in enumerate(month_name) if name
              for alias in (name.casefold(), name[:3].casefold())}
    forms = ((r"\b(\d{1,2})\s+([a-z]+)\s+(\d{4})\b", False),
             (r"\b([a-z]+)\s+(\d{1,2}),?\s+(\d{4})\b", True))
    for pattern, month_first in forms:
        for a, b, year in re.findall(pattern, query, re.I):
            month, day = (a, b) if month_first else (b, a)
            if month.casefold() in months:
                try:
                    candidates.add(date(int(year), months[month.casefold()], int(day)).isoformat())
                except ValueError:
                    continue
    return candidates


def exact_row(question: str, passages: list[Passage]) -> list[Passage]:
    """Use an explicit identifier and qualifiers only when they resolve one CSV row."""
    tables: dict[str, dict[int, list[Passage]]] = {}
    for passage in passages:
        if passage.cells is not None and passage.row is not None:
            tables.setdefault(passage.file, {}).setdefault(passage.row, []).append(passage)
    qualifiers = {"region", "channel", "country", "market", "location", "store", "currency"}
    dates = _dates(question)
    matches = []
    for rows in tables.values():
        cells = {n: group[0].cells or {} for n, group in rows.items()}
        constraints: dict[str, set[str]] = {}
        for fields in cells.values():
            for column, value in fields.items():
                key = column.casefold()
                if ((key == "date" or key.endswith("_date")) and dates):
                    constraints.setdefault(column, set()).update(dates)
                elif key in qualifiers and _contains(question, value):
                    constraints.setdefault(column, set()).add(value.casefold())
        for n, fields in cells.items():
            identifiers = [value for column, value in fields.items()
                           if (column.casefold() in {"id", "sku", "code"}
                               or column.casefold().endswith(("_id", "_sku", "_code")))
                           and len(value) >= 3 and any(c.isdigit() for c in value)
                           and any(c.isalpha() for c in value)]
            if any(_contains(question, value) for value in identifiers) and all(
                fields.get(column, "").casefold() in values for column, values in constraints.items()
            ):
                matches.append(rows[n])
    return matches[0] if len(matches) == 1 else []


def prose_queries(question: str, row: Passage) -> list[str]:
    """Split explicit follow-up clauses and exclude the exact row's clause."""
    identifiers = [value for column, value in (row.cells or {}).items()
                   if column.casefold() in {"id", "sku", "code"}
                   or column.casefold().endswith(("_id", "_sku", "_code"))]
    separators = r"[?;\n]+\s*(?:(?:and|also|aur)\s+)?|\b(?:and|also|aur)\s+(?=(?:what|when|how|where|which|is|are|can|tell)\b)"
    parts = [part.strip() for part in re.split(separators, question, flags=re.I) if part.strip()]
    if len(parts) < 2:
        return []
    return [part for part in parts if not any(_contains(part, value) for value in identifiers)]


class Index:
    def __init__(self, passages: list[Passage], settings: Settings, embedding: str, encoder=None):
        if encoder is None:
            os.environ.setdefault("USE_TF", "0")
            from sentence_transformers import SentenceTransformer
            encoder = SentenceTransformer(embedding, local_files_only=True, device="cpu", trust_remote_code=False)
        self.encoder = encoder
        self.rebuild(passages, settings)

    def rebuild(self, passages: list[Passage], settings: Settings) -> None:
        self.settings, self.passages = settings, passages
        vectors = self.encode([p.text for p in passages])
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(vectors)
        self._prose = [i for i, passage in enumerate(passages) if passage.cells is None]
        self._prose_index = None
        if self._prose and len(self._prose) != len(passages):
            self._prose_index = faiss.IndexFlatIP(vectors.shape[1])
            self._prose_index.add(vectors[self._prose])

    def encode(self, texts: list[str]) -> np.ndarray:
        vectors = np.ascontiguousarray(self.encoder.encode(texts), dtype="float32")
        faiss.normalize_L2(vectors)
        return vectors

    def search(self, query: str, *, prose_only: bool = False) -> list[Passage]:
        if prose_only and not self._prose:
            return []
        index = self._prose_index if prose_only and self._prose_index is not None else self.index
        rows = self._prose if index is self._prose_index else range(len(self.passages))
        scores, ids = index.search(self.encode([query]), self.settings.top_k)
        return [self.passages[rows[i]] for i, score in zip(ids[0], scores[0])
                if i >= 0 and score >= self.settings.min_score]
