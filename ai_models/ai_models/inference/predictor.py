"""
Predictor — loads the 30k-trained TF-IDF model and returns a solution
plus a confidence score for any IT issue text using cosine similarity.

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
_vectorizer   = joblib.load(os.path.join(_AI_MODELS_DIR, 'vectorizer.pkl'))
_tfidf_matrix = joblib.load(os.path.join(_AI_MODELS_DIR, 'tfidf_matrix.pkl'))
_solutions    = joblib.load(os.path.join(_AI_MODELS_DIR, 'solutions.pkl'))

_FALLBACK  = "Please contact IT support for further troubleshooting."
_THRESHOLD = 0.15


def predict_solution(issue_text: str) -> tuple[str, float]:
    """
    Return the best matching solution and its cosine-similarity confidence.

    Parameters
    ----------
    issue_text : str
        Raw issue description as typed by the user.

    Returns
    -------
    tuple[str, float]
        (solution, confidence)
        ``solution``   — matched solution string, or fallback message.
        ``confidence`` — cosine similarity score in [0, 1].
                         0.0 when the fallback is returned.

    Examples
    --------
    >>> solution, score = predict_solution("computer won't start")
    >>> print(f"Solution: {solution}\\nConfidence: {score:.2f}")
    """
    if not issue_text or not str(issue_text).strip():
        return _FALLBACK, 0.0

    cleaned = preprocess(issue_text)
    vec     = _vectorizer.transform([cleaned])
    scores  = cosine_similarity(vec, _tfidf_matrix).flatten()
    best_idx = int(np.argmax(scores))
    best_score = float(scores[best_idx])

    if best_score < _THRESHOLD:
        return _FALLBACK, 0.0

    return str(_solutions[best_idx]), round(best_score, 4)


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
