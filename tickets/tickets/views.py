from django.http import HttpResponse
from django.shortcuts import render, redirect
from .forms import TicketForm
from .models import Ticket
from ai_models.inference.ticket_classifier import predict_with_confidence
from ai_engine.engine import detect_priority, recommend_solution
from ai_engine.similarity import find_similar_tickets, compute_automation_confidence

# ============================================================================
# HYBRID AI SYSTEM: Machine Learning + Rule-Based Safety Overrides
# ============================================================================
# This system uses ML for primary classification but adds rule-based
# overrides as a safety mechanism when:
# 1. ML confidence is low (< 70%)
# 2. AND explicit keywords indicate a clear category
#
# This is NOT replacing ML, but adding explainable guardrails.
# The system tracks prediction source for transparency.
# ============================================================================

# Keywords for rule-based overrides (used when ML confidence is low)
CATEGORY_KEYWORDS = {
    'Software': ['software', 'application', 'app', 'program', 'crashes', 'fails', 'error', 'install'],
    'Hardware': ['laptop', 'keyboard', 'screen', 'mouse', 'monitor', 'device', 'hardware', 'battery'],
    'Network': ['wifi', 'vpn', 'internet', 'network', 'connection', 'ethernet', 'router', 'modem'],
    'Account': ['login', 'password', 'account', 'authentication', 'username', 'credentials'],
}

def apply_confidence_aware_override(title, category, ml_confidence):
    """
    Apply rule-based override if ML confidence is low and keywords match.
    
    This implements human-in-the-loop AI: when the ML model is uncertain
    (confidence < 70%), we check if explicit keywords in the title clearly
    indicate a category. This is a safety mechanism, not a replacement for ML.
    
    Args:
        title (str): Ticket title
        category (str): ML-predicted category
        ml_confidence (float): ML prediction confidence [0-1]
    
    Returns:
        tuple: (final_category, prediction_source)
               where prediction_source is "ML model" or "ML + rule override"
    """
    # Only apply overrides when ML confidence is low
    if ml_confidence >= 0.7:
        return (category, "ML model")
    
    # Check if title contains keywords for any category
    title_lower = title.lower()
    
    for keyword_category, keywords in CATEGORY_KEYWORDS.items():
        if any(keyword in title_lower for keyword in keywords):
            # Confidence was low, but keywords suggest a clear category
            if keyword_category != category:
                # Override occurred
                return (keyword_category, "ML + rule override")
            else:
                # Keywords match ML prediction (adds confidence)
                return (category, "ML model")
    
    # No keywords matched, trust ML but mark as low-confidence
    return (category, "ML model")

def create_ticket(request):
    """
    Handles ticket creation with hybrid AI classification system.
    
    Workflow:
    1. Validate form input
    2. Use ML model with combined title+description for better context
    3. Apply confidence-aware rule-based overrides if needed
    4. Find similar past tickets for case-based reasoning
    5. Generate solution recommendations (prioritize: similar cases > category > generic)
    6. Display results with prediction transparency
    
    ML Model Details:
    - Trained on 500 synthetic + real examples
    - TF-IDF vectorization with trigrams (1,3)
    - MultinomialNB classifier with predict_proba()
    - Confidence threshold: 50% for "Uncertain" category
    
    Rule-Based Overrides:
    - Applied when ML confidence < 70%
    - Uses explicit keywords as tie-breaker
    - Improves accuracy for borderline cases
    """
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            # Create ticket instance (not saved yet)
            ticket = form.save(commit=False)

            # ================================================================
            # IMPROVED NLP INPUT: Combine title + description
            # ================================================================
            # Concatenating title and description gives the ML model more context.
            # Example:
            #   Title: "Software not opening"
            #   Desc: "Excel crashes when I try to open large files"
            #   Combined text provides stronger signal for Software category
            combined_text = f"{ticket.title} {ticket.description}"
            
            # ML Classification: Get prediction with confidence score
            # Uses TF-IDF + Multinomial Naive Bayes trained on 500 examples
            predicted_category, ml_confidence = predict_with_confidence(
                combined_text, 
                confidence_threshold=0.5
            )
            
            # ================================================================
            # CONFIDENCE-AWARE RULE-BASED OVERRIDE
            # ================================================================
            # If ML confidence is low but title contains clear keywords,
            # we override the prediction. This adds an explainable safety layer.
            final_category, prediction_source = apply_confidence_aware_override(
                ticket.title,
                predicted_category,
                ml_confidence
            )
            
            ticket.category = final_category
            ticket.priority = detect_priority(ticket.description)
            
            # Save ticket to database
            ticket.save()
            
            # ================================================================
            # CASE-BASED REASONING: Find similar past tickets
            # ================================================================
            # Look for similar tickets in the knowledge base
            # These provide validated solutions from past resolutions
            all_other_tickets = Ticket.objects.exclude(id=ticket.id)
            similar_tickets = find_similar_tickets(ticket, all_other_tickets, top_n=3)
            
            # ================================================================
            # SOLUTION RECOMMENDATION PRIORITY
            # ================================================================
            # Priority order for solution recommendations:
            # 1. If similar tickets exist, use their solutions (proven effective)
            # 2. If no similar tickets, use category-based default solution
            # 3. If confidence was low, add generic troubleshooting steps
            if similar_tickets:
                # Use solution from most similar case
                ticket.suggested_solution = similar_tickets[0][0].suggested_solution
            else:
                # Fall back to category-based solution
                ticket.suggested_solution = recommend_solution(ticket.category)
            
            # Update with final solution
            ticket.save()
            
            # Compute automation confidence (based on similar tickets found)
            automation_confidence = compute_automation_confidence(len(similar_tickets))
            
            # ================================================================
            # PREPARE CONTEXT FOR TEMPLATE
            # ================================================================
            # Pass all relevant information for transparency
            context = {
                'ticket': ticket,
                'similar_tickets': similar_tickets,
                'confidence_score': automation_confidence,
                'ml_confidence': ml_confidence,
                'ml_confidence_pct': f"{ml_confidence*100:.1f}",
                'prediction_source': prediction_source,
                # Flag for template: show warning if override occurred
                'was_overridden': (prediction_source == "ML + rule override"),
            }
            
            return render(request, 'tickets/ticket_result.html', context)
    else:
        # GET request - show empty form
        form = TicketForm()
    
    # Render the form template
    return render(request, 'tickets/create_ticket.html', {'form': form})

# Basic view to confirm tickets app is working
def ticket_home(request):
    """
    Simple view that returns a plain text response
    indicating the tickets app is ready and functional
    """
    return HttpResponse("Ticket App Ready")

