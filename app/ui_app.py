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
import base64
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

        # Visualisations
        visualizations = doc.get("visualizations", {})
        if visualizations and visualizations.get("status") == "generated":
            with st.expander("📊 Visualisations (Graphiques, Nuages de Mots, Mindmap)", expanded=False):
                st.markdown("### Visualisations Générées")
                
                # Nuage de mots
                if visualizations.get("wordcloud"):
                    st.markdown("#### ☁️ Nuage de Mots")
                    st.image(f"data:image/png;base64,{visualizations['wordcloud']}", use_container_width=True)
                    st.caption("Visualisation des mots les plus fréquents dans le document")
                    st.divider()
                
                # Graphiques statistiques
                if visualizations.get("statistics"):
                    st.markdown("#### 📈 Statistiques")
                    st.image(f"data:image/png;base64,{visualizations['statistics']}", use_container_width=True)
                    st.caption("Analyse statistique du contenu extrait")
                    st.divider()
                
                # Mindmap
                if visualizations.get("mindmap"):
                    st.markdown("#### 🧠 Carte Mentale (Mindmap)")
                    st.image(f"data:image/png;base64,{visualizations['mindmap']}", use_container_width=True)
                    st.caption("Structure logique du document")
        elif visualizations and visualizations.get("status") == "unavailable":
            with st.expander("📊 Visualisations", expanded=False):
                st.warning("⚠️ Visualisations indisponibles. Installez les dépendances: `pip install wordcloud matplotlib networkx`")


        # Détails des agents
        with st.expander("🔍 Détails des Agents (Pipeline)", expanded=False):
            st.markdown("### Pipeline d'analyse multi-agents")
            st.caption("Visualisez le travail de chaque agent dans le processus d'analyse")
            
            agent_details = doc.get("agent_details", {})
            
            # Agent 1: Ingestion
            with st.container():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f"### {agent_details.get('ingestion', {}).get('status', '⏳')}")
                with col2:
                    st.markdown("#### 1️⃣ Agent d'Ingestion")
                    st.write(f"**Rôle**: Extraire le texte brut du PDF page par page")
                    st.write(f"**Résultat**: {agent_details.get('ingestion', {}).get('description', 'N/A')}")
                st.divider()
            
            # Agent 2: Détection
            with st.container():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f"### {agent_details.get('detection', {}).get('status', '⏳')}")
                with col2:
                    st.markdown("#### 2️⃣ Agent de Détection")
                    st.write(f"**Rôle**: Identifier le type de document (article, contrat, CV, cours, autre)")
                    st.write(f"**Résultat**: {agent_details.get('detection', {}).get('description', 'N/A')}")
                    det_data = agent_details.get('detection', {}).get('data', {})
                    if det_data:
                        st.json(det_data)
                st.divider()
            
            # Agent 3: Structuration
            with st.container():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f"### {agent_details.get('structuration', {}).get('status', '⏳')}")
                with col2:
                    st.markdown("#### 3️⃣ Agent de Structuration")
                    st.write(f"**Rôle**: Segmenter le document en sections logiques")
                    st.write(f"**Résultat**: {agent_details.get('structuration', {}).get('description', 'N/A')}")
                    struct_data = agent_details.get('structuration', {}).get('data', {})
                    if struct_data.get('sections'):
                        st.write("**Sections identifiées**:")
                        for i, section in enumerate(struct_data['sections'][:10], 1):
                            st.write(f"{i}. {section}")
                        if len(struct_data['sections']) > 10:
                            st.caption(f"... et {len(struct_data['sections']) - 10} autres sections")
                st.divider()
            
            # Agent 4: Extraction
            with st.container():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f"### {agent_details.get('extraction', {}).get('status', '⏳')}")
                with col2:
                    st.markdown("#### 4️⃣ Agent d'Extraction")
                    st.write(f"**Rôle**: Extraire les informations structurées selon le type de document")
                    st.write(f"**Résultat**: {agent_details.get('extraction', {}).get('description', 'N/A')}")
                    ext_data = agent_details.get('extraction', {}).get('data', {})
                    if ext_data.get('fields'):
                        st.write("**Champs extraits**:", ", ".join(ext_data['fields']))
                        st.caption(f"Méthode: {ext_data.get('method', 'N/A')}")
                st.divider()
            
            # Agent 5: Synthèse
            with st.container():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f"### {agent_details.get('synthese', {}).get('status', '⏳')}")
                with col2:
                    st.markdown("#### 5️⃣ Agent de Synthèse")
                    st.write(f"**Rôle**: Générer un résumé exécutif et identifier les points clés")
                    st.write(f"**Résultat**: {agent_details.get('synthese', {}).get('description', 'N/A')}")
                    synth_data = agent_details.get('synthese', {}).get('data', {})
                    if synth_data:
                        st.caption(f"Longueur résumé: {synth_data.get('summary_length', 0)} caractères")
                        st.caption(f"Méthode: {synth_data.get('method', 'N/A')}")
                st.divider()
            
            # Agent 6: Vérification
            with st.container():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f"### {agent_details.get('verification', {}).get('status', '⏳')}")
                with col2:
                    st.markdown("#### 6️⃣ Agent de Vérification")
                    st.write(f"**Rôle**: Vérifier la cohérence et identifier les anomalies potentielles")
                    st.write(f"**Résultat**: {agent_details.get('verification', {}).get('description', 'N/A')}")
                    ver_data = agent_details.get('verification', {}).get('data', {})
                    if ver_data:
                        severity = ver_data.get('severity', 'N/A')
                        if severity == "Haute":
                            st.error(f"⚠️ Sévérité: {severity}")
                        else:
                            st.success(f"✅ Sévérité: {severity}")
                st.divider()
            
            # Agent 7: Visualisation
            with st.container():
                col1, col2 = st.columns([1, 5])
                with col1:
                    st.markdown(f"### {agent_details.get('visualisation', {}).get('status', '⏳')}")
                with col2:
                    st.markdown("#### 7️⃣ Agent de Visualisation")
                    st.write(f"**Rôle**: Générer des graphiques, nuages de mots et mindmaps")
                    st.write(f"**Résultat**: {agent_details.get('visualisation', {}).get('description', 'N/A')}")
                    viz_data = agent_details.get('visualisation', {}).get('data', {})
                    if viz_data:
                        st.write(f"- Nuage de mots: {viz_data.get('wordcloud', 'N/A')}")
                        st.write(f"- Statistiques: {viz_data.get('statistics', 'N/A')}")
                        st.write(f"- Mindmap: {viz_data.get('mindmap', 'N/A')}")

        # Rapport PDF
        rp = doc["report_path"]
        if os.path.exists(rp):
            st.markdown("### 📄 Rapport PDF")
            
            with open(rp, "rb") as f:
                pdf_bytes = f.read()
            
            # Bouton pour télécharger
            st.download_button(
                label="📥 Télécharger le rapport PDF",
                data=pdf_bytes,
                file_name=os.path.basename(rp),
                mime="application/pdf",
                use_container_width=True
            )
            
            st.info("💡 Téléchargez le rapport et ouvrez-le avec votre lecteur PDF pour le consulter.")
        
        st.divider()

st.markdown("---")
