from __future__ import annotations
from typing import Dict, Any, List, Optional
from app.llm_client import is_configured as llm_ready, chat_json_schema
from app.agents.synthese_article import synthesize_article


def synthesize(doc: Dict[str, Any], sections: Dict[str, Any], extracted: Dict[str, Any], use_llm: bool = False, model: Optional[str] = None) -> Dict[str, Any]:
    t = doc.get("document_type", "autre")
    summary = ""
    key_points: List[str] = []
    risks_or_remarks: List[str] = []

    # Optional LLM summarization
    if use_llm and llm_ready():
        if t == "article_scientifique":
            return synthesize_article(extracted, model=model)
        sys = "Tu rends un JSON strict contenant summary, key_points, et éventuellement risks_or_remarks."
        prompt = (
            "Donne un JSON strict: {\n  \"summary\": string, \n  \"key_points\": [string], \n  \"risks_or_remarks\": [string]\n}\n\n"
            f"Type: {t}\n\n"
            f"Infos extraites:\n{extracted}\n"
        )
        schema = {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "key_points": {"type": "array", "items": {"type": "string"}},
                "risks_or_remarks": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["summary", "key_points"],
        }
        data = chat_json_schema(prompt, schema=schema, system=sys, model=model)
        if isinstance(data, dict) and data.get("summary") and isinstance(data.get("key_points"), list):
            data.setdefault("risks_or_remarks", [])
            return data

    if t == "article_scientifique":
        # Build summary with available content
        problem = extracted.get("probleme") or ""
        methods = extracted.get("methodes") or ""
        results = extracted.get("resultats_principaux") or ""
        conclusion = extracted.get("conclusion") or ""
        
        if problem or methods or results or conclusion:
            parts = []
            if problem:
                parts.append("Contexte: " + problem[:400])
            if methods:
                parts.append("Méthodes: " + methods[:250])
            if results:
                parts.append("Résultats: " + results[:250])
            if conclusion:
                parts.append("Conclusion: " + conclusion[:250])
            summary = "\n\n".join(parts)
        else:
            # Absolute fallback: use document text
            all_text = "\n".join([p.get("text", "")[:1000] for p in doc.get("pages", [])[:2]])
            summary = f"Document scientifique analysé. Contenu: {all_text[:600]}..."
        
        key_points = []
        if extracted.get("objectifs"):
            key_points.append(f"Objectifs: {extracted['objectifs'][:150]}")
        if extracted.get("methodes"):
            key_points.append(f"Méthodes: {extracted['methodes'][:150]}")
        if extracted.get("resultats_principaux"):
            key_points.append(f"Résultats: {extracted['resultats_principaux'][:150]}")
        
        for k in (extracted.get("mots_cles") or [])[:5]:
            key_points.append(f"Mot-clé: {k}")
        
        if not key_points:
            key_points.append("Analyse heuristique: structure de document scientifique détectée")

    elif t == "contrat":
        parties = extracted.get("parties") or []
        dates = extracted.get("dates") or {}
        summary = (
            "Synthèse du contrat: parties principales mentionnées, dates clés si disponibles, "
            "durée et obligations résumées."
        )
        key_points = []
        if parties:
            key_points.append(f"Parties (extraits): {parties[0][:120]}")
        if dates:
            key_points.append(
                f"Dates (sig/début/fin): {dates.get('signature')} / {dates.get('debut')} / {dates.get('fin')}"
            )
        if extracted.get("duree"):
            key_points.append(f"Durée: {extracted['duree']}")
        if extracted.get("montants"):
            key_points.append(f"Montants (extraits): {', '.join(extracted['montants'][:3])}")
        if extracted.get("obligations_principales"):
            key_points.append("Obligations: présentées (extraits)")
        if extracted.get("clauses_resiliation"):
            key_points.append("Résiliation: clauses identifiées (extraits)")
        if extracted.get("penalites"):
            key_points.append("Pénalités: mentions détectées (extraits)")

        # Risques simples
        if not dates.get("fin"):
            risks_or_remarks.append("Date de fin non claire ou absente.")
        if not extracted.get("obligations_principales"):
            risks_or_remarks.append("Obligations principales peu explicites.")

    else:
        summary = "Résumé générique: sections détectées et points saillants extraits de manière heuristique."
        titles = (extracted.get("sections_principales") or [])[:5]
        if titles:
            key_points.append("Sections principales: " + ", ".join(titles))
        for k in (extracted.get("mots_cles") or [])[:5]:
            key_points.append(f"Mot-clé: {k}")

    return {
        "summary": summary,
        "key_points": key_points,
        "risks_or_remarks": risks_or_remarks,
    }
