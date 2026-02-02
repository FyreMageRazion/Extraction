"""
PDF loader: reads all PDFs from a directory (default ./inputs/), extracts
text, and returns a single string for pa_case_normalizer. Downstream skills
use only normalized JSON, not raw PDF text.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

try:
    from pypdf import PdfReader
except ImportError:
    PdfReader = None  # type: ignore[misc, assignment]


def _extract_text_from_pdf(path: Path) -> str:
    """Extract text from one PDF file."""
    if PdfReader is None:
        raise RuntimeError("pypdf is required. Install with: pip install pypdf")
    reader = PdfReader(str(path))
    parts = []
    for page in reader.pages:
        try:
            t = page.extract_text()
            if t:
                parts.append(t)
        except Exception:
            pass
    return "\n".join(parts) if parts else ""


def load_pdfs_from_directory(
    directory: str | Path,
    *,
    fallback_directory: str | Path | None = None,
) -> str:
    """
    Load all PDFs from directory, concatenate text with document headers.
    If directory is missing or empty and fallback_directory is set, use that.
    Returns a single string suitable for pa_case_normalizer input (documents).
    """
    path = Path(directory)
    if fallback_directory is not None and (not path.exists() or not path.is_dir()):
        path = Path(fallback_directory)
    if not path.exists() or not path.is_dir():
        return ""

    collected: List[Tuple[str, str]] = []
    for f in sorted(path.iterdir()):
        if f.suffix.lower() != ".pdf":
            continue
        try:
            text = _extract_text_from_pdf(f)
            if text.strip():
                collected.append((f.name, text))
        except Exception:
            continue

    if not collected:
        return ""

    out_parts = []
    for name, body in collected:
        out_parts.append(f"\n\n--- Document: {name} ---\n\n{body}")
    return "".join(out_parts).strip()
