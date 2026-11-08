
import json
import re
import sys
from pathlib import Path

import numpy as np
from pypdf import PdfReader

ROOT = Path(__file__).parent.parent
PDF_DIR = ROOT / "data" / "guidelines"
INDEX_DIR = ROOT / "data" / "index"
MODEL_NAME = "intfloat/multilingual-e5-small"

# app crop -> keyword in the file name
CROP_KEY = {"Tomato": "tomato", "Potato": "potato", "Pepper": "capsicum"}

_model = None
_index = None

COMMON = {
    "the", "and", "of", "to", "in", "is", "for", "with", "on",
    "are", "as", "by", "or", "at", "from", "be", "that", "this",
    "can", "may", "per", "should", "which"
}

MIN_ENGLISH = 0.08  # share of words that are common English words

SKIP_FILES = {
    "potato-tomato_icar-crri_odisha-advisory-2026-01.pdf"
}


def _get_model():
    global _model

    if _model is None:
        from sentence_transformers import SentenceTransformer
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def _pdf_chunks(path: Path):
    reader = PdfReader(str(path))

    for page_no, page in enumerate(reader.pages, start=1):
        text = re.sub(r"\s+", " ", page.extract_text() or "").strip()

        if len(text) < 80:
            continue

        size, step = 1000, 700  # overlapping windows

        for start in range(0, len(text), step):
            piece = text[start:start + size]

            if len(piece) >= 80:
                yield page_no, piece

            if start + size >= len(text):
                break


def english_ratio(texts):
    words = re.findall(r"[a-z]+", " ".join(texts).lower())

    return (
        sum(w in COMMON for w in words) / len(words)
        if words else 0.0
    )


def build():
    model = _get_model()
    chunks = []

    for pdf in sorted(PDF_DIR.glob("*.pdf")):
        pieces = list(_pdf_chunks(pdf))

        ratio = english_ratio([t for _, t in pieces])

        if ratio < MIN_ENGLISH:
            print(
                f"SKIPPED (not readable English, ratio {ratio:.2f}): "
                f"{pdf.name}"
            )
            continue

        for page_no, text in pieces:
            chunks.append({
                "source": pdf.name,
                "page": page_no,
                "text": text
            })

        print(
            f"{pdf.name}: {len(pieces)} chunks "
            f"(english ratio {ratio:.2f})"
        )

    if not chunks:
        print("No chunks found. Check data/guidelines/")
        return

    emb = model.encode(
        ["passage: " + c["text"] for c in chunks],
        normalize_embeddings=True,
        show_progress_bar=True,
    )

    INDEX_DIR.mkdir(parents=True, exist_ok=True)

    np.save(
        INDEX_DIR / "embeddings.npy",
        emb.astype(np.float32)
    )

    (INDEX_DIR / "chunks.json").write_text(
        json.dumps(chunks),
        encoding="utf-8"
    )

    print(f"Built index with {len(chunks)} chunks")


def _load():
    global _index

    if _index is None:
        emb = np.load(INDEX_DIR / "embeddings.npy")

        chunks = json.loads(
            (INDEX_DIR / "chunks.json").read_text(encoding="utf-8")
        )

        _index = (emb, chunks)

    return _index


def search(query: str, crop: str, k: int = 4):
    """Top-k passages: crop-specific files get a small bonus, max 2 passages per file."""

    emb, chunks = _load()

    key = CROP_KEY.get(crop, crop.lower())

    q = _get_model().encode(
        ["query: " + query],
        normalize_embeddings=True
    )[0]

    scores = emb @ q

    adj = np.full(len(chunks), -1.0)

    for i, c in enumerate(chunks):
        name = c["source"]

        specific = key in name.split("_")[0].split("-")
        generic = name.startswith("vegetables")

        if name in SKIP_FILES or not (specific or generic):
            continue

        adj[i] = scores[i] + (0.03 if specific else 0.0)

    out, per_source = [], {}

    for i in np.argsort(-adj):
        if adj[i] <= 0:
            break

        src = chunks[i]["source"]

        if per_source.get(src, 0) >= 2:
            continue

        per_source[src] = per_source.get(src, 0) + 1

        out.append({
            **chunks[i],
            "score": float(scores[i])
        })

        if len(out) == k:
            break

    return out


# label fragment -> terms that must appear in a passage for it to count as relevant
DISEASE_TERMS = {
    "Early_blight": ["early blight", "alternaria"],
    "Late_blight": ["late blight", "phytophthora"],
    "Bacterial_spot": [
        "bacterial spot",
        "bacterial leaf spot",
        "xanthomonas"
    ],
    "Leaf_Mold": [
        "leaf mold",
        "leaf mould",
        "cladosporium",
        "passalora"
    ],
    "Septoria_leaf_spot": ["septoria"],
    "Spider_mites": ["spider mite", "tetranychus"],
    "Target_Spot": ["target spot", "corynespora"],
    "YellowLeaf__Curl_Virus": ["leaf curl", "whitefly"],
    "mosaic_virus": ["mosaic"],
}


def passages_for(label: str, crop: str, k: int = 3):
    """Relevant guideline passages for a predicted disease. [] if none or healthy."""

    if crop == "Pepper":
        # No readable English pepper disease source yet
        return []

    terms = next(
        (v for key, v in DISEASE_TERMS.items() if key in label),
        None
    )

    if not terms:
        return []

    hits = search(
        f"{crop} {terms[0]} symptoms and management",
        crop,
        k=12
    )

    hits = [
        h for h in hits
        if any(t in h["text"].lower() for t in terms)
    ]

    # Keep only one passage per PDF page
    seen, unique = set(), []

    for h in hits:
        key = (h["source"], h["page"])

        if key not in seen:
            seen.add(key)
            unique.append(h)

    return unique[:k]


if __name__ == "__main__":

    if "--build" in sys.argv:
        build()

    elif "--test" in sys.argv:
        q = sys.argv[sys.argv.index("--test") + 1]

        crop = (
            sys.argv[sys.argv.index("--test") + 2]
            if len(sys.argv) > sys.argv.index("--test") + 2
            else "Tomato"
        )

        for r in search(q, crop):
            print(
                f"\n[{r['source']} p.{r['page']}] "
                f"score {r['score']:.2f}\n"
                f"{r['text'][:500]}"
            )
