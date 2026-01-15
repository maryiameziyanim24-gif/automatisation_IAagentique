from __future__ import annotations
import os, sys
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from app.orchestrator import analyze_pdfs

files = [
    'data/examples/article1.pdf',
    'data/examples/contrat1.pdf',
]

if __name__ == '__main__':
    res = analyze_pdfs(files, use_llm=False, llm_model=None, force_type=None)
    for d in res:
        print(d['filename'], d['document_type'], d.get('report_path'))
