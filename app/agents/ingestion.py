from __future__ import annotations
from typing import Dict, List, Any
from pypdf import PdfReader
import os


def ingest_pdf(file_path: str) -> Dict[str, Any]:
    """
    Lit un PDF et extrait le texte page par page.
    Retourne un dict: { filename, num_pages, pages: [ {page_number, text} ] }
    """
    reader = PdfReader(file_path)
    pages: List[Dict[str, Any]] = []
    for i, page in enumerate(reader.pages, start=1):
        try:
            text = page.extract_text() or ""
        except Exception:
            text = ""
        pages.append({"page_number": i, "text": text})

    return {
        "filename": os.path.basename(file_path),
        "path": file_path,
        "num_pages": len(pages),
        "pages": pages,
    }


def ingest_pdfs(file_paths: List[str]) -> List[Dict[str, Any]]:
    return [ingest_pdf(p) for p in file_paths]
