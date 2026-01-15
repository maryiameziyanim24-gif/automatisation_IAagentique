from __future__ import annotations
from typing import Dict, Any, List
import os
import io
import base64
from collections import Counter
import logging

log = logging.getLogger("visualisation")

# Import des bibliothèques de visualisation
try:
    from wordcloud import WordCloud
    import matplotlib
    matplotlib.use('Agg')  # Backend sans interface graphique
    import matplotlib.pyplot as plt
    import networkx as nx
    VISUALIZATION_AVAILABLE = True
except ImportError:
    VISUALIZATION_AVAILABLE = False
    log.warning("Bibliothèques de visualisation non disponibles. Installez: wordcloud, matplotlib, networkx")


def generate_wordcloud(text: str, max_words: int = 100) -> str | None:
    """Génère un nuage de mots et retourne l'image en base64"""
    if not VISUALIZATION_AVAILABLE:
        return None
    
    try:
        # Créer le nuage de mots
        wordcloud = WordCloud(
            width=800, 
            height=400, 
            background_color='white',
            max_words=max_words,
            colormap='viridis',
            relative_scaling=0.5,
            min_font_size=10
        ).generate(text)
        
        # Sauvegarder dans un buffer
        buf = io.BytesIO()
        plt.figure(figsize=(10, 5))
        plt.imshow(wordcloud, interpolation='bilinear')
        plt.axis('off')
        plt.tight_layout(pad=0)
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # Encoder en base64
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return img_base64
    except Exception as e:
        log.error(f"Erreur génération wordcloud: {e}")
        return None


def generate_statistics_chart(extracted_info: Dict[str, Any], doc_type: str) -> str | None:
    """Génère un graphique de statistiques selon le type de document"""
    if not VISUALIZATION_AVAILABLE:
        return None
    
    try:
        fig, axes = plt.subplots(1, 2, figsize=(12, 5))
        
        # Graphique 1: Nombre de mots-clés
        if 'mots_cles' in extracted_info:
            keywords = extracted_info['mots_cles'][:10]
            if keywords:
                axes[0].barh(range(len(keywords)), [1] * len(keywords), color='steelblue')
                axes[0].set_yticks(range(len(keywords)))
                axes[0].set_yticklabels(keywords)
                axes[0].set_xlabel('Fréquence relative')
                axes[0].set_title('Top 10 Mots-Clés')
                axes[0].invert_yaxis()
        
        # Graphique 2: Statistiques selon le type
        if doc_type == 'article_scientifique':
            sections = ['Problème', 'Objectifs', 'Méthodes', 'Résultats', 'Conclusion']
            values = [
                1 if extracted_info.get('probleme') else 0,
                1 if extracted_info.get('objectifs') else 0,
                1 if extracted_info.get('methodes') else 0,
                1 if extracted_info.get('resultats_principaux') else 0,
                1 if extracted_info.get('conclusion') else 0,
            ]
            axes[1].bar(sections, values, color=['green' if v else 'red' for v in values])
            axes[1].set_ylabel('Présence (1=Oui, 0=Non)')
            axes[1].set_title('Sections Identifiées')
            axes[1].tick_params(axis='x', rotation=45)
        elif doc_type == 'contrat':
            data = {
                'Parties': len(extracted_info.get('parties', [])),
                'Montants': len(extracted_info.get('montants', [])),
                'Obligations': len(extracted_info.get('obligations_principales', []))[:5],
                'Clauses': len(extracted_info.get('clauses_resiliation', []))[:5],
            }
            axes[1].bar(data.keys(), data.values(), color='coral')
            axes[1].set_ylabel('Nombre d\'éléments')
            axes[1].set_title('Éléments Extraits du Contrat')
        else:
            sections_count = len(extracted_info.get('sections_principales', []))
            points_count = len(extracted_info.get('points_cles', []))
            axes[1].bar(['Sections', 'Points Clés'], [sections_count, points_count], color='teal')
            axes[1].set_ylabel('Nombre')
            axes[1].set_title('Contenu du Document')
        
        plt.tight_layout()
        
        # Sauvegarder dans un buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # Encoder en base64
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return img_base64
    except Exception as e:
        log.error(f"Erreur génération graphique statistiques: {e}")
        return None


def generate_mindmap(extracted_info: Dict[str, Any], doc_type: str, doc_title: str) -> str | None:
    """Génère une mindmap simple du document"""
    if not VISUALIZATION_AVAILABLE:
        return None
    
    try:
        G = nx.DiGraph()
        
        # Nœud central
        G.add_node("Document", label=doc_title[:30])
        
        # Ajouter des branches selon le type
        if doc_type == 'article_scientifique':
            branches = {
                'Problème': extracted_info.get('probleme', '')[:50] if extracted_info.get('probleme') else '',
                'Méthodes': extracted_info.get('methodes', '')[:50] if extracted_info.get('methodes') else '',
                'Résultats': extracted_info.get('resultats_principaux', '')[:50] if extracted_info.get('resultats_principaux') else '',
                'Conclusion': extracted_info.get('conclusion', '')[:50] if extracted_info.get('conclusion') else '',
            }
            for branch, content in branches.items():
                if content:
                    G.add_node(branch, label=branch)
                    G.add_edge("Document", branch)
        elif doc_type == 'contrat':
            if extracted_info.get('parties'):
                G.add_node('Parties', label='Parties')
                G.add_edge("Document", 'Parties')
            if extracted_info.get('montants'):
                G.add_node('Montants', label='Montants')
                G.add_edge("Document", 'Montants')
            if extracted_info.get('obligations_principales'):
                G.add_node('Obligations', label='Obligations')
                G.add_edge("Document", 'Obligations')
        else:
            sections = extracted_info.get('sections_principales', [])[:5]
            for i, sec in enumerate(sections):
                node_name = f"Section{i+1}"
                G.add_node(node_name, label=sec[:30])
                G.add_edge("Document", node_name)
        
        # Dessiner la mindmap
        fig, ax = plt.subplots(figsize=(10, 8))
        pos = nx.spring_layout(G, k=2, iterations=50)
        
        # Dessiner les nœuds
        nx.draw_networkx_nodes(G, pos, node_color='lightblue', node_size=3000, alpha=0.9, ax=ax)
        
        # Dessiner les arêtes
        nx.draw_networkx_edges(G, pos, edge_color='gray', arrows=True, arrowsize=20, ax=ax)
        
        # Ajouter les labels
        labels = nx.get_node_attributes(G, 'label')
        if not labels:
            labels = {node: node for node in G.nodes()}
        nx.draw_networkx_labels(G, pos, labels, font_size=10, font_weight='bold', ax=ax)
        
        ax.axis('off')
        plt.title(f"Mindmap: {doc_title[:40]}", fontsize=14, fontweight='bold')
        plt.tight_layout()
        
        # Sauvegarder dans un buffer
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100, bbox_inches='tight')
        plt.close()
        
        # Encoder en base64
        buf.seek(0)
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return img_base64
    except Exception as e:
        log.error(f"Erreur génération mindmap: {e}")
        return None


def create_visualizations(doc: Dict[str, Any], extracted_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Génère toutes les visualisations pour un document
    
    Returns:
        Dict avec les clés:
        - wordcloud: image base64 du nuage de mots
        - statistics: image base64 des statistiques
        - mindmap: image base64 de la mindmap
    """
    if not VISUALIZATION_AVAILABLE:
        log.warning("Visualisations désactivées (bibliothèques manquantes)")
        return {
            "wordcloud": None,
            "statistics": None,
            "mindmap": None,
            "status": "unavailable"
        }
    
    # Extraire le texte complet pour le wordcloud
    full_text = ""
    for page in doc.get("pages", []):
        full_text += page.get("text", "") + " "
    
    # Limiter le texte pour éviter les problèmes de mémoire
    full_text = full_text[:10000]
    
    doc_type = doc.get("document_type", "autre")
    doc_title = doc.get("filename", "Document")
    
    return {
        "wordcloud": generate_wordcloud(full_text, max_words=80) if full_text.strip() else None,
        "statistics": generate_statistics_chart(extracted_info, doc_type),
        "mindmap": generate_mindmap(extracted_info, doc_type, doc_title),
        "status": "generated"
    }
