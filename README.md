#  Analyseur Multi-Agents de Documents PDF

**Système d'analyse intelligente de documents PDF avec pipeline multi-agents et visualisations automatiques**

Analyse automatique de **5 types de documents** : Articles scientifiques, Contrats, CV, Cours et Documents génériques.

---

##  Fonctionnalités

###  Détection Automatique de Type
- **Articles scientifiques** : Problématique, méthodes, résultats, conclusion
- **Contrats** : Parties, dates, montants, obligations
- **CV** : Expérience, formation, compétences
- **Cours** : Chapitres, exercices, objectifs pédagogiques
- **Documents génériques** : Sections, points clés, mots-clés

###  Visualisations Automatiques
-  **Nuage de mots** : Termes les plus fréquents
-  **Graphiques statistiques** : Sections et éléments extraits
-  **Mindmap** : Carte mentale de la structure

###  Pipeline Multi-Agents (7 Agents)
1. Agent d'Ingestion
2. Agent de Détection
3. Agent de Structuration
4. Agent d'Extraction
5. Agent de Synthèse
6. Agent de Vérification
7. Agent de Visualisation

###  LLM : Mistral AI Cloud
- Modèles supportés : mistral-small, mistral-medium, mistral-large
- Performances : ~20-30s par analyse
- Mode heuristique sans API key

---

##  Installation

```powershell
git clone https://github.com/maryiameziyanim24-gif/automatisation_IAagentique.git
cd automatisation_IAagentique
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

Configuration Mistral AI (optionnel) :
```powershell
setx MISTRAL_API_KEY "votre_cle"
```

---

##  Utilisation

```powershell
streamlit run app/ui_app.py
```

Ouvrir http://localhost:8501

---

##  Stack Technique

- pypdf 4.0.2
- mistralai 1.10.0
- reportlab 4.2.2
- wordcloud 1.9.3
- matplotlib 3.8.2
- networkx 3.2.1
- streamlit 1.40.2

---

##  Auteur

**Maryame Ziyani**
- GitHub: [@maryiameziyanim24-gif](https://github.com/maryiameziyanim24-gif)

 N'hésitez pas à laisser une étoile sur GitHub !
