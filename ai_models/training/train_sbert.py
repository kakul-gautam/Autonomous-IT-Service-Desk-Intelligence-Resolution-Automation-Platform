"""
Train a SBERT-based retrieval prototype.

Requirements: `sentence-transformers` installed in the environment.

This script:
 - loads `ai_models/datasets/train.csv`/`test.csv`
 - computes SBERT embeddings for issues
 - fits a NearestNeighbors index (cosine)
 - evaluates Precision@1 and Precision@3 on test set
 - saves artifacts to `ai_models/sbert_artifacts/`
"""
from pathlib import Path
import joblib
import csv
import sys
import numpy as np

DATA_DIR = Path(__file__).resolve().parents[2] / 'ai_models' / 'datasets'
OUT_DIR = Path(__file__).resolve().parents[2] / 'ai_models' / 'sbert_artifacts'


def load_split(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append((r['issue'].strip(), r['solution'].strip()))
    return rows


def precision_at_k(retrieved_sols, gold_sol, k):
    if not retrieved_sols:
        return 0
    topk = retrieved_sols[:k]
    return 1.0 if gold_sol in topk else 0.0


def main():
    try:
        from sentence_transformers import SentenceTransformer
    except Exception as e:
        print('sentence-transformers is not installed. Run: pip install sentence-transformers')
        sys.exit(2)

    print('Loading train/val/test...')
    train = load_split(DATA_DIR / 'train.csv')
    test = load_split(DATA_DIR / 'test.csv')
    if not train:
        print('No training data found at', DATA_DIR / 'train.csv')
        sys.exit(1)

    model_name = 'all-MiniLM-L6-v2'
    print('Loading SBERT model:', model_name)
    model = SentenceTransformer(model_name)

    train_texts = [t for t,_ in train]
    train_sols = [s for _,s in train]

    print('Encoding train texts...')
    train_emb = model.encode(train_texts, convert_to_numpy=True, show_progress_bar=True)

    # NearestNeighbors using cosine distance via sklearn (brute-force)
    from sklearn.neighbors import NearestNeighbors
    nn = NearestNeighbors(n_neighbors=10, metric='cosine', algorithm='brute')
    nn.fit(train_emb)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(model, OUT_DIR / 'sbert_model.joblib')
    joblib.dump(nn, OUT_DIR / 'sbert_nn.joblib')
    joblib.dump(train_texts, OUT_DIR / 'train_texts.pkl')
    joblib.dump(train_sols, OUT_DIR / 'train_solutions.pkl')
    joblib.dump(train_emb, OUT_DIR / 'train_embeddings.pkl')
    print('Saved artifacts to', OUT_DIR)

    # Evaluate on test set if available
    if not test:
        print('No test set available; skipping evaluation.')
        return

    test_texts = [t for t,_ in test]
    test_sols = [s for _,s in test]
    print('Encoding test texts...')
    test_emb = model.encode(test_texts, convert_to_numpy=True)

    dists, idxs = nn.kneighbors(test_emb, n_neighbors=10, return_distance=True)

    precisions_at_1 = []
    precisions_at_3 = []
    for i, retrieved_idx in enumerate(idxs):
        retrieved_sols = [train_sols[j] for j in retrieved_idx]
        gold = test_sols[i]
        precisions_at_1.append(precision_at_k(retrieved_sols, gold, 1))
        precisions_at_3.append(precision_at_k(retrieved_sols, gold, 3))

    p1 = float(np.mean(precisions_at_1)) if precisions_at_1 else 0.0
    p3 = float(np.mean(precisions_at_3)) if precisions_at_3 else 0.0
    print(f'Precision@1: {p1:.3f}  Precision@3: {p3:.3f}  Test rows: {len(test)}')


if __name__ == '__main__':
    main()
