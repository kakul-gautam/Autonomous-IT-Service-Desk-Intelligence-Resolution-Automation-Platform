"""
Hybrid Predictor — word+char TF-IDF retrieval with confidence calibration.

Improvements:
- Hybrid similarity (word TF-IDF + char n-gram TF-IDF)
- Fast top-k retrieval using argpartition
- Weighted voting by similarity (not just raw counts)
- Category prediction from retrieved neighbors (for dashboard flow)

Artifacts are loaded from ai_models/ (parent of this inference/ directory).
Run ai_models/training/train_model.py first to generate them.
"""

import os
import sys
import joblib
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

# Allow `from ai_models.utils.preprocess import preprocess` when running standalone
_AI_MODELS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT  = os.path.dirname(_AI_MODELS_DIR)
for _p in (_PROJECT_ROOT, _AI_MODELS_DIR):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ai_models.utils.preprocess import preprocess

# ── Load artifacts once at import time ────────────────────────────────────────
_word_vectorizer = joblib.load(os.path.join(_AI_MODELS_DIR, 'word_vectorizer.pkl'))
_word_tfidf_matrix = joblib.load(os.path.join(_AI_MODELS_DIR, 'word_tfidf_matrix.pkl'))

_char_vectorizer = None
_char_tfidf_matrix = None
_char_vectorizer_path = os.path.join(_AI_MODELS_DIR, 'char_vectorizer.pkl')
_char_matrix_path = os.path.join(_AI_MODELS_DIR, 'char_tfidf_matrix.pkl')
if os.path.exists(_char_vectorizer_path) and os.path.exists(_char_matrix_path):
    _char_vectorizer = joblib.load(_char_vectorizer_path)
    _char_tfidf_matrix = joblib.load(_char_matrix_path)

_solutions = joblib.load(os.path.join(_AI_MODELS_DIR, 'solutions.pkl'))
_categories = None
_categories_path = os.path.join(_AI_MODELS_DIR, 'categories.pkl')
if os.path.exists(_categories_path):
    _categories = joblib.load(_categories_path)

_FALLBACK       = "Please contact IT support for further troubleshooting."
_THRESHOLD      = 0.28
_K_NEIGHBORS    = 7
_CONFIDENCE_MIN = 0.38
_WORD_WEIGHT    = 0.72
_CHAR_WEIGHT    = 0.28


def _normalize_category_label(label: str) -> str:
    """Normalize model category labels to project-standard casing."""
    val = str(label).strip().lower()
    mapping = {
        'software': 'Software',
        'hardware': 'Hardware',
        'network': 'Network',
        'account': 'Account',
        'uncertain': 'Uncertain',
    }
    return mapping.get(val, str(label).strip().title())


def _score_query(cleaned_text: str) -> np.ndarray:
    """Return hybrid similarity scores for a cleaned query."""
    word_vec = _word_vectorizer.transform([cleaned_text])
    word_scores = cosine_similarity(word_vec, _word_tfidf_matrix).flatten()

    if _char_vectorizer is None or _char_tfidf_matrix is None:
        return word_scores

    char_vec = _char_vectorizer.transform([cleaned_text])
    char_scores = cosine_similarity(char_vec, _char_tfidf_matrix).flatten()

    # Weighted hybrid score to improve robustness against typos/variants.
    return (_WORD_WEIGHT * word_scores) + (_CHAR_WEIGHT * char_scores)


def _top_k(scores: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
    """Return top-k indices and scores in descending score order."""
    if len(scores) == 0:
        return np.array([], dtype=int), np.array([], dtype=float)

    k = min(k, len(scores))
    idx = np.argpartition(scores, -k)[-k:]
    ordered = idx[np.argsort(scores[idx])[::-1]]
    return ordered, scores[ordered]


def _weighted_vote(labels: list[str], weights: np.ndarray) -> tuple[str, float]:
    """Return winner label and weighted consensus ratio in [0, 1]."""
    if not labels:
        return "", 0.0

    tally: dict[str, float] = {}
    for label, weight in zip(labels, weights):
        tally[str(label)] = tally.get(str(label), 0.0) + float(max(weight, 0.0))

    winner = max(tally.items(), key=lambda kv: kv[1])[0]
    total = sum(tally.values())
    if total <= 0:
        return winner, 0.0
    return winner, float(tally[winner] / total)


def predict_solution(issue_text: str) -> tuple[str, float]:
    """
    Return the best matching solution using K-NN algorithm with confidence.

    Parameters
    ----------
    issue_text : str
        Raw issue description as typed by the user.

    Returns
    -------
    tuple[str, float]
        (solution, confidence)
        ``solution``   — matched solution string, or fallback message.
        ``confidence`` — confidence score in [0, 1].
                         0.0 when the fallback is returned.

    Algorithm:
    1. Preprocess input text (lowercase, expand contractions, etc.)
    2. Vectorize using TF-IDF
    3. Calculate cosine similarity to all training samples
    4. Find K=5 nearest neighbors
    5. Check if K-NN consensus is strong enough
    6. Return majority solution OR fallback if confidence too low

    Examples
    --------
    >>> solution, score = predict_solution("computer won't start")
    >>> print(f"Solution: {solution}\\nConfidence: {score:.3f}")
    """
    # ── Input validation ──────────────────────────────────────────────────────
    if not issue_text or not str(issue_text).strip():
        return _FALLBACK, 0.0

    # ── Preprocessing ─────────────────────────────────────────────────────────
    cleaned = preprocess(issue_text)
    if not cleaned:
        return _FALLBACK, 0.0

    # ── Vectorization + hybrid scoring ───────────────────────────────────────
    try:
        scores = _score_query(cleaned)
    except Exception:
        return _FALLBACK, 0.0

    top_k_indices, top_k_scores = _top_k(scores, _K_NEIGHBORS)
    if len(top_k_scores) == 0:
        return _FALLBACK, 0.0

    max_score = float(top_k_scores[0])
    if max_score < _THRESHOLD:
        return _FALLBACK, 0.0

    top_k_solutions = [str(_solutions[i]) for i in top_k_indices]
    best_solution, consensus_ratio = _weighted_vote(top_k_solutions, top_k_scores)

    # Margin gives useful confidence signal against ambiguous candidates.
    second_score = float(top_k_scores[1]) if len(top_k_scores) > 1 else 0.0
    margin = max(0.0, max_score - second_score)
    mean_topk = float(np.mean(top_k_scores))

    confidence = (0.55 * max_score) + (0.25 * consensus_ratio) + (0.15 * mean_topk) + (0.05 * margin)
    confidence = float(np.clip(confidence, 0.0, 1.0))

    if confidence < _CONFIDENCE_MIN:
        return _FALLBACK, 0.0

    return best_solution, round(confidence, 3)


def predict_with_confidence(issue_text: str, confidence_threshold: float = 0.5) -> tuple[str, float]:
    """
    Predict ticket category with confidence for Django ticket flow.
    
    Args:
        issue_text: Issue description
        confidence_threshold: Threshold for uncertainty
    
    Returns:
        (predicted_category, confidence_score)
    """
    if not issue_text or not str(issue_text).strip():
        return ("Uncertain", 0.0)

    cleaned = preprocess(issue_text)
    if not cleaned:
        return ("Uncertain", 0.0)

    if _categories is None:
        # Safe fallback when older artifacts don't include categories.
        text = cleaned.lower()
        if any(k in text for k in ("wifi", "network", "internet", "vpn", "router", "ethernet")):
            return (_normalize_category_label("network"), 0.65)
        if any(k in text for k in ("login", "password", "account", "username", "credential")):
            return (_normalize_category_label("account"), 0.65)
        if any(k in text for k in ("laptop", "keyboard", "screen", "battery", "monitor", "device")):
            return (_normalize_category_label("hardware"), 0.65)
        if any(k in text for k in ("software", "application", "app", "crash", "install", "update", "error")):
            return (_normalize_category_label("software"), 0.65)
        return ("Uncertain", 0.0)

    try:
        scores = _score_query(cleaned)
    except Exception:
        return ("Uncertain", 0.0)

    top_k_indices, top_k_scores = _top_k(scores, _K_NEIGHBORS)
    if len(top_k_scores) == 0:
        return ("Uncertain", 0.0)

    top_categories = [str(_categories[i]) for i in top_k_indices]
    best_category, consensus_ratio = _weighted_vote(top_categories, top_k_scores)

    max_score = float(top_k_scores[0])
    mean_topk = float(np.mean(top_k_scores))
    confidence = float(np.clip((0.65 * max_score) + (0.35 * consensus_ratio * mean_topk), 0.0, 1.0))

    if confidence < confidence_threshold:
        return ("Uncertain", round(confidence, 3))
    return (_normalize_category_label(best_category), round(confidence, 3))


# ── Smoke-test ─────────────────────────────────────────────────────────────────
if __name__ == '__main__':
    test_cases = [
        "wifi not connecting",
        "computer won't start",
        "cannot login to account",
        "application keeps crashing",
    ]
    sep = "-" * 70
    for issue in test_cases:
        solution, confidence = predict_solution(issue)
        print(sep)
        print(f"Issue             : {issue}")
        print(f"Predicted Solution: {solution}")
        print(f"Confidence        : {confidence:.4f}")
    print(sep)
