from __future__ import annotations
import csv
import os
import sys
from typing import List

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from app.agents.ingestion import ingest_pdfs
from app.agents.type_detection import detect_document_type


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/evaluate_types.py data/examples/labels_types.csv [--llm]")
        sys.exit(1)

    labels_csv = sys.argv[1]
    use_llm = "--llm" in sys.argv

    rows = []
    with open(labels_csv, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append(r)

    file_paths: List[str] = [os.path.join(os.path.dirname(labels_csv), r["filename"]) for r in rows]
    docs = ingest_pdfs(file_paths)

    gold = [r["type"].strip() for r in rows]
    pred = []

    for doc in docs:
        t, c = detect_document_type(doc, use_llm=use_llm)
        pred.append(t)
        print(f"{doc['filename']}: pred={t} (conf={c:.2f})")

    correct = sum(1 for g, p in zip(gold, pred) if g == p)
    total = len(gold)
    acc = correct / total if total else 0.0
    print(f"Accuracy: {acc:.2%} ({correct}/{total})")


if __name__ == "__main__":
    main()
