from __future__ import annotations
from typing import Dict, Any, Tuple, Optional
import re
from app.llm_client import is_configured as llm_ready, chat_json

ARTICLE_HINTS = [
    r"\babstract\b",
    r"\bintroduction\b",
    r"\bmethods?\b|\bméthodes\b",
    r"\bresults?\b|\brésultats\b",
    r"\bdiscussion\b",
    r"\bconclusion(s)?\b",
    r"\breferences?\b|\bréférences\b",
]

CONTRACT_HINTS = [
    r"\b(le\s+présent\s+contrat)\b",
    r"\bcontrat\b|\bconditions\s+générales\b",
    r"\bles\s+parties\b|\bentre\b",
    r"\bdurée\b|\bdate\b|\bentrée\s+en\s+vigueur\b",
    r"\bobligations?\b|\bs'engage(nt)?\b|\bdoit\b",
    r"\brésiliation\b|\brésilier\b",
    r"\b(pénalité|pénalités|amende|dommages)\b",
    r"\bprix\b|\bpaiement\b|\bfacturation\b|\bmontant(s)?\b|€|eur|euro(s)?",
]

CV_HINTS = [
    r"\bcurriculum\s+vitae\b|\bcv\b",
    r"\bexpérience\b|\bexperience\b",
    r"\bformation\b|\beducation\b",
    r"\bcompétences\b|\bskills\b",
    r"\bemail\b|\be-mail\b|\b@\w+",
    r"\btél(\.|ephone|éphone)?\b|\bphone\b|\+?\d{1,3}[\s.-]?\d{2,}",
    r"\blangues?\b|\blanguages?\b",
]

COURS_HINTS = [
    r"\bcours\b|\bcourse\b|\bsyllabus\b",
    r"\bchapitre\b|\bchapter\b",
    r"\bexercices?\b|\bexercises?\b|\btd\b|\btp\b",
    r"\bprofesseur\b|\benseignant\b|\blecture\b",
    r"\buniversité\b|\buniversity\b|\bfaculté\b",
    r"\bobjectifs?\s+pédagogiques\b|\blearning\s+outcomes\b",
]


def _sample_text(doc: Dict[str, Any], max_chars: int = 3000) -> str:
    buf = []
    total = 0
    for page in doc.get("pages", [])[:3]:
        t = page.get("text", "")
        if not t:
            continue
        if total + len(t) > max_chars:
            t = t[: max(0, max_chars - total)]
        buf.append(t)
        total += len(t)
        if total >= max_chars:
            break
    return "\n".join(buf).lower()


def detect_document_type(doc: Dict[str, Any], use_llm: bool = False, model: Optional[str] = None) -> Tuple[str, float]:
    """
    Retourne (document_type, confidence) parmi {"article_scientifique", "contrat", "cv", "cours", "autre"}
    Heuristiques simples basées sur des mots-clés, avec option LLM.
    """
    text = _sample_text(doc)

    # Optional LLM pass
    if use_llm and llm_ready() and text.strip():
        prompt = (
            "Classifie ce document en JSON: {\"type\": \"article_scientifique|contrat|cv|cours|autre\", \"confidence\": 0.8}\n\n"
            f"Texte:\n{text[:2000]}"
        )
        data = chat_json(prompt, system="Classifieur PDF", model=model) or {}
        t = (data.get("type") or "").strip()
        c = float(data.get("confidence") or 0)
        if t in {"article_scientifique", "contrat", "cv", "cours", "autre"} and 0 <= c <= 1:
            return (t, max(0.5, c))

    article_hits = sum(1 for pat in ARTICLE_HINTS if re.search(pat, text))
    contract_hits = sum(1 for pat in CONTRACT_HINTS if re.search(pat, text))
    cv_hits = sum(1 for pat in CV_HINTS if re.search(pat, text))
    cours_hits = sum(1 for pat in COURS_HINTS if re.search(pat, text))

    scores = {
        "article_scientifique": article_hits,
        "contrat": contract_hits,
        "cv": cv_hits,
        "cours": cours_hits,
    }

    best_type, best_hits = max(scores.items(), key=lambda x: x[1])

    if best_hits == 0:
        return ("autre", 0.4)

    conf = min(0.55 + 0.05 * best_hits, 0.95)
    return (best_type, conf)
