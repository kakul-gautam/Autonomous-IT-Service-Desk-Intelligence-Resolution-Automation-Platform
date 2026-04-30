"""
Train reranker on the final large combined dataset.

Uses: train_final.csv, val_final.csv, test_final.csv
Outputs artifacts to: ai_models/reranker_artifacts_v2/

Evaluates Precision@1 and Precision@3 on test_final.csv.
"""
from pathlib import Path
import csv
import joblib
import numpy as np
from collections import Counter

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler
from sklearn.metrics.pairwise import cosine_similarity


DATA_DIR = Path(__file__).resolve().parents[2] / 'ai_models' / 'datasets'
OUT_DIR = Path(__file__).resolve().parents[2] / 'ai_models' / 'reranker_artifacts_v2'


def load_split(path: Path):
    rows = []
    if not path.exists():
        return rows
    with path.open('r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for r in reader:
            rows.append({'issue': (r.get('issue') or '').strip(), 'category': (r.get('category') or '').strip(), 'solution': (r.get('solution') or '').strip()})
    return rows


def build_vectorizers(train_texts):
    word_vectorizer = TfidfVectorizer(stop_words='english', ngram_range=(1,2), max_features=10000, sublinear_tf=True)
    char_vectorizer = TfidfVectorizer(analyzer='char_wb', ngram_range=(3,5), max_features=15000, sublinear_tf=True)
    word_matrix = word_vectorizer.fit_transform(train_texts)
    char_matrix = char_vectorizer.fit_transform(train_texts)
    return word_vectorizer, char_vectorizer, word_matrix, char_matrix


def prepare_candidate_features(query_vec_w, query_vec_c, cand_idx, word_matrix, char_matrix, query_cat, train_rows, solution_freq):
    word_cands = word_matrix[cand_idx]
    char_cands = char_matrix[cand_idx]
    w_scores = cosine_similarity(query_vec_w, word_cands).flatten()
    c_scores = cosine_similarity(query_vec_c, char_cands).flatten()
    features = []
    sols = []
    for i, idx in enumerate(cand_idx):
        sol = train_rows[idx]['solution']
        cat = train_rows[idx].get('category','')
        freq = solution_freq.get(sol, 1)
        feat = [w_scores[i], c_scores[i], 1.0 if cat == query_cat else 0.0, float(freq)]
        features.append(feat)
        sols.append(sol)
    return np.array(features, dtype=float), sols


def create_training_pairs(train_rows, word_vect, char_vect, word_matrix, char_matrix, top_k=10):
    solution_freq = Counter([r['solution'] for r in train_rows])
    X = []
    y = []
    for q in train_rows:
        query_text = q['issue']
        query_cat = q.get('category','')
        q_w = word_vect.transform([query_text])
        q_c = char_vect.transform([query_text])
        w_scores = cosine_similarity(q_w, word_matrix).flatten()
        c_scores = cosine_similarity(q_c, char_matrix).flatten()
        hybrid = 0.7 * w_scores + 0.3 * c_scores
        cand_idx = np.argpartition(hybrid, -top_k)[-top_k:]
        ordered = cand_idx[np.argsort(hybrid[cand_idx])[::-1]]
        feats, sols = prepare_candidate_features(q_w, q_c, ordered, word_matrix, char_matrix, query_cat, train_rows, solution_freq)
        for fi, sol in enumerate(sols):
            label = 1 if sol == q['solution'] else 0
            X.append(feats[fi])
            y.append(label)
    return np.array(X), np.array(y)


def rerank_and_eval(test_rows, train_rows, word_vect, char_vect, word_matrix, char_matrix, clf, scaler, top_k=10):
    solution_freq = Counter([r['solution'] for r in train_rows])
    p1_list = []
    p3_list = []
    for q in test_rows:
        q_w = word_vect.transform([q['issue']])
        q_c = char_vect.transform([q['issue']])
        w_scores = cosine_similarity(q_w, word_matrix).flatten()
        c_scores = cosine_similarity(q_c, char_matrix).flatten()
        hybrid = 0.7 * w_scores + 0.3 * c_scores
        cand_idx = np.argpartition(hybrid, -top_k)[-top_k:]
        ordered = cand_idx[np.argsort(hybrid[cand_idx])[::-1]]
        feats, sols = prepare_candidate_features(q_w, q_c, ordered, word_matrix, char_matrix, q.get('category',''), train_rows, solution_freq)
        if feats.shape[0] == 0:
            p1_list.append(0)
            p3_list.append(0)
            continue
        feats_scaled = scaler.transform(feats)
        probs = clf.predict_proba(feats_scaled)[:,1]
        ranked_idx = np.argsort(probs)[::-1]
        ranked_sols = [sols[i] for i in ranked_idx]
        gold = q['solution']
        p1 = 1.0 if gold == ranked_sols[0] else 0.0
        p3 = 1.0 if gold in ranked_sols[:3] else 0.0
        p1_list.append(p1)
        p3_list.append(p3)
    return float(np.mean(p1_list)), float(np.mean(p3_list))


def main():
    print('Loading final splits...')
    train_rows = load_split(DATA_DIR / 'train_final.csv')
    val_rows = load_split(DATA_DIR / 'val_final.csv')
    test_rows = load_split(DATA_DIR / 'test_final.csv')
    
    if not train_rows:
        print('No training data found. Run combine_datasets.py first.')
        return
    
    print(f'Train: {len(train_rows)}, Val: {len(val_rows)}, Test: {len(test_rows)}')
    
    train_texts = [r['issue'] for r in train_rows]
    print('Building vectorizers...')
    word_vect, char_vect, word_matrix, char_matrix = build_vectorizers(train_texts)
    
    print('Creating training pairs...')
    X, y = create_training_pairs(train_rows, word_vect, char_vect, word_matrix, char_matrix, top_k=10)
    print(f'Training pairs: {X.shape}, Positive: {int(y.sum())}')
    
    scaler = StandardScaler()
    Xs = scaler.fit_transform(X)
    
    print('Training logistic regression re-ranker...')
    clf = LogisticRegression(max_iter=1000, class_weight='balanced')
    clf.fit(Xs, y)
    
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    joblib.dump(word_vect, OUT_DIR / 'word_vectorizer.pkl')
    joblib.dump(char_vect, OUT_DIR / 'char_vectorizer.pkl')
    joblib.dump(word_matrix, OUT_DIR / 'word_tfidf_matrix.pkl')
    joblib.dump(char_matrix, OUT_DIR / 'char_tfidf_matrix.pkl')
    joblib.dump(clf, OUT_DIR / 'reranker_clf.pkl')
    joblib.dump(scaler, OUT_DIR / 'feature_scaler.pkl')
    joblib.dump(train_rows, OUT_DIR / 'train_rows.pkl')
    print(f'Artifacts saved to {OUT_DIR}')
    
    print('\nEvaluating on test set...')
    p1, p3 = rerank_and_eval(test_rows, train_rows, word_vect, char_vect, word_matrix, char_matrix, clf, scaler, top_k=10)
    print(f'Precision@1: {p1:.3f}')
    print(f'Precision@3: {p3:.3f}')
    print(f'Test rows: {len(test_rows)}')
    
    # Also eval on val
    print('\nEvaluating on val set...')
    p1_val, p3_val = rerank_and_eval(val_rows, train_rows, word_vect, char_vect, word_matrix, char_matrix, clf, scaler, top_k=10)
    print(f'Val Precision@1: {p1_val:.3f}')
    print(f'Val Precision@3: {p3_val:.3f}')


if __name__ == '__main__':
    main()
