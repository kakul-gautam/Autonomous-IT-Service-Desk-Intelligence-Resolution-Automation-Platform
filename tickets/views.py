from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import logging
from .forms import TicketForm, TicketCommentForm
from .models import Ticket, TicketComment
from .security import (
    validate_feedback_text,
    user_can_access_ticket,
    user_owns_ticket
)
from ai_models.inference.predictor import predict_with_confidence
from ai_engine.engine import detect_priority
from ai_engine.suggestion_engine import get_ai_solution
from ai_engine.similarity import find_similar_tickets, compute_automation_confidence

logger = logging.getLogger(__name__)

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

@login_required
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
            try:
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
            
                ticket.owner = request.user
                ticket.category = final_category
                ticket.priority = detect_priority(combined_text, final_category)
            
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
                    # Use AI model for solution recommendation
                    ticket.suggested_solution = get_ai_solution(combined_text)
            
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

                logger.info(
                    'Ticket created: ticket_id=%s owner_id=%s category=%s ml_confidence=%.4f source=%s',
                    ticket.id,
                    request.user.id,
                    ticket.category,
                    ml_confidence,
                    prediction_source,
                )
                return render(request, 'tickets/ticket_result.html', context)
            except (ValidationError, IntegrityError, ValueError, KeyError) as e:
                logger.error('Error in ticket creation: %s', str(e), exc_info=True)
                return render(
                    request,
                    'tickets/create_ticket.html',
                    {
                        'form': form,
                        'error_message': 'An unexpected error occurred while creating the ticket. Please try again.',
                    }
                )
    else:
        # GET request - show empty form
        form = TicketForm()
    
    # Render the form template
    return render(request, 'tickets/create_ticket.html', {'form': form})

# ============================================================================
# AI SUGGESTION ACTIONS - User interaction with AI recommendations
# ============================================================================

@login_required
def ticket_detail(request, ticket_id):
    """
    Display ticket details with AI suggestion prominently featured.
    
    Shows:
    - Ticket information
    - AI-suggested solution
    - Action buttons: "Mark as Resolved" or "Still Need Help"
    - Feedback from other users (if any)
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id, owner=request.user)
    except Ticket.DoesNotExist:
        return redirect('dashboard_home')
    
    context = {
        'ticket': ticket,
        'ai_solution_pending': ticket.ai_solution_helpful is None,
        'ai_was_helpful': ticket.ai_solution_helpful,
    }
    
    return render(request, 'tickets/ticket_detail.html', context)


@login_required
@require_http_methods(["POST"])
def mark_ai_helpful(request, ticket_id):
    """
    Mark AI suggestion as helpful and resolve the ticket.
    
    Security:
    - Requires login
    - Requires POST method (CSRF protected)
    - Validates user ownership of ticket
    - Sanitizes feedback input
    
    Workflow:
    1. User clicks "Mark as Resolved"
    2. AI suggestion marked as helpful
    3. Ticket status updated to "Resolved"
    4. User can optionally add feedback
    5. Redirect to dashboard with success message
    """
    try:
        # Authorization: Check user owns this ticket
        ticket = Ticket.objects.get(id=ticket_id)
        
        if not user_can_access_ticket(request.user, ticket):
            logger.warning(
                f"Unauthorized access attempt: user_id={request.user.id} "
                f"ticket_id={ticket_id}"
            )
            return redirect('dashboard_home')
        
        # Get and validate feedback
        raw_feedback = request.POST.get('feedback', '').strip()
        
        try:
            feedback = validate_feedback_text(raw_feedback)
        except Exception as e:
            logger.error(
                f"Feedback validation error: ticket_id={ticket_id} error={str(e)}"
            )
            feedback = ""
        
        # Mark ticket as resolved
        ticket.mark_ai_solution_helpful(feedback_text=feedback)
        
        logger.info(
            'AI solution marked helpful: ticket_id=%s user_id=%s feedback_len=%d',
            ticket.id,
            request.user.id,
            len(feedback)
        )
        
        return render(
            request,
            'tickets/ai_action_success.html',
            {
                'ticket': ticket,
                'action': 'resolved',
                'message': 'Great! Your ticket has been marked as resolved using the AI suggestion.'
            }
        )
    except Ticket.DoesNotExist:
        logger.warning(f"Ticket not found: ticket_id={ticket_id}")
        return redirect('dashboard_home')
    except Exception as e:
        logger.error(
            f'Error marking AI helpful: ticket_id={ticket_id} error={str(e)}',
            exc_info=True
        )
        return render(
            request,
            'tickets/ai_action_error.html',
            {
                'ticket': ticket,  # Use explicitly defined ticket variable
                'message': 'An error occurred while processing your request. Please try again.'
            }
        )


@login_required
@require_http_methods(["POST"])
def mark_ai_unhelpful(request, ticket_id):
    """
    Mark AI suggestion as unhelpful and redirect to support.
    
    Security:
    - Requires login
    - Requires POST method (CSRF protected)
    - Validates user ownership of ticket
    - Sanitizes feedback input
    
    Workflow:
    1. User clicks "Still Need Help"
    2. AI suggestion marked as unhelpful
    3. Capture feedback for improvement
    4. Redirect to support system with prefilled context
    5. Support agent has access to ticket details and feedback
    """
    ticket = None  # Initialize before try block
    try:
        # Authorization: Check user owns this ticket
        ticket = Ticket.objects.get(id=ticket_id)
        
        if not user_can_access_ticket(request.user, ticket):
            logger.warning(
                f"Unauthorized access attempt: user_id={request.user.id} "
                f"ticket_id={ticket_id}"
            )
            return redirect('dashboard_home')
        
        # Get and validate feedback
        raw_feedback = request.POST.get('feedback', '').strip()
        
        try:
            feedback = validate_feedback_text(raw_feedback)
        except Exception as e:
            logger.error(
                f"Feedback validation error: ticket_id={ticket_id} error={str(e)}"
            )
            feedback = ""
        
        # Mark ticket as unhelpful
        ticket.mark_ai_solution_unhelpful(feedback_text=feedback)
        
        logger.info(
            'AI solution marked unhelpful: ticket_id=%s user_id=%s feedback_len=%d',
            ticket.id,
            request.user.id,
            len(feedback)
        )
        
        # Get or create support ticket with context
        from support.models import SupportTicket
        
        # Check if support ticket already exists for this ticket
        support_ticket = SupportTicket.objects.filter(
            user=request.user,
            category=ticket.category,
            title__icontains=ticket.id
        ).first()
        
        created = False
        if support_ticket is None:
            # Create new support ticket
            support_ticket = SupportTicket.objects.create(
                title=f'Support needed for: {ticket.title}',
                description=(
                    f'Original issue: {ticket.description}\n\n'
                    f'AI suggestion was: {ticket.suggested_solution}\n\n'
                    f'Why it didn\'t help: {feedback if feedback else "User indicated more support needed"}'
                ),
                user=request.user,
                category=ticket.category,
                status='Open'
            )
            created = True
        
        return render(
            request,
            'tickets/ai_action_routed.html',
            {
                'ticket': ticket,
                'support_ticket': support_ticket if created else None,
                'message': 'Your feedback has been recorded. A support agent will help you further.'
            }
        )
    except Ticket.DoesNotExist:
        logger.warning(f"Ticket not found: ticket_id={ticket_id}")
        return redirect('dashboard_home')
    except Exception as e:
        logger.error(
            f'Error marking AI unhelpful: ticket_id={ticket_id} error={str(e)}',
            exc_info=True
        )
        return render(
            request,
            'tickets/ai_action_error.html',
            {
                'ticket': ticket,
                'message': 'An error occurred while escalating your ticket. Please try again.'
            }
        )


# ============================================================================
# EXPORT FEATURE
# ============================================================================

@login_required
def export_my_tickets(request):
    """
    Export user's tickets to CSV format.
    
    Security:
    - Requires login
    - Only exports user's own tickets
    - Sets proper download headers
    """
    from .export import export_tickets_to_csv
    
    try:
        # Get only user's own tickets
        tickets = Ticket.objects.filter(owner=request.user).order_by('-created_at')
        
        if not tickets.exists():
            return render(
                request,
                'tickets/export_error.html',
                {'message': 'You have no tickets to export.'}
            )
        
        logger.info(
            'Exporting tickets: user_id=%s count=%d',
            request.user.id,
            tickets.count()
        )
        
        return export_tickets_to_csv(request.user, tickets)
    
    except Exception as e:
        logger.error(
            f'Error exporting tickets: user_id={request.user.id} error={str(e)}',
            exc_info=True
        )
        return render(
            request,
            'tickets/export_error.html',
            {'message': 'An error occurred while exporting your tickets.'}
        )


# ============================================================================
# TICKET COMMENTS
# ============================================================================

@login_required
@require_http_methods(["POST"])
def add_comment(request, ticket_id):
    """
    Add a comment to a ticket.
    
    Security:
    - Requires login
    - Requires POST method (CSRF protected)
    - Only allows commenting on own tickets
    """
    try:
        ticket = Ticket.objects.get(id=ticket_id, owner=request.user)
    except Ticket.DoesNotExist:
        return redirect('dashboard_home')
    
    form = TicketCommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.ticket = ticket
        comment.author = request.user
        comment.save()
        
        logger.info(
            'Comment added: ticket_id=%s user_id=%s',
            ticket.id,
            request.user.id
        )
    
    return redirect('ticket_detail', ticket_id=ticket.id)


@login_required
@require_http_methods(["POST"])
def delete_comment(request, comment_id):
    """
    Delete a comment from a ticket.
    
    Security:
    - Requires login
    - Requires POST method (CSRF protected)
    - Only allows deleting own comments
    """
    try:
        comment = TicketComment.objects.get(id=comment_id, author=request.user)
        ticket_id = comment.ticket.id
        comment.delete()
        
        logger.info(
            'Comment deleted: comment_id=%s user_id=%s',
            comment_id,
            request.user.id
        )
    except TicketComment.DoesNotExist:
        return redirect('dashboard_home')
    
    return redirect('ticket_detail', ticket_id=ticket_id)


# ============================================================================
# HELPER VIEW
# ============================================================================

@login_required
def ticket_home(request):
    """
    Simple view that returns a plain text response
    indicating the tickets app is ready and functional
    """
    return HttpResponse("Ticket App Ready")

