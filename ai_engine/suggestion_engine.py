"""
AI suggestion engine — thin wrapper around the trained predictor.

Public API
----------
get_ai_solution(issue_text: str) -> str
    Returns an AI-generated solution string, or a safe fallback on error.
"""

import logging

_FALLBACK = "Please contact IT support for further troubleshooting."
logger = logging.getLogger(__name__)


def get_ai_solution(issue_text: str) -> str:
    """
    Return an AI-recommended solution for the given issue text.

    predict_solution() returns (solution, confidence); we surface only the
    solution string here so callers don't need to change their interface.
    Gracefully falls back to a generic message on any error.
    """
    try:
        from ai_models.inference.predictor import predict_solution
        solution, _confidence = predict_solution(issue_text)
        return solution if solution else _FALLBACK
    except Exception as e:
        logger.error('ML Error: %s', str(e), exc_info=True)
        return _FALLBACK
