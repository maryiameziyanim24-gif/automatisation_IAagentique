from __future__ import annotations
from typing import Dict, Any, Optional
import json

from app.llm_client import is_configured as llm_ready, chat_json_schema


SYNTH_SCHEMA = {
    "type": "object",
    "properties": {
        "summary": {"type": "string"},
        "key_points": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["summary", "key_points"],
}


def synthesize_article(extracted_info: Dict[str, Any], model: Optional[str] = None) -> Dict[str, Any]:
    """
    Utilise le LLM pour produire un résumé exécutif + points clés à partir d'une extraction structurée d'article.
    """
    if llm_ready() and extracted_info:
        sys = (
            "Tu rédiges des synthèses claires d'articles scientifiques à partir d'informations structurées. "
            "Retourne un JSON strict (summary + key_points)."
        )
        content = json.dumps(extracted_info, ensure_ascii=False)
        prompt = (
            "À partir des informations extraites ci-dessous (JSON), rédige: \n"
            "- un résumé exécutif (1-2 paragraphes) en français couvrant contexte, problème, objectifs, type d'article, approche, résultats, conclusions;\n"
            "- une liste de 5 à 8 points clés (phrases concises).\n\n"
            f"Infos extraites:\n{content}\n\n"
            "Réponse JSON STRICT: {\n  \"summary\": string, \n  \"key_points\": [string]\n}"
        )
        data = chat_json_schema(prompt, schema=SYNTH_SCHEMA, system=sys, model=model)
        if isinstance(data, dict):
            return data

    # Fallback simple
    text = (
        f"Contexte: {extracted_info.get('contexte', 'inconnu')}. "
        f"Problème: {extracted_info.get('probleme', 'inconnu')}. "
        f"Objectifs: {extracted_info.get('objectifs', 'inconnu')}. "
        f"Approche: {extracted_info.get('approche', 'inconnu')}. "
        f"Résultats: {extracted_info.get('resultats_principaux', 'inconnu')}. "
        f"Conclusions: {extracted_info.get('conclusions', 'inconnu')}."
    )
    return {"summary": text, "key_points": []}
