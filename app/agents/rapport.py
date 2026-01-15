from __future__ import annotations
from typing import Dict, Any, List
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
import os
import datetime as dt


def _p(text: str, styles):
    return Paragraph(text.replace("\n", "<br/>"), styles["BodyText"]) 


def build_report(doc: Dict[str, Any], out_dir: str = "reports/generated") -> str:
    os.makedirs(out_dir, exist_ok=True)
    base = os.path.splitext(os.path.basename(doc.get("filename", "rapport")))[0]
    ts = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    out_path = os.path.join(out_dir, f"rapport_{base}_{ts}.pdf")

    styles = getSampleStyleSheet()
    story: List[Any] = []

    # Page de garde
    title = f"Rapport d'analyse de document PDF"
    story.append(Paragraph(f"<b>{title}</b>", styles["Title"]))
    story.append(Spacer(1, 12))
    story.append(_p(f"Fichier: <b>{doc.get('filename')}</b>", styles))
    story.append(_p(f"Type détecté: <b>{doc.get('document_type')}</b>", styles))
    story.append(_p(f"Pages: <b>{doc.get('num_pages')}</b>", styles))
    story.append(_p(f"Date d'analyse: <b>{dt.datetime.now().strftime('%Y-%m-%d %H:%M')}</b>", styles))
    story.append(Spacer(1, 16))

    # Résumé
    synth = doc.get("synthesis", {})
    story.append(Paragraph("<b>Résumé exécutif</b>", styles["Heading2"]))
    story.append(_p(synth.get("summary", ""), styles))
    story.append(Spacer(1, 12))

    # Points clés
    kp = synth.get("key_points", [])
    if kp:
        story.append(Paragraph("<b>Points clés</b>", styles["Heading2"]))
        for p in kp:
            story.append(_p(f"• {p}", styles))
        story.append(Spacer(1, 12))

    # Alertes
    ver = doc.get("verification", {})
    alerts = ver.get("alerts", [])
    if alerts:
        story.append(Paragraph("<b>Alertes / Incertitudes</b>", styles["Heading2"]))
        for a in alerts:
            story.append(_p(f"• {a}", styles))
        story.append(Spacer(1, 12))

    # Informations extraites (tableaux simples selon type)
    story.append(Paragraph("<b>Informations extraites</b>", styles["Heading2"]))
    t = doc.get("document_type")
    info = doc.get("extracted_info", {})

    if t == "article_scientifique":
        rows = [
            ["Problème", (info.get("probleme") or "-")[:300]],
            ["Objectifs", (info.get("objectifs") or "-")[:300]],
            ["Méthodes", (info.get("methodes") or "-")[:300]],
            ["Résultats", (info.get("resultats_principaux") or "-")[:300]],
            ["Conclusion", (info.get("conclusion") or "-")[:300]],
            ["Mots-clés", ", ".join(info.get("mots_cles") or [])],
        ]
    elif t == "contrat":
        rows = [
            ["Parties", " | ".join(info.get("parties") or [])[:300]],
            ["Dates (sig/début/fin)", f"{(info.get('dates') or {}).get('signature')} / {(info.get('dates') or {}).get('debut')} / {(info.get('dates') or {}).get('fin')}"] ,
            ["Durée", info.get("duree") or "-"],
            ["Montants", ", ".join(info.get("montants") or [])[:300]],
            ["Obligations (extraits)", " | ".join(info.get("obligations_principales") or [])[:300]],
            ["Résiliation (extraits)", " | ".join(info.get("clauses_resiliation") or [])[:300]],
            ["Pénalités (extraits)", " | ".join(info.get("penalites") or [])[:300]],
        ]
    else:
        rows = [
            ["Sections principales", ", ".join(info.get("sections_principales") or [])[:300]],
            ["Points clés (mots)", ", ".join(info.get("points_cles") or [])[:300]],
            ["Mots-clés", ", ".join(info.get("mots_cles") or [])[:300]],
        ]

    tbl = Table(rows, hAlign="LEFT", colWidths=[140, 360])
    tbl.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.whitesmoke),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    story.append(tbl)

    # Annexes minimales: références de pages pour quelques points clés
    akp = ver.get("annotated_key_points", [])
    if akp:
        story.append(Spacer(1, 16))
        story.append(Paragraph("<b>Annexe: Références de pages (approx.)</b>", styles["Heading2"]))
        for it in akp[:8]:
            pgs = ", ".join(map(str, it.get("page_refs", []))) or "-"
            story.append(_p(f"• {it.get('text')} (pages: {pgs}, support: {it.get('support')})", styles))

    doc_pdf = SimpleDocTemplate(out_path, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    doc_pdf.build(story)

    return out_path
