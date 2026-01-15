from __future__ import annotations
from typing import Dict, Any, List, Optional
import re
from app.llm_client import is_configured as llm_ready, chat_json_schema

HEADING_PATTERNS = [
    r"^(?:[0-9]{1,2}|[ivxlcdm]{1,4}|[a-z])\s*[\.)\-]\s+.+$",  # 1. Title / I. Title / a) Title
    r"^(introduction|méthodes?|methods?|résultats?|results?|discussion|conclusion|références?)$",
    r"^(parties|objet\s+du\s+contrat|durée|prix|paiement|obligations?|résiliation|pénalités?)$",
]

HEADING_RE = [re.compile(pat, re.IGNORECASE) for pat in HEADING_PATTERNS]


def _is_heading(line: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if len(s) <= 80 and (s.isupper() or s.istitle()):
        return True
    return any(r.match(s) for r in HEADING_RE)


def segment_document(doc: Dict[str, Any], use_llm: bool = False, model: Optional[str] = None) -> Dict[str, Any]:
    """
    Découpe le document en sections rudimentaires à partir des titres probables.
    Retourne { sections: [ {title, content, pages} ] }
    """
    # LLM-based segmentation if enabled
    if use_llm and llm_ready():
        # Build a concise sample (up to ~10k chars)
        buf = []
        total = 0
        for p in doc.get("pages", []):
            t = p.get("text", "")
            if not t:
                continue
            if total + len(t) > 10000:
                t = t[: max(0, 10000 - total)]
            buf.append(f"[Page {p.get('page_number')}]\n{t}")
            total += len(t)
            if total >= 10000:
                break
        sample = "\n\n".join(buf)
        sys = "Tu segmentes des documents PDF en sections logiques au format JSON."
        prompt = (
            "Retourne JSON strict: {\n  \"sections\": [ {\n    \"title\": "
            "string, \n    \"content\": string, \n    \"pages\": [integer]\n  } ]\n}\n"
            "Respecte des titres plausibles selon le type (article: Introduction, Méthodes...; contrat: Parties, Durée...).\n\n"
            f"Texte:\n{sample}"
        )
        schema = {
            "type": "object",
            "properties": {
                "sections": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "content": {"type": "string"},
                            "pages": {"type": "array", "items": {"type": "integer"}},
                        },
                        "required": ["title", "content", "pages"],
                    },
                    "minItems": 1,
                }
            },
            "required": ["sections"],
        }
        data = chat_json_schema(prompt, schema=schema, system=sys, model=model) or {}
        if isinstance(data, dict) and isinstance(data.get("sections"), list) and data.get("sections"):
            # sanitize minimal shape
            cleaned = []
            for s in data.get("sections", [])[:25]:
                title = str(s.get("title", "Section")).strip()[:120]
                content = str(s.get("content", "")).strip()
                pages = s.get("pages") or []
                pages = [int(p) for p in pages if isinstance(p, int)][:10]
                if not pages:
                    pages = [1]
                cleaned.append({"title": title, "content": content, "pages": pages})
            return {"sections": cleaned}

    sections: List[Dict[str, Any]] = []
    current: Dict[str, Any] | None = None

    for page in doc.get("pages", []):
        page_no = page.get("page_number")
        text = page.get("text", "")
        lines = text.splitlines()
        for line in lines:
            if _is_heading(line):
                # start a new section
                if current:
                    sections.append(current)
                current = {"title": line.strip(), "content": "", "pages": [page_no]}
            else:
                if not current:
                    current = {"title": "Document", "content": "", "pages": [page_no]}
                current["content"] += (line + "\n")
                if page_no not in current["pages"]:
                    current["pages"].append(page_no)

    if current:
        sections.append(current)

    if not sections:
        sections = [{"title": "Document", "content": "\n".join(p.get("text", "") for p in doc.get("pages", [])), "pages": [p.get("page_number") for p in doc.get("pages", [])]}]

    return {"sections": sections}
