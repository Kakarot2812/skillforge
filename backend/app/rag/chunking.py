"""
Deterministic, dependency-free text chunking for RAG ingestion.

Design goals (character-based, not token-based, consistent with the
character budgets already used throughout ``app/qwen_ai``):

- configurable size/overlap
- prefers splitting on heading/paragraph/sentence boundaries over mid-word cuts
- stable ordering (``chunk_index`` is always assignment order)
- stable identity: the same input text with the same settings always
  produces the same chunk boundaries and hashes, which is what makes
  ingestion idempotent (see ``app/rag/ingestion.py``)

No NLP pipeline, no external tokenizer dependency — a small, predictable
splitter is enough for this project's evidence sizes.
"""
import hashlib
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional

_HEADING_RE = re.compile(r"^(#{1,6}\s+.+|[A-Z][A-Za-z0-9 /&-]{2,60}:)\s*$", re.MULTILINE)
_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n+")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")
_WHITESPACE_RE = re.compile(r"[ \t]+")


def normalize_text(text: str) -> str:
    """Collapse runs of whitespace and normalise line endings without altering meaning."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = _WHITESPACE_RE.sub(" ", text)
    lines = [line.strip() for line in text.split("\n")]
    # Collapse 3+ blank lines to a single paragraph break, keep single blank lines.
    normalized_lines: List[str] = []
    blank_run = 0
    for line in lines:
        if line == "":
            blank_run += 1
            if blank_run <= 1:
                normalized_lines.append(line)
        else:
            blank_run = 0
            normalized_lines.append(line)
    return "\n".join(normalized_lines).strip()


def content_hash(text: str) -> str:
    """Stable sha256 hex digest of normalised content, used for idempotent ingestion."""
    return hashlib.sha256(normalize_text(text).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Chunk:
    index: int
    content: str
    content_hash: str
    heading: Optional[str] = None
    metadata: Dict[str, object] = field(default_factory=dict)


def _iter_paragraph_units(text: str) -> List[tuple]:
    """Split on blank-line paragraph boundaries, pairing each paragraph with the
    most recent heading line (its own first line, or a preceding standalone
    heading paragraph). A paragraph that is *only* a heading carries its
    heading forward but emits no content unit of its own.
    """
    paragraphs = [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(text) if p.strip()]
    units: List[tuple] = []
    current_heading: Optional[str] = None
    for para in paragraphs:
        lines = para.split("\n")
        first_line = lines[0].strip()
        if _HEADING_RE.match(first_line):
            current_heading = first_line.lstrip("#").strip().rstrip(":").strip()
            rest = "\n".join(lines[1:]).strip()
            if rest:
                units.append((current_heading, rest))
        else:
            units.append((current_heading, para))
    return units


def _split_long_paragraph(paragraph: str, max_size: int) -> List[str]:
    """Split an overlong paragraph on sentence boundaries, falling back to hard cuts."""
    if len(paragraph) <= max_size:
        return [paragraph]

    sentences = _SENTENCE_SPLIT_RE.split(paragraph)
    pieces: List[str] = []
    current = ""
    for sentence in sentences:
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= max_size:
            current = candidate
            continue
        if current:
            pieces.append(current)
        if len(sentence) <= max_size:
            current = sentence
        else:
            # A single sentence longer than max_size: hard-wrap as a last resort.
            for i in range(0, len(sentence), max_size):
                pieces.append(sentence[i : i + max_size])
            current = ""
    if current:
        pieces.append(current)
    return pieces


def chunk_text(
    text: str,
    *,
    chunk_size: int,
    chunk_overlap: int,
) -> List[Chunk]:
    """Split normalised text into overlapping chunks, preferring natural boundaries.

    Chunks are built by greedily packing sections (paragraphs/headings) up to
    ``chunk_size`` characters; a section that alone exceeds ``chunk_size`` is
    further split on sentence boundaries. ``chunk_overlap`` characters of the
    previous chunk's tail are carried into the next chunk's start so retrieved
    chunks keep some surrounding context.

    Returns an empty list for blank input — callers should treat that as
    "nothing to ingest" rather than an error.
    """
    if chunk_overlap >= chunk_size:
        raise ValueError("chunk_overlap must be smaller than chunk_size")

    normalized = normalize_text(text)
    if not normalized:
        return []

    units = _iter_paragraph_units(normalized)
    pieces: List[str] = []
    piece_headings: List[Optional[str]] = []
    for heading, unit_text in units:
        for piece in _split_long_paragraph(unit_text, chunk_size):
            pieces.append(piece)
            piece_headings.append(heading)

    chunks: List[Chunk] = []
    buffer = ""
    buffer_heading: Optional[str] = None
    for piece, heading in zip(pieces, piece_headings):
        candidate = f"{buffer}\n\n{piece}".strip() if buffer else piece
        if len(candidate) <= chunk_size or not buffer:
            buffer = candidate
            buffer_heading = buffer_heading or heading
            continue

        chunks.append(_make_chunk(len(chunks), buffer, buffer_heading))
        overlap_tail = buffer[-chunk_overlap:].strip() if chunk_overlap else ""
        buffer = f"{overlap_tail}\n\n{piece}".strip() if overlap_tail else piece
        buffer_heading = heading

    if buffer:
        chunks.append(_make_chunk(len(chunks), buffer, buffer_heading))

    return chunks


def _make_chunk(index: int, content: str, heading: Optional[str]) -> Chunk:
    content = content.strip()
    return Chunk(
        index=index,
        content=content,
        content_hash=content_hash(content),
        heading=heading,
        metadata={"heading": heading} if heading else {},
    )
