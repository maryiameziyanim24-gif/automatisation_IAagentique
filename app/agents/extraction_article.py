from __future__ import annotations
from typing import Dict, Any, Optional

from app.llm_client import is_configured as llm_ready, chat_json_schema


ARTICLE_SCHEMA = {
    "type": "object",
    "properties": {
        "contexte": {"type": "string"},
        "probleme": {"type": "string"},
        "objectifs": {"type": "string"},
        "type_article": {"type": "string", "enum": ["survey", "recherche_experimentale", "theorique", "autre"]},
        "approche": {"type": "string"},
        "resultats_principaux": {"type": "string"},
        "conclusions": {"type": "string"},
        "mots_cles": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["contexte", "probleme", "objectifs", "type_article", "approche", "resultats_principaux", "conclusions", "mots_cles"],
}


def extract_information_for_article(sections: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    """
    Utilise le LLM pour extraire un canevas enrichi pour articles scientifiques.
    Retourne un dictionnaire conforme à ARTICLE_SCHEMA. Fallback minimal si LLM indisponible.
    """
    joined = []
    for s in sections.get("sections", []):
        title = s.get("title", "")
        content = s.get("content", "")
        joined.append(f"[SECTION: {title}]\n{content}")
    sections_text = "\n\n".join(joined)

    if llm_ready() and sections_text.strip():
        sys = (
            "Tu es un agent qui analyse des ARTICLES SCIENTIFIQUES et extrait des informations structurées. "
            "Réponds STRICTEMENT en JSON valide correspondant au schéma donné."
        )
        prompt = (
            "Extrait les champs suivants et renvoie un JSON STRICT:\n"
            "{\n  \"contexte\": string,\n  \"probleme\": string,\n  \"objectifs\": string,\n  \"type_article\": \"survey|recherche_experimentale|theorique|autre\",\n  \"approche\": string,\n  \"resultats_principaux\": string,\n  \"conclusions\": string,\n  \"mots_cles\": [string]\n}\n\n"
            "Interdictions: pas de mots vides en mots_cles (pas 'the', 'and', 'of'). Si une info manque, essaie de l'inférer.\n\n"
            f"Sections de l'article:\n\n{sections_text}"
        )
        data = chat_json_schema(prompt, schema=ARTICLE_SCHEMA, system=sys, model=model)
        if isinstance(data, dict):
            return data

    # Fallback minimal
    return {
        "contexte": "inconnu",
        "probleme": "inconnu",
        "objectifs": "inconnu",
        "type_article": "autre",
        "approche": "inconnu",
        "resultats_principaux": "inconnu",
        "conclusions": "inconnu",
        "mots_cles": [],
    }
