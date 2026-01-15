from __future__ import annotations
from typing import Dict, Any, List
from rapidfuzz import fuzz


def verify_and_annotate(doc: Dict[str, Any], synthesis: Dict[str, Any]) -> Dict[str, Any]:
    pages = doc.get("pages", [])
    key_points = synthesis.get("key_points", [])

    annotated_key_points: List[Dict[str, Any]] = []
    alerts: List[str] = []

    for kp in key_points:
        scores = []
        for p in pages:
            text = p.get("text", "")
            score = fuzz.token_set_ratio(kp, text)
            scores.append((score, p.get("page_number")))
        scores.sort(reverse=True, key=lambda x: x[0])
        top = [pg for sc, pg in scores[:2] if sc >= 40]
        support = "fort" if scores and scores[0][0] >= 70 else ("moyen" if scores and scores[0][0] >= 40 else "incertain")
        if not top:
            alerts.append(f"Point non clairement supporté: '{kp[:60]}...'")
        annotated_key_points.append({
            "text": kp,
            "page_refs": top,
            "support": support,
        })

    annotated_summary = synthesis.get("summary", "")

    return {
        "annotated_summary": annotated_summary,
        "annotated_key_points": annotated_key_points,
        "alerts": alerts,
    }
