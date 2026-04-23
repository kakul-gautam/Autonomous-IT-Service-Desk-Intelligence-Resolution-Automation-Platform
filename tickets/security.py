"""
Security checks for tickets app.

Handles input validation and user authorization.
"""

import html
import re
from django.core.exceptions import ValidationError

MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 5000
MAX_FEEDBACK_LENGTH = 1000


def validate_and_sanitize_text(text, max_length, field_name="text"):
    """Check if text is valid and safe. Prevents XSS and buffer overflow."""
    if not text:
        return ""
    
    if not isinstance(text, str):
        raise ValidationError(f"{field_name} must be text")
    
    # No null bytes
    if '\x00' in text:
        raise ValidationError(f"{field_name} has invalid characters")
    
    # Clean up whitespace
    sanitized = text.strip()
    sanitized = re.sub(r'\s+', ' ', sanitized)
    
    # Escape HTML to prevent XSS (must happen before length check in case it expands)
    sanitized = html.escape(sanitized)
    
    # Check length after escaping
    if len(sanitized) > max_length:
        raise ValidationError(f"{field_name} is too long (max {max_length} chars)")
    
    return sanitized


def validate_ticket_title(title):
    """Make sure ticket title is valid."""
    if not title or not title.strip():
        raise ValidationError("Title cannot be empty")
    
    sanitized = validate_and_sanitize_text(title, MAX_TITLE_LENGTH, "Title")
    
    if len(sanitized) < 5:
        raise ValidationError("Title too short (at least 5 characters)")
    
    if not any(c.isalnum() for c in sanitized):
        raise ValidationError("Title must have real words")
    
    return sanitized


def validate_ticket_description(description):
    """Check if description is long enough and valid."""
    if not description or not description.strip():
        raise ValidationError("Description cannot be empty")
    
    sanitized = validate_and_sanitize_text(
        description, 
        MAX_DESCRIPTION_LENGTH, 
        "Description"
    )
    
    if len(sanitized) < 10:
        raise ValidationError("Description too short")
    
    return sanitized


def validate_feedback_text(feedback):
    """Validate user feedback on AI suggestions."""
    if not feedback or not feedback.strip():
        return ""
    
    sanitized = validate_and_sanitize_text(
        feedback, 
        MAX_FEEDBACK_LENGTH, 
        "Feedback"
    )
    
    return sanitized


def is_safe_from_sql_injection(text):
    """
    Check if text appears safe from SQL injection attempts.
    
    Returns:
        bool: True if text appears safe (no SQL injection patterns detected)
    """
    # SQL injection patterns - compiled with IGNORECASE for robustness
    sql_patterns = [
        r"\b(UNION|SELECT|INSERT|UPDATE|DELETE|DROP)\b",
        r";.*?--",
        r"\bOR\s+1\s*=\s*1\b",
        r"\bAND\s+1\s*=\s*1\b",
    ]
    
    text_upper = text.upper()
    
    for pattern in sql_patterns:
        if re.search(pattern, text_upper, re.IGNORECASE):
            return False
    
    return True


def user_owns_ticket(user, ticket):
    """Check if user owns the ticket."""
    return ticket.owner == user and user.is_authenticated


def user_can_access_ticket(user, ticket):
    """Check if user is allowed to see this ticket."""
    if not user.is_authenticated:
        return False
    
    if user_owns_ticket(user, ticket):
        return True
    
    if user.is_staff or user.is_superuser:
        return True
    
    return False
