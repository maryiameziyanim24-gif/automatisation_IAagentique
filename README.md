# Analyseur multi-agents de PDF (Article, Contrat, Autre)

Objectif: application Python complète (UI Streamlit) qui analyse des PDF, détecte le type (article, contrat, autre), extrait des informations clés, synthétise un résumé, vérifie les affirmations (citations/pages) et génère un rapport PDF.

## Stack
- Python 3.10+
- Streamlit (UI)
- pypdf (extraction de texte)
- reportlab (génération PDF)
- rapidfuzz (appui à la vérification simple)
- OpenAI (LLM optionnel)

## Installation (Windows)
1) Créer un environnement (recommandé):
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2) Installer les dépendances:
```powershell
pip install -r requirements.txt
```

3) (Optionnel) Configurer OpenAI pour le LLM
```powershell
$env:OPENAI_API_KEY = "votre_cle_api"
# Optionnel: choisir le modèle
$env:OPENAI_MODEL = "gpt-4o-mini"
```

## Démarrer l'application
```powershell
streamlit run app/ui_app.py
```
Puis ouvrir le lien local (ex: http://localhost:8501).

## Organisation
```
app/
  ui_app.py         # UI Streamlit
  orchestrator.py   # Orchestrateur du pipeline
  agents/
    ingestion.py
    type_detection.py
    structuration.py
    extraction.py
    synthese.py
    verification.py
    rapport.py
data/
  examples/         # Placez ici quelques PDF d'exemple
  uploads/          # Fichiers uploadés via l'UI
reports/
  generated/        # Rapports PDF générés
docs/
  notes.md          # Notes / architecture / limites
```

## Flux (pipeline)
1. Ingestion → extrait le texte par page.
2. Détection de type → "article_scientifique" / "contrat" / "autre" (heuristiques).
3. Structuration → sections logiques (titres + contenu).
4. Extraction → champs clés selon le type (ou générique).
5. Synthèse → résumé + points clés (+ risques pour contrat).
6. Vérification → citations (pages) et alertes d'incertitude.
7. Rapport → PDF via reportlab.

LLM: activable dans la barre latérale (OpenAI). Sans clé, le système fonctionne en heuristique.

## Option "Forcer le type"
Dans la barre latérale, vous pouvez forcer le type de document (Article/Contrat/Autre) pour bypasser la détection (utile en démo ou pour comparer).

## Évaluation (détection de type)
Préparez un fichier CSV d’étiquettes (ex: `data/examples/labels_types.csv`).

Lancer l’évaluation sans LLM:
```powershell
python scripts/evaluate_types.py data/examples/labels_types.csv
```
Avec LLM activé:
```powershell
python scripts/evaluate_types.py data/examples/labels_types.csv --llm
```

## Remarques
- Cette version fonctionne sans clé LLM (heuristiques). Vous pouvez brancher un LLM plus tard.
- Les PDF scannés (images) ne sont pas gérés (pas d'OCR).
- Les heuristiques sont volontairement simples pour rester robustes en démo.
