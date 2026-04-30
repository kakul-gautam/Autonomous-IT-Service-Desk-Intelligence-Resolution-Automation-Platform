"""Retrain reranker artifacts directly from tickets_diverse.csv.

Outputs artifacts compatible with ai_models.inference.reranker_predictor:
- word_vectorizer.pkl
- char_vectorizer.pkl
- word_tfidf_matrix.pkl
- char_tfidf_matrix.pkl
- reranker_clf.pkl
- feature_scaler.pkl
- train_rows.pkl
"""

from __future__ import annotations

import csv
import random
import sys
from collections import Counter
from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

BASE_DIR = Path(__file__).resolve().parents[2]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ai_models.utils.preprocess import preprocess
DATASET_PATH = BASE_DIR / 'ai_models' / 'datasets' / 'tickets_diverse.csv'
OUT_DIR = BASE_DIR / 'ai_models' / 'reranker_artifacts_v2'


def load_rows(path: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    with path.open('r', encoding='utf-8', newline='') as f:
        reader = csv.DictReader(f)
        for row in reader:
            issue = (row.get('issue') or '').strip()
            category = (row.get('category') or '').strip()
            solution = (row.get('solution') or '').strip()
            if issue and solution:
                rows.append({'issue': preprocess(issue), 'category': category, 'solution': solution})
    return rows


def split_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    random.seed(42)
    shuffled = rows[:]
    random.shuffle(shuffled)
    n = len(shuffled)
    train_end = int(n * 0.8)
    val_end = int(n * 0.9)
    return shuffled[:train_end], shuffled[train_end:val_end], shuffled[val_end:]


def build_vectorizers(train_rows: list[dict[str, str]]):
    train_texts = [r['issue'] for r in train_rows]
    word_vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1, 2), max_features=10000, sublinear_tf=True)
    char_vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5), max_features=15000, sublinear_tf=True)

    word_matrix = word_vectorizer.fit_transform(train_texts)
    char_matrix = char_vectorizer.fit_transform(train_texts)
    return word_vectorizer, char_vectorizer, word_matrix, char_matrix


def prepare_candidate_features(query_vec_w, query_vec_c, cand_idx, word_matrix, char_matrix, query_cat, train_rows, solution_freq):
    word_cands = word_matrix[cand_idx]
    char_cands = char_matrix[cand_idx]
    w_scores = cosine_similarity(query_vec_w, word_cands).flatten()
    c_scores = cosine_similarity(query_vec_c, char_cands).flatten()

    features = []
    solutions = []
    for i, idx in enumerate(cand_idx):
        solution = train_rows[idx]['solution']
        category = train_rows[idx].get('category', '')
        freq = solution_freq.get(solution, 1)
        features.append([w_scores[i], c_scores[i], 1.0 if category == query_cat else 0.0, float(freq)])
        solutions.append(solution)

    return np.array(features, dtype=float), solutions


def create_training_pairs(train_rows, word_vect, char_vect, word_matrix, char_matrix, top_k=10):
    solution_freq = Counter(r['solution'] for r in train_rows)
    X = []
    y = []

    for row in train_rows:
        q_w = word_vect.transform([row['issue']])
        q_c = char_vect.transform([row['issue']])

        w_scores = cosine_similarity(q_w, word_matrix).flatten()
        c_scores = cosine_similarity(q_c, char_matrix).flatten()
        hybrid = 0.7 * w_scores + 0.3 * c_scores

        cand_idx = np.argpartition(hybrid, -top_k)[-top_k:]
        ordered = cand_idx[np.argsort(hybrid[cand_idx])[::-1]]

        feats, sols = prepare_candidate_features(q_w, q_c, ordered, word_matrix, char_matrix, row.get('category', ''), train_rows, solution_freq)

        for i, sol in enumerate(sols):
            X.append(feats[i])
            y.append(1 if sol == row['solution'] else 0)

    return np.array(X), np.array(y)


def rerank_and_eval(eval_rows, train_rows, word_vect, char_vect, word_matrix, char_matrix, clf, scaler, top_k=10):
    if not eval_rows:
        return 0.0, 0.0

    solution_freq = Counter(r['solution'] for r in train_rows)
    p1 = []
    p3 = []

    for row in eval_rows:
        q_w = word_vect.transform([row['issue']])
        q_c = char_vect.transform([row['issue']])

        w_scores = cosine_similarity(q_w, word_matrix).flatten()
        c_scores = cosine_similarity(q_c, char_matrix).flatten()
        hybrid = 0.7 * w_scores + 0.3 * c_scores

        cand_idx = np.argpartition(hybrid, -top_k)[-top_k:]
        ordered = cand_idx[np.argsort(hybrid[cand_idx])[::-1]]
        feats, sols = prepare_candidate_features(q_w, q_c, ordered, word_matrix, char_matrix, row.get('category', ''), train_rows, solution_freq)

        if feats.size == 0:
            p1.append(0.0)
            p3.append(0.0)
            continue

        scores = clf.predict_proba(scaler.transform(feats))[:, 1]
        ranked_idx = np.argsort(scores)[::-1]
        ranked_solutions = [sols[i] for i in ranked_idx]
        gold = row['solution']

        p1.append(1.0 if ranked_solutions and ranked_solutions[0] == gold else 0.0)
        p3.append(1.0 if gold in ranked_solutions[:3] else 0.0)

    return float(np.mean(p1)), float(np.mean(p3))


def main() -> None:
    if not DATASET_PATH.exists():
        raise FileNotFoundError(f'Dataset not found: {DATASET_PATH}')

    rows = load_rows(DATASET_PATH)
    if len(rows) < 50:
        raise RuntimeError('Dataset is too small to train a reliable reranker.')

    train_rows, val_rows, test_rows = split_rows(rows)
    print(f'Rows loaded: {len(rows)} (train={len(train_rows)}, val={len(val_rows)}, test={len(test_rows)})')

    word_vect, char_vect, word_matrix, char_matrix = build_vectorizers(train_rows)
    X, y = create_training_pairs(train_rows, word_vect, char_vect, word_matrix, char_matrix, top_k=10)
    print(f'Training pairs: {X.shape}, positives: {int(y.sum())}')

    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)

    clf = LogisticRegression(max_iter=1000, class_weight='balanced', random_state=42)
    clf.fit(Xs, y)

    p1_val, p3_val = rerank_and_eval(val_rows, train_rows, word_vect, char_vect, word_matrix, char_matrix, clf, scaler, top_k=10)
    p1_test, p3_test = rerank_and_eval(test_rows, train_rows, word_vect, char_vect, word_matrix, char_matrix, clf, scaler, top_k=10)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(word_vect, OUT_DIR / 'word_vectorizer.pkl')
    joblib.dump(char_vect, OUT_DIR / 'char_vectorizer.pkl')
    joblib.dump(word_matrix, OUT_DIR / 'word_tfidf_matrix.pkl')
    joblib.dump(char_matrix, OUT_DIR / 'char_tfidf_matrix.pkl')
    joblib.dump(clf, OUT_DIR / 'reranker_clf.pkl')
    joblib.dump(scaler, OUT_DIR / 'feature_scaler.pkl')
    joblib.dump(train_rows, OUT_DIR / 'train_rows.pkl')

    print(f'Artifacts saved to: {OUT_DIR}')
    print(f'Val Precision@1={p1_val:.3f}, Precision@3={p3_val:.3f}')
    print(f'Test Precision@1={p1_test:.3f}, Precision@3={p3_test:.3f}')


if __name__ == '__main__':
    main()
