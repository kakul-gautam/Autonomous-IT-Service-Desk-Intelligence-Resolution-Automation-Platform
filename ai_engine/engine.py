# ============================================================================
# HYBRID AI ENGINE: Priority + fallback rule utilities
# ============================================================================
# Category prediction is handled by ai_models.inference.predictor.
# This module focuses on:
# - Priority detection (rule-based, transparent, fast)
# - Optional category-based fallback recommendation text
# ============================================================================


# Priority phrase/keyword weights tuned from historical tickets.
_HIGH_PHRASE_WEIGHTS = {
    "not working": 4,
    "cannot login": 4,
    "can't login": 4,
    "system down": 4,
    "production down": 5,
    "service down": 5,
    "website down": 5,
    "email down": 4,
    "locked out": 4,
    "password reset": 3,
    "urgent": 4,
    "critical": 4,
    "asap": 3,
    "immediately": 3,
}

_MEDIUM_KEYWORD_WEIGHTS = {
    "slow": 1,
    "intermittent": 1,
    "warning": 1,
    "disconnect": 1,
    "unstable": 1,
    "battery": 1,
    "blurry": 1,
    "interface": 1,
    "cursor": 1,
    "apps": 1,
    "application": 1,
}

_LOW_KEYWORD_WEIGHTS = {
    "how to": -2,
    "request": -2,
    "feature": -2,
    "enhancement": -2,
    "minor": -1,
    "cosmetic": -2,
    "question": -1,
    "guidance": -1,
    "clarification": -1,
}


def detect_priority(text: str, category: str | None = None) -> str:
    """
    Determine ticket priority level using impact/urgency keyword scoring.
    
    Args:
        text (str): Ticket title + description
        category (str | None): Predicted category (Software/Hardware/Network/Account)
    
    Returns:
        str: Priority level ("High", "Medium", or "Low")
    """
    text_lower = (text or "").lower()

    score = 0

    # 1) High-impact phrases first (strong signals).
    for phrase, weight in _HIGH_PHRASE_WEIGHTS.items():
        if phrase in text_lower:
            score += weight

    # 2) Medium and low indicators (weaker, additive adjustments).
    for keyword, weight in _MEDIUM_KEYWORD_WEIGHTS.items():
        if keyword in text_lower:
            score += weight

    for keyword, weight in _LOW_KEYWORD_WEIGHTS.items():
        if keyword in text_lower:
            score += weight

    # 3) Generic outage/auth impact catch-all.
    if any(k in text_lower for k in ("down", "outage", "failed", "failure", "breach")):
        score += 2
    if any(k in text_lower for k in ("password", "login", "account")) and any(
        k in text_lower for k in ("cannot", "can't", "failed", "reset", "locked")
    ):
        score += 2

    # Category-aware impact adjustment.
    category_lower = (category or "").lower().strip()
    if category_lower in ("network", "account") and any(
        term in text_lower for term in ("down", "cannot", "locked", "outage", "login", "website", "email")
    ):
        score += 2
    if category_lower == "software" and any(term in text_lower for term in ("crash", "freeze", "unable", "cannot")):
        score += 1

    if score >= 5:
        return "High"
    if score <= 0:
        return "Low"

    # Default priority for standard incidents.
    return "Medium"


# Recommend a solution based on the classified category
def recommend_solution(category):
    """
    Recommend a solution based on the predicted category.
    
    This function is step 3 in solution recommendation priority:
    1. Similar ticket solutions (if found) - proven effective
    2. Category-based default solution (this function) - reasonable fallback
    3. Generic troubleshooting (for Uncertain category) - safety net
    
    Called from tickets/views.py when no similar tickets are found in knowledge base.
    
    Args:
        category (str): Ticket category (Hardware, Software, Network, Account, Uncertain)
    
    Returns:
        str: Suggested solution steps
    """
    if not category:
        return "Please provide a detailed description for recommendation"
    
    category_lower = category.lower().strip()
    
    # Category-specific solutions (proven effective for these issue types)
    if category_lower == "network":
        return "1. Restart your router/modem. 2. Check network cables. 3. Verify WiFi connection settings."
    if category_lower == "hardware":
        return "1. Restart the device. 2. Check hardware connections. 3. Check if peripherals are powered on."
    if category_lower == "software":
        return "1. Restart the application. 2. Clear application cache. 3. Reinstall the software if issue persists."
    if category_lower == "account":
        return "1. Use password reset link. 2. Verify username spelling. 3. Check account is unlocked."
    if category_lower == "uncertain":
        # Low-confidence predictions: generic troubleshooting + escalation path
        return "The issue category couldn't be determined with confidence. General troubleshooting: 1. Restart your device. 2. Check all cables and connections. 3. Review recent changes/updates. 4. Contact IT support with more details."

    # Default fallback solution for unmapped categories
    return "Please contact IT support for assistance with this issue."

# Determine ticket category based on keywords (DEPRECATED - use ML classifier)
def classify_category(text):
    """
    DEPRECATED: This rule-based classifier is superseded by ML-based classification.
    See ai_models/inference/predictor.py::predict_with_confidence().
    
    Kept for reference and as fallback for edge cases where ML fails.
    """
    text_lower = (text or "").lower()

    if any(keyword in text_lower for keyword in ["wifi", "internet", "network"]):
        return "Network"
    if any(keyword in text_lower for keyword in ["laptop", "mouse", "keyboard", "hardware"]):
        return "Hardware"
    if any(keyword in text_lower for keyword in ["crash", "software", "install", "error"]):
        return "Software"
    if any(keyword in text_lower for keyword in ["login", "password", "account"]):
        return "Account"

    return "General"

