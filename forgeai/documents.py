import hashlib
from pathlib import Path
import pandas as pd
import pymupdf
from .schema import Passage, Settings


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def load(folder: Path) -> tuple[list[Passage], dict[str, str]]:
    if not folder.is_dir():
        raise ValueError(f"Missing document folder: {folder}")
    passages, manifest = [], {}
    for path in sorted(folder.rglob("*")):
        if not path.is_file():
            continue
        if not path.resolve().is_relative_to(folder.resolve()):
            raise ValueError("Document outside input folder")
        name = path.relative_to(folder).as_posix()
        manifest[name] = digest(path.read_bytes())
        suffix = path.suffix.lower()
        def add(text: str, locator: str, **metadata):
            if not text.strip():
                raise ValueError(f"No extractable text: {name} {locator}")
            passages.append(Passage(id=f"{name}#{locator}", file=name, text=text, **metadata))
        if suffix == ".pdf":
            with pymupdf.open(path) as pdf:
                if not len(pdf):
                    raise ValueError(f"Empty PDF: {name}")
                for i, page in enumerate(pdf, 1):
                    add(page.get_text(), f"p{i}", page=i)
        elif suffix == ".csv":
            table = pd.read_csv(path, dtype=str, keep_default_na=False)
            if table.empty:
                raise ValueError(f"Empty CSV: {name}")
            for i, cells in enumerate(table.to_dict("records"), 1):
                add(" | ".join(f"{k}={v}" for k, v in cells.items()), f"r{i}", row=i, cells=cells)
        elif suffix == ".txt":
            add(path.read_text(encoding="utf-8-sig"), "text")
        else:
            raise ValueError(f"Unsupported file format: {name}")
    if not passages:
        raise ValueError("Empty document folder")
    return passages, manifest


def chunk(passages: list[Passage], settings: Settings) -> list[Passage]:
    result = []
    for item in passages:
        words = item.text.split()
        stride = settings.chunk_words - settings.overlap
        for i, start in enumerate(range(0, len(words), stride), 1):
            result.append(item.model_copy(update={
                "id": f"{item.id}:c{i}", "text": " ".join(words[start:start + settings.chunk_words])
            }))
            if start + settings.chunk_words >= len(words):
                break
    return result

