from __future__ import annotations
import os
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

BASE = os.path.join(os.path.dirname(__file__), '..', 'data', 'examples')

ARTICLE_TEXT = (
    "Abstract\nThis paper presents a method...\n\n"
    "Introduction\nIn this study we investigate...\n\n"
    "Methods\nWe used a randomized trial...\n\n"
    "Results\nThe results indicate significant improvement...\n\n"
    "Conclusion\nWe conclude that...\n\nReferences\n[1] ..."
)

CONTRACT_TEXT = (
    "Le présent contrat est conclu entre la Société X (Fournisseur) et la Société Y (Client).\n\n"
    "Parties\nDénommées ci-après les Parties.\n\n"
    "Durée du contrat\nCe contrat entre en vigueur le 2024-01-15 pour une durée de 12 mois.\n\n"
    "Prix et Paiement\nLe montant total est de 10 000 EUR à payer mensuellement.\n\n"
    "Résiliation\nChaque Partie peut résilier avec un préavis de 30 jours.\n\n"
    "Pénalités\nDes pénalités peuvent s'appliquer en cas de retard.\n"
)

def write_pdf(path: str, text: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    c = canvas.Canvas(path, pagesize=A4)
    width, height = A4
    margin = 50
    y = height - margin
    for line in text.split('\n'):
        if y < margin:
            c.showPage()
            y = height - margin
        c.drawString(margin, y, line[:120])
        y -= 14
    c.save()


def main():
    write_pdf(os.path.join(BASE, 'article1.pdf'), ARTICLE_TEXT)
    write_pdf(os.path.join(BASE, 'contrat1.pdf'), CONTRACT_TEXT)
    print('Generated: data/examples/article1.pdf, data/examples/contrat1.pdf')

if __name__ == '__main__':
    main()
