"""
Integration helpers for ML models in Django views.
"""
import re
import logging

logger = logging.getLogger(__name__)


def get_ai_suggestion_with_confidence(issue_text: str) -> tuple:
    """
    Get AI suggestion using the reranker model.
    
    Falls back gracefully if model not loaded.
    
    Returns:
        (suggestion_text, confidence_score)
    """
    try:
        from ai_models.inference.reranker_predictor import predict_solution_candidates

        candidates = predict_solution_candidates(issue_text, confidence_threshold=0.0, max_results=3)
        if not candidates:
            return ("Please contact IT support for assistance.", 0.0)

        suggestion_lines = []
        for index, (solution, confidence) in enumerate(candidates, start=1):
            cleaned_solution = re.sub(r'^\s*\d+\.\s*', '', solution)
            suggestion_lines.append(f"{index}. {cleaned_solution}")

        return ("\n\n".join(suggestion_lines), candidates[0][1])
    except ImportError as e:
        logger.warning(f"Reranker model not available: {e}")
        try:
            from ai_engine.suggestion_engine import get_ai_solution
            return (get_ai_solution(issue_text), 0.5)
        except Exception as e2:
            logger.error(f"Failed to get AI suggestion: {e2}")
            return ("Please contact IT support for assistance.", 0.0)
    except Exception as e:
        logger.error(f"Error in AI suggestion: {e}")
        try:
            from ai_engine.suggestion_engine import get_ai_solution
            return (get_ai_solution(issue_text), 0.3)
        except:
            return ("Please contact IT support for assistance.", 0.0)
