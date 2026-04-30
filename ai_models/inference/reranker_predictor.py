"""
Inference wrapper for Django integration.

Loads reranker artifacts and provides predict() function for Django views.
"""
import os
import sys
import joblib
import numpy as np
from pathlib import Path
from sklearn.metrics.pairwise import cosine_similarity
from collections import Counter

_HERE = Path(__file__).resolve().parents[2]
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from ai_models.utils.preprocess import preprocess

# Artifacts directory (reranker_artifacts_v2 is our best model)
ARTIFACTS_DIR = _HERE / 'ai_models' / 'reranker_artifacts_v2'

# Load artifacts once at import time
def _load_artifacts():
    artifacts = {}
    try:
        artifacts['word_vect'] = joblib.load(ARTIFACTS_DIR / 'word_vectorizer.pkl')
        artifacts['char_vect'] = joblib.load(ARTIFACTS_DIR / 'char_vectorizer.pkl')
        artifacts['word_matrix'] = joblib.load(ARTIFACTS_DIR / 'word_tfidf_matrix.pkl')
        artifacts['char_matrix'] = joblib.load(ARTIFACTS_DIR / 'char_tfidf_matrix.pkl')
        artifacts['clf'] = joblib.load(ARTIFACTS_DIR / 'reranker_clf.pkl')
        artifacts['scaler'] = joblib.load(ARTIFACTS_DIR / 'feature_scaler.pkl')
        artifacts['train_rows'] = joblib.load(ARTIFACTS_DIR / 'train_rows.pkl')
    except Exception as e:
        import logging
        logging.error(f"Failed to load reranker artifacts: {e}")
        raise
    return artifacts

try:
    _ARTIFACTS = _load_artifacts()
    _WORD_VECT = _ARTIFACTS['word_vect']
    _CHAR_VECT = _ARTIFACTS['char_vect']
    _WORD_MATRIX = _ARTIFACTS['word_matrix']
    _CHAR_MATRIX = _ARTIFACTS['char_matrix']
    _CLF = _ARTIFACTS['clf']
    _SCALER = _ARTIFACTS['scaler']
    _TRAIN_ROWS = _ARTIFACTS['train_rows']
    _MODEL_LOADED = True
except Exception as e:
    import logging
    logging.warning(f"Reranker not loaded (model may not be trained yet): {e}")
    _MODEL_LOADED = False


def predict_solution(issue_text: str, top_k: int = 10, confidence_threshold: float = 0.3) -> tuple:
    """
    Predict the best solution for an issue using the reranker.
    
    Args:
        issue_text: Raw issue description
        top_k: Number of candidates to retrieve (default 10)
        confidence_threshold: Minimum confidence to return a solution
    
    Returns:
        (solution_text, confidence_score)
        - solution_text: The recommended solution or fallback message
        - confidence_score: Float between 0 and 1
    """
    if not _MODEL_LOADED:
        return ("ML model not loaded. Contact IT support for assistance.", 0.0)
    
    if not issue_text or not str(issue_text).strip():
        return ("Please provide a description of your issue.", 0.0)
    
    # Preprocess
    cleaned = preprocess(issue_text)
    if not cleaned:
        return ("Could not process issue text. Please try again with more detail.", 0.0)
    
    try:
        ranked_candidates = _predict_ranked_candidates(
            cleaned,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
            max_results=1,
        )

        if not ranked_candidates:
            return ("No matching solutions found. Please contact IT support.", 0.0)

        best_solution, confidence = ranked_candidates[0]
        return (best_solution, confidence)
    
    except Exception as e:
        import logging
        logging.error(f"Prediction error: {e}")
        return ("An error occurred during prediction. Please try again.", 0.0)


def _predict_ranked_candidates(cleaned_text: str, top_k: int, confidence_threshold: float, max_results: int) -> list[tuple[str, float]]:
    """Return ranked solution candidates for a cleaned query."""
    q_w = _WORD_VECT.transform([cleaned_text])
    q_c = _CHAR_VECT.transform([cleaned_text])

    w_scores = cosine_similarity(q_w, _WORD_MATRIX).flatten()
    c_scores = cosine_similarity(q_c, _CHAR_MATRIX).flatten()
    hybrid = 0.7 * w_scores + 0.3 * c_scores

    cand_idx = np.argpartition(hybrid, -top_k)[-top_k:]
    ordered = cand_idx[np.argsort(hybrid[cand_idx])[::-1]]

    word_cands = _WORD_MATRIX[ordered]
    char_cands = _CHAR_MATRIX[ordered]
    w_cand_scores = cosine_similarity(q_w, word_cands).flatten()
    c_cand_scores = cosine_similarity(q_c, char_cands).flatten()

    solution_freq = Counter([r['solution'] for r in _TRAIN_ROWS])
    features = []
    solutions = []

    for i, idx in enumerate(ordered):
        sol = _TRAIN_ROWS[idx]['solution']
        cat = _TRAIN_ROWS[idx].get('category', '')
        freq = solution_freq.get(sol, 1)
        feat = [w_cand_scores[i], c_cand_scores[i], 1.0, float(freq)]
        features.append(feat)
        solutions.append(sol)

    if not features:
        return []

    X_scaled = _SCALER.transform(np.array(features, dtype=float))
    probs = _CLF.predict_proba(X_scaled)[:, 1]
    ranked_idx = np.argsort(probs)[::-1]

    ranked_candidates: list[tuple[str, float]] = []
    seen: set[str] = set()
    for idx in ranked_idx:
        solution = solutions[idx]
        confidence = float(probs[idx])
        if confidence < confidence_threshold:
            continue
        if solution in seen:
            continue
        ranked_candidates.append((solution, round(confidence, 3)))
        seen.add(solution)
        if len(ranked_candidates) >= max_results:
            break

    return ranked_candidates


def predict_solution_candidates(issue_text: str, top_k: int = 10, confidence_threshold: float = 0.3, max_results: int = 3) -> list[tuple[str, float]]:
    """Return multiple ranked solution candidates for an issue."""
    if not _MODEL_LOADED:
        return [("ML model not loaded. Contact IT support for assistance.", 0.0)]

    if not issue_text or not str(issue_text).strip():
        return [("Please provide a description of your issue.", 0.0)]

    cleaned = preprocess(issue_text)
    if not cleaned:
        return [("Could not process issue text. Please try again with more detail.", 0.0)]

    try:
        ranked_candidates = _predict_ranked_candidates(
            cleaned,
            top_k=top_k,
            confidence_threshold=confidence_threshold,
            max_results=max_results,
        )
        if not ranked_candidates:
            return [("Confidence too low. Please contact IT support for assistance.", 0.0)]
        return ranked_candidates
    except Exception as e:
        import logging
        logging.error(f"Candidate prediction error: {e}")
        return [("An error occurred during prediction. Please try again.", 0.0)]


def predict_category(issue_text: str, confidence_threshold: float = 0.4) -> tuple:
    """
    Predict the category for an issue.
    
    Args:
        issue_text: Raw issue description
        confidence_threshold: Minimum confidence threshold
    
    Returns:
        (category, confidence_score)
    """
    if not _MODEL_LOADED:
        return ("Uncertain", 0.0)
    
    if not issue_text or not str(issue_text).strip():
        return ("Uncertain", 0.0)
    
    cleaned = preprocess(issue_text)
    if not cleaned:
        return ("Uncertain", 0.0)
    
    try:
        q_w = _WORD_VECT.transform([cleaned])
        q_c = _CHAR_VECT.transform([cleaned])
        w_scores = cosine_similarity(q_w, _WORD_MATRIX).flatten()
        c_scores = cosine_similarity(q_c, _CHAR_MATRIX).flatten()
        hybrid = 0.7 * w_scores + 0.3 * c_scores
        
        top_k = 5
        cand_idx = np.argpartition(hybrid, -top_k)[-top_k:]
        
        categories = [_TRAIN_ROWS[i].get('category', 'Uncertain') for i in cand_idx]
        cat_counts = Counter(categories)
        best_cat, count = cat_counts.most_common(1)[0]
        confidence = float(count) / top_k
        
        if confidence < confidence_threshold:
            return ("Uncertain", round(confidence, 3))
        
        return (best_cat, round(confidence, 3))
    
    except Exception as e:
        import logging
        logging.error(f"Category prediction error: {e}")
        return ("Uncertain", 0.0)
