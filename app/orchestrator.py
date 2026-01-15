from __future__ import annotations
from typing import List, Dict, Any
import os
import logging
import random

from app.agents.ingestion import ingest_pdfs
from app.agents.type_detection import detect_document_type
from app.agents.structuration import segment_document
from app.agents.extraction import extract_information
from app.agents.synthese import synthesize
from app.agents.verification import verify_and_annotate
from app.agents.rapport import build_report
from app.agents.visualisation import create_visualizations
from app.logging_config import configure_logging


def analyze_pdfs(file_paths: List[str], use_llm: bool = False, llm_model: str | None = None, force_type: str | None = None, detection_mode: str | None = None) -> List[Dict[str, Any]]:
    configure_logging()
    log = logging.getLogger("orchestrator")
    docs = ingest_pdfs(file_paths)
    results: List[Dict[str, Any]] = []

    for doc in docs:
        # Initialiser le suivi des agents
        agent_details = {
            "ingestion": {"status": "✅", "description": f"{doc.get('num_pages', 0)} pages extraites", "data": {}},
            "detection": {"status": "⏳", "description": "En cours...", "data": {}},
            "structuration": {"status": "⏳", "description": "En attente", "data": {}},
            "extraction": {"status": "⏳", "description": "En attente", "data": {}},
            "synthese": {"status": "⏳", "description": "En attente", "data": {}},
            "verification": {"status": "⏳", "description": "En attente", "data": {}},
            "visualisation": {"status": "⏳", "description": "En attente", "data": {}},
        }
        
        log.info("[1/6] Détection du type...")
        if force_type in {"article_scientifique", "contrat", "cv", "cours", "autre"}:
            doc["document_type"] = force_type
            doc["type_confidence"] = 1.0
            log.info(f"Type forcé: %s pour %s", force_type, doc.get("filename"))
            agent_details["detection"] = {
                "status": "✅", 
                "description": f"Type forcé: {force_type}",
                "data": {"type": force_type, "confidence": 1.0, "method": "Forcé par utilisateur"}
            }
        else:
            if detection_mode == "random":
                dtype = random.choice(["article_scientifique", "contrat", "cv", "cours", "autre"])
                conf = 0.5
                log.info("Type choisi aléatoirement: %s pour %s", dtype, doc.get("filename"))
                agent_details["detection"] = {
                    "status": "✅", 
                    "description": f"Type: {dtype} (aléatoire)",
                    "data": {"type": dtype, "confidence": conf, "method": "Sélection aléatoire"}
                }
            else:
                dtype, conf = detect_document_type(doc, use_llm=use_llm, model=llm_model)
                agent_details["detection"] = {
                    "status": "✅", 
                    "description": f"Type: {dtype} (conf: {conf:.2f})",
                    "data": {
                        "type": dtype, 
                        "confidence": conf, 
                        "method": "LLM + Heuristiques" if use_llm else "Heuristiques seules"
                    }
                }
            doc["document_type"] = dtype
            doc["type_confidence"] = conf
            log.info("Type détecté: %s (%.2f) pour %s", dtype, conf, doc.get("filename"))

        log.info("[2/6] Structuration...")
        sections = segment_document(doc, use_llm=use_llm, model=llm_model)
        doc["sections"] = sections
        # Gérer sections qui peuvent être des dicts ou des strings
        section_titles = []
        for s in sections:
            if isinstance(s, dict):
                section_titles.append(s.get("title", "Sans titre"))
            elif isinstance(s, str):
                section_titles.append(s)
            else:
                section_titles.append("Section")
        agent_details["structuration"] = {
            "status": "✅",
            "description": f"{len(sections)} sections identifiées",
            "data": {"sections": section_titles, "count": len(sections)}
        }

        log.info("[3/6] Extraction...")
        extracted = extract_information(doc, sections, use_llm=use_llm, model=llm_model)
        doc["extracted_info"] = extracted
        extracted_fields = list(extracted.keys()) if isinstance(extracted, dict) else []
        agent_details["extraction"] = {
            "status": "✅",
            "description": f"{len(extracted_fields)} champs extraits",
            "data": {"fields": extracted_fields, "method": "LLM + Extraction" if use_llm else "Extraction heuristique"}
        }

        log.info("[4/6] Synthèse...")
        synth = synthesize(doc, sections, extracted, use_llm=use_llm, model=llm_model)
        doc["synthesis"] = synth
        agent_details["synthese"] = {
            "status": "✅",
            "description": f"Résumé généré ({len(synth.get('key_points', []))} points clés)",
            "data": {
                "summary_length": len(synth.get("summary", "")),
                "key_points_count": len(synth.get("key_points", [])),
                "method": "LLM" if use_llm else "Heuristique"
            }
        }

        log.info("[5/6] Vérification...")
        ver = verify_and_annotate(doc, synth)
        doc["verification"] = ver
        agent_details["verification"] = {
            "status": "✅",
            "description": f"{len(ver.get('alerts', []))} alertes détectées",
            "data": {"alerts_count": len(ver.get("alerts", [])), "severity": "Haute" if ver.get("alerts") else "Basse"}
        }

        log.info("[6/7] Visualisations...")
        visualizations = create_visualizations(doc, extracted)
        doc["visualizations"] = visualizations
        viz_count = sum(1 for v in [visualizations.get("wordcloud"), visualizations.get("statistics"), visualizations.get("mindmap")] if v)
        agent_details["visualisation"] = {
            "status": "✅" if viz_count > 0 else "⚠️",
            "description": f"{viz_count}/3 visualisations générées",
            "data": {
                "wordcloud": "Disponible" if visualizations.get("wordcloud") else "Non généré",
                "statistics": "Disponible" if visualizations.get("statistics") else "Non généré",
                "mindmap": "Disponible" if visualizations.get("mindmap") else "Non généré"
            }
        }

        log.info("[7/7] Génération du rapport...")
        report_path = build_report(doc)
        doc["report_path"] = report_path
        doc["agent_details"] = agent_details

        results.append(doc)

    return results
