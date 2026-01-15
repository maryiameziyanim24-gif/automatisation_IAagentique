import os
import sys

# Ensure repository root is on sys.path so 'app' package resolves
APP_DIR = os.path.abspath(os.path.dirname(__file__))
ROOT = os.path.abspath(os.path.join(APP_DIR, '..'))
for p in (ROOT,):
    if p not in sys.path:
        sys.path.insert(0, p)

import io
import time
import streamlit as st
from typing import List

from app.orchestrator import analyze_pdfs
from app.llm_client import is_configured as llm_ready
from app.llm_client import has_model, list_models

UPLOAD_DIR = os.path.join("data", "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="Analyseur multi-agents de PDF", layout="wide")
st.title("Analyseur multi-agents de PDF")
st.caption("Types: article, contrat, cv, cours, autre. Heuristiques avec option LLM (Mistral AI).")

with st.sidebar:
    st.header("Options")
    st.info("💡 Conseil: Désactivez le LLM pour une analyse rapide (5-10s), activez-le pour plus de précision avec Mistral (~30s-1min).")
    use_llm = st.checkbox("Activer LLM (Mistral AI)", value=False)
    
    # Get available models
    available_models = list_models() if llm_ready() else []
    if available_models:
        llm_model = st.selectbox(
            "Modèle Mistral",
            options=available_models,
            index=0,
            help="Sélectionnez un modèle. mistral-small = rapide, mistral-large = précis"
        )
    else:
        llm_model = st.text_input("Modèle Mistral", value="mistral-small-latest", help="Ex: mistral-small-latest")
    
    if use_llm and not llm_ready():
        st.warning("MISTRAL_API_KEY manquante. Définissez-la dans l'environnement.")
    detection_mode = st.radio(
        "Mode de détection",
        options=["Auto", "Aléatoire"],
        index=0,
        help="'Aléatoire' choisit un type au hasard (article/contrat/cv/cours/autre)."
    )

uploaded_files = st.file_uploader(
    "Choisissez un ou plusieurs fichiers PDF",
    type=["pdf"],
    accept_multiple_files=True,
    help="Glissez-déposez vos PDF ici."
)

col1, col2 = st.columns([1,1])
with col1:
    run_btn = st.button("Analyser")
with col2:
    st.write("")


def _save_uploaded(files) -> List[str]:
    paths = []
    for f in files:
        name = f.name
        base, ext = os.path.splitext(name)
        ts = int(time.time() * 1000)
        safe = f"{base}_{ts}{ext}"
        path = os.path.join(UPLOAD_DIR, safe)
        with open(path, "wb") as out:
            out.write(f.read())
        paths.append(path)
    return paths

if run_btn and uploaded_files:
    with st.spinner("Analyse en cours..."):
        file_paths = _save_uploaded(uploaded_files)
        start = time.time()
        results = analyze_pdfs(
            file_paths,
            use_llm=use_llm and llm_ready(),
            llm_model=llm_model if use_llm else None,
            force_type=None,
            detection_mode=("random" if detection_mode == "Aléatoire" else None),
        )
        elapsed = time.time() - start

    st.success(f"Analyse terminée en {elapsed:.2f}s")

    for doc in results:
        st.markdown(f"### Résultat: {doc['filename']}")
        st.write(f"Type détecté: **{doc['document_type']}** (confiance {doc.get('type_confidence', 0):.2f})")
        st.write(f"Pages: {doc.get('num_pages')}")

        # Résumé
        with st.expander("Résumé et points clés", expanded=True):
            st.markdown("#### Résumé exécutif")
            st.write(doc["synthesis"]["summary"]) 
            st.markdown("#### Points clés")
            for p in doc["synthesis"]["key_points"]:
                st.write("- " + p)
            if doc["synthesis"].get("risks_or_remarks"):
                st.markdown("#### Risques / remarques")
                for r in doc["synthesis"]["risks_or_remarks"]:
                    st.write("- " + r)

        # Alertes
        with st.expander("Alertes / Vérification", expanded=False):
            alerts = doc["verification"]["alerts"]
            if alerts:
                for a in alerts:
                    st.error(a)
            else:
                st.info("Aucune alerte majeure détectée (heuristique).")

        # Télécharger rapport
        rp = doc["report_path"]
        if os.path.exists(rp):
            with open(rp, "rb") as f:
                st.download_button(
                    label="Télécharger le rapport PDF",
                    data=f.read(),
                    file_name=os.path.basename(rp),
                    mime="application/pdf",
                )
        st.divider()

st.markdown("---")
