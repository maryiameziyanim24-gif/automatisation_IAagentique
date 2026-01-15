from __future__ import annotations
from typing import Dict, Any, List, Optional
import re
from collections import Counter
from app.llm_client import is_configured as llm_ready, chat_json_schema
from app.agents.extraction_article import extract_information_for_article

DATE_PAT = re.compile(r"\b(\d{1,2}[\-/]\d{1,2}[\-/]\d{2,4}|\d{4}-\d{2}-\d{2})\b")
MONTANT_PAT = re.compile(r"(?:€\s?|eur\s?|euro[s]?\s?)?\b\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})?\s*(?:€|eur|euro[s]?)\b", re.IGNORECASE)
DUREE_PAT = re.compile(r"\b(\d+\s*(?:jour[s]?|mois|année[s]?|an[s]?))\b", re.IGNORECASE)

SPLIT_SENT = re.compile(r"(?<=[.!?])\s+")

FR_STOPWORDS = set("""
a au aux avec ce ces dans de des du elle en et eux il je la le leur lui ma mais me même mes moi mon ne nos notre nous on ou par pas pour qu que qui sa se ses son sur ta te tes toi ton tu un une vos votre vous c d l j s t y n m qu\'
""".split())
EN_STOPWORDS = set("""
the and or of to in on for by with as is are was were be been being a an at from that this these those into over under out up down not no yes can could may might should would will shall it its it's they them their he him his she her we our us you your i me my mine ours yours theirs
""".split())


def _concat_sections_text(sections: Dict[str, Any]) -> str:
    return "\n\n".join([f"## {s['title']}\n{s['content']}" for s in sections.get("sections", [])])


def _extract_article(sections: Dict[str, Any], doc: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    data = {
        "probleme": None,
        "objectifs": None,
        "methodes": None,
        "resultats_principaux": None,
        "conclusion": None,
        "mots_cles": [],
    }
    # Map sections by likely titles
    def find_sec(keys: List[str]) -> str | None:
        for s in sections.get("sections", []):
            title = s.get("title", "").lower()
            if any(k in title for k in keys):
                return s.get("content", "").strip()
        return None

    # Try to find specific sections
    data["probleme"] = find_sec(["introduction", "background", "contexte"]) or find_sec(["abstract", "résumé"])
    data["objectifs"] = find_sec(["objectif", "objectifs", "goal", "aim"])
    data["methodes"] = find_sec(["méthode", "méthodes", "method", "methods"])
    data["resultats_principaux"] = find_sec(["résultats", "results"])
    data["conclusion"] = find_sec(["conclusion", "discussion"])
    
    # If nothing found, use first section content as fallback
    all_sections = sections.get("sections", [])
    if not data["probleme"] and all_sections:
        data["probleme"] = all_sections[0].get("content", "")[:500]
    
    # Absolute fallback: use document pages text directly
    if not data["probleme"] and doc:
        pages_text = " ".join([p.get("text", "") for p in doc.get("pages", [])[:2]])
        if pages_text.strip():
            data["probleme"] = pages_text[:600]
            data["objectifs"] = "Analyse du document (extraction heuristique)"
            data["methodes"] = "Extraction par reconnaissance de structure"

    # naive keywords by frequency
    all_text = _concat_sections_text(sections).lower()
    if not all_text and doc:
        all_text = " ".join([p.get("text", "") for p in doc.get("pages", [])[:3]]).lower()
    words = [w.strip(".,:;()[]{}\"'!?%") for w in all_text.split()]
    words = [w for w in words if w and (w not in FR_STOPWORDS) and (w not in EN_STOPWORDS) and len(w) > 2]
    common = [w for w, _ in Counter(words).most_common(15)]
    data["mots_cles"] = common[:7]
    return data


def _extract_contrat(sections: Dict[str, Any]) -> Dict[str, Any]:
    data = {
        "parties": [],
        "dates": {"signature": None, "debut": None, "fin": None},
        "duree": None,
        "montants": [],
        "obligations_principales": [],
        "clauses_resiliation": [],
        "penalites": [],
    }
    text = _concat_sections_text(sections)

    # Parties: heuristics - lines near keywords
    parties = []
    for line in text.splitlines():
        if re.search(r"\b(parties|entre|dénommé|dénomination|société|client|fournisseur)\b", line, re.IGNORECASE):
            parties.append(line.strip())
    data["parties"] = parties[:5]

    # Dates
    dates = DATE_PAT.findall(text)
    if dates:
        # naive mapping
        if len(dates) >= 1:
            data["dates"]["signature"] = dates[0]
        if len(dates) >= 2:
            data["dates"]["debut"] = dates[1]
        if len(dates) >= 3:
            data["dates"]["fin"] = dates[2]

    # Durée
    m = DUREE_PAT.search(text)
    if m:
        data["duree"] = m.group(1)

    # Montants
    data["montants"] = list({m.group(0) for m in MONTANT_PAT.finditer(text)})[:10]

    # Obligations / résiliation / pénalités (collect sentences)
    sentences = re.split(r"(?<=[.!?])\s+", text)
    for s in sentences:
        low = s.lower()
        if any(k in low for k in ["doit", "s'engage", "obligation", "tenu de"]):
            data["obligations_principales"].append(s.strip())
        if "résiliation" in low or "résilier" in low:
            data["clauses_resiliation"].append(s.strip())
        if any(k in low for k in ["pénalité", "pénalités", "amende", "dommage"]):
            data["penalites"].append(s.strip())

    return data


def _extract_autre(sections: Dict[str, Any]) -> Dict[str, Any]:
    # Basic summary of sections and top keywords
    titles = [s.get("title", "").strip() for s in sections.get("sections", [])]
    text = _concat_sections_text(sections).lower()
    words = [w.strip(".,:;()[]{}\"'!?%") for w in text.split()]
    words = [w for w in words if w and (w not in FR_STOPWORDS) and (w not in EN_STOPWORDS) and len(w) > 2]
    common = [w for w, _ in Counter(words).most_common(20)]
    return {
        "sections_principales": titles[:10],
        "points_cles": common[:10],
        "mots_cles": common[:7],
    }


def extract_information(doc: Dict[str, Any], sections: Dict[str, Any], use_llm: bool = False, model: Optional[str] = None) -> Dict[str, Any]:
    t = doc.get("document_type", "autre")

    # Optional LLM-based extraction
    if use_llm and llm_ready():
        joined = "\n\n".join([f"# {s['title']}\n{s['content']}" for s in sections.get("sections", [])])
        if t == "article_scientifique":
            return extract_information_for_article(sections, model=model)
        if t == "article_scientifique":
            prompt = (
                "Extrait en JSON strict: {\n  \"probleme\": string|null, \n  \"objectifs\": string|null, \n  \"methodes\": string|null, \n  \"resultats_principaux\": string|null, \n  \"conclusion\": string|null, \n  \"mots_cles\": [string]\n}\n\n"
                f"Sections:\n{joined}"
            )
            schema = {
                "type": "object",
                "properties": {
                    "probleme": {"type": ["string", "null"]},
                    "objectifs": {"type": ["string", "null"]},
                    "methodes": {"type": ["string", "null"]},
                    "resultats_principaux": {"type": ["string", "null"]},
                    "conclusion": {"type": ["string", "null"]},
                    "mots_cles": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["mots_cles"],
            }
            data = chat_json_schema(prompt, schema=schema, system="Extraction article scientifique", model=model)
            if isinstance(data, dict) and data:
                data.setdefault("mots_cles", [])
                return data
        elif t == "contrat":
            prompt = (
                "Extrait en JSON strict: {\n  \"parties\": [string], \n  \"dates\": {\n    \"signature\": string|null, \n    \"debut\": string|null, \n    \"fin\": string|null\n  }, \n  \"duree\": string|null, \n  \"montants\": [string], \n  \"obligations_principales\": [string], \n  \"clauses_resiliation\": [string], \n  \"penalites\": [string]\n}\n\n"
                f"Sections:\n{joined}"
            )
            schema = {
                "type": "object",
                "properties": {
                    "parties": {"type": "array", "items": {"type": "string"}},
                    "dates": {
                        "type": "object",
                        "properties": {
                            "signature": {"type": ["string", "null"]},
                            "debut": {"type": ["string", "null"]},
                            "fin": {"type": ["string", "null"]},
                        },
                        "required": ["signature", "debut", "fin"],
                    },
                    "duree": {"type": ["string", "null"]},
                    "montants": {"type": "array", "items": {"type": "string"}},
                    "obligations_principales": {"type": "array", "items": {"type": "string"}},
                    "clauses_resiliation": {"type": "array", "items": {"type": "string"}},
                    "penalites": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["parties", "dates"],
            }
            data = chat_json_schema(prompt, schema=schema, system="Extraction contrat", model=model)
            if isinstance(data, dict) and data:
                data.setdefault("dates", {"signature": None, "debut": None, "fin": None})
                for k in ["parties", "montants", "obligations_principales", "clauses_resiliation", "penalites"]:
                    data.setdefault(k, [])
                return data
        else:
            prompt = (
                "Extrait en JSON strict: {\n  \"sections_principales\": [string], \n  \"points_cles\": [string], \n  \"mots_cles\": [string]\n}\n\n"
                f"Sections:\n{joined}"
            )
            schema = {
                "type": "object",
                "properties": {
                    "sections_principales": {"type": "array", "items": {"type": "string"}},
                    "points_cles": {"type": "array", "items": {"type": "string"}},
                    "mots_cles": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["sections_principales"],
            }
            data = chat_json_schema(prompt, schema=schema, system="Extraction générique", model=model)
            if isinstance(data, dict) and data:
                for k in ["sections_principales", "points_cles", "mots_cles"]:
                    data.setdefault(k, [])
                return data

    # Fallback heuristic
    if t == "article_scientifique":
        return _extract_article(sections, doc)
    if t == "contrat":
        return _extract_contrat(sections)
    return _extract_autre(sections)
