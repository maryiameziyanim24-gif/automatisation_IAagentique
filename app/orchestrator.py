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
from app.logging_config import configure_logging


def analyze_pdfs(file_paths: List[str], use_llm: bool = False, llm_model: str | None = None, force_type: str | None = None, detection_mode: str | None = None) -> List[Dict[str, Any]]:
    configure_logging()
    log = logging.getLogger("orchestrator")
    docs = ingest_pdfs(file_paths)
    results: List[Dict[str, Any]] = []

    for doc in docs:
        log.info("[1/6] Détection du type...")
        if force_type in {"article_scientifique", "contrat", "cv", "cours", "autre"}:
            doc["document_type"] = force_type
            doc["type_confidence"] = 1.0
            log.info(f"Type forcé: %s pour %s", force_type, doc.get("filename"))
        else:
            if detection_mode == "random":
                dtype = random.choice(["article_scientifique", "contrat", "cv", "cours", "autre"])
                conf = 0.5
                log.info("Type choisi aléatoirement: %s pour %s", dtype, doc.get("filename"))
            else:
                dtype, conf = detect_document_type(doc, use_llm=use_llm, model=llm_model)
            doc["document_type"] = dtype
            doc["type_confidence"] = conf
            log.info("Type détecté: %s (%.2f) pour %s", dtype, conf, doc.get("filename"))

        log.info("[2/6] Structuration...")
        sections = segment_document(doc, use_llm=use_llm, model=llm_model)
        doc["sections"] = sections

        log.info("[3/6] Extraction...")
        extracted = extract_information(doc, sections, use_llm=use_llm, model=llm_model)
        doc["extracted_info"] = extracted

        log.info("[4/6] Synthèse...")
        synth = synthesize(doc, sections, extracted, use_llm=use_llm, model=llm_model)
        doc["synthesis"] = synth

        log.info("[5/6] Vérification...")
        ver = verify_and_annotate(doc, synth)
        doc["verification"] = ver

        log.info("[6/6] Génération du rapport...")
        report_path = build_report(doc)
        doc["report_path"] = report_path

        results.append(doc)

    return results
