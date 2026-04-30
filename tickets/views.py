from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.core.exceptions import ValidationError
from django.db import IntegrityError
import logging
import re
from .forms import TicketForm, TicketCommentForm
from .models import Ticket, TicketComment
from .security import (
    validate_feedback_text,
    user_can_access_ticket,
    user_owns_ticket
)
from .ml_integration import get_ai_suggestion_with_confidence
from ai_models.inference.reranker_predictor import predict_category
from ai_engine.engine import detect_priority

logger = logging.getLogger(__name__)


def _normalize_category(raw_category: str) -> str:
    """Map model output to stable dashboard categories."""
    value = (raw_category or '').strip().lower()
    if not value:
        return 'Other'
    if 'hardware' in value or 'device' in value or 'keyboard' in value or 'battery' in value:
        return 'Hardware'
    if 'software' in value or 'application' in value or 'app' in value or 'install' in value:
        return 'Software'
    if 'network' in value or 'wifi' in value or 'vpn' in value or 'internet' in value or 'ethernet' in value:
        return 'Network'
    if 'account' in value or 'login' in value or 'permission' in value or 'auth' in value:
        return 'Account'
    if value == 'uncertain':
        return 'Other'
    return 'Other'


def _split_ranked_blocks(raw_text: str) -> list[str]:
    """Split a numbered suggestion string into per-suggestion blocks."""
    text = str(raw_text or '').strip()
    if not text:
        return []

    # Primary path: model output is joined with blank lines between suggestions.
    blank_line_blocks = [block.strip() for block in re.split(r'\n\s*\n', text) if block.strip()]
    if len(blank_line_blocks) > 1:
        return blank_line_blocks

    # Preferred format: each suggestion starts with "1. ", "2. ", etc.
    matches = list(re.finditer(r'(?m)^\s*\d+\.\s+', text))
    if len(matches) >= 2:
        blocks = []
        for idx, match in enumerate(matches):
            start = match.start()
            end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
            block = text[start:end].strip()
            if block:
                blocks.append(block)
        if blocks:
            return blocks

    # Fallback: split on blank lines if numbered markers are not present.
    return [block.strip() for block in re.split(r'\n\s*\n', text) if block.strip()]


def _extract_steps(lines: list[str]) -> list[str]:
    """Extract actionable steps from lines inside a suggestion block."""
    step_candidates: list[str] = []

    for line in lines[1:]:
        # Capture nested numbered steps and common bullet markers.
        nested = re.sub(r'^\s*(?:\d+[\.)]|[-*•])\s*', '', line).strip()
        if nested and nested != line:
            step_candidates.append(nested)

    if step_candidates:
        return step_candidates

    # If no explicit bullets are present, treat extra lines as steps.
    if len(lines) > 1:
        return [line.strip() for line in lines[1:] if line.strip()]

    return []


def _build_ranked_suggestions(raw_suggestions):
    """Convert newline-delimited ranked suggestions into template-friendly items."""
    ranked_suggestions = []

    if not raw_suggestions:
        return ranked_suggestions

    blocks = _split_ranked_blocks(raw_suggestions)
    for index, block in enumerate(blocks, start=1):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue

        summary = re.sub(r'^\d+\.\s*', '', lines[0]).strip()
        if summary.endswith(':'):
            summary = summary[:-1].strip()
        if not summary:
            summary = f'Suggestion {index}'

        steps = _extract_steps(lines)

        ranked_suggestions.append(
            {
                'rank': index,
                'summary': summary,
                'steps': steps,
                'text': '\n'.join(lines),
                'is_top': index == 1,
            }
        )

    return ranked_suggestions

# ============================================================================
# MODERN ML-POWERED SYSTEM: TF-IDF + Logistic Regression Re-ranker
# ============================================================================
# This system uses a trained ML model (TF-IDF vectorization + LR re-ranker)
# with diverse dataset (650 rows, 65 unique solutions) to provide
# high-quality solution recommendations for IT support tickets.
# ============================================================================

@login_required
def create_ticket(request):
    """
    Handles ticket creation with ML-powered solution recommendations.
    
    Workflow:
    1. Validate form input
    2. Use trained ML model (TF-IDF + LR) to generate solution recommendations
    3. Capture confidence score from model
    4. Display suggested solution with confidence level
    
    ML Model Details:
    - Trained on 650 diverse IT support examples
    - Hybrid TF-IDF: word-level (10K features) + char-level (15K features)
    - Logistic Regression re-ranker for final scoring
    - Confidence: model-calibrated prediction score (0-1)
    """
    if request.method == 'POST':
        form = TicketForm(request.POST)
        if form.is_valid():
            try:
                # Create ticket instance (not saved yet)
                ticket = form.save(commit=False)

                combined_text = f"{ticket.title} {ticket.description}"
                
                # Get AI solution recommendation with confidence score
                # Using trained ML model: TF-IDF + Logistic Regression
                ai_solution, confidence_score = get_ai_suggestion_with_confidence(combined_text)
                predicted_category, _category_confidence = predict_category(combined_text, confidence_threshold=0.0)
                
                # Save ticket with owner and AI solution
                ticket.owner = request.user
                ticket.category = _normalize_category(predicted_category)
                ticket.priority = detect_priority(combined_text, ticket.category)
                ticket.suggested_solution = ai_solution
                ticket.save()
                
                logger.info(
                    'Ticket created: ticket_id=%s owner_id=%s confidence=%.4f solution=%s',
                    ticket.id,
                    request.user.id,
                    confidence_score,
                    ai_solution[:50],
                )
                return redirect('ticket_detail', ticket_id=ticket.id)
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
        'ranked_suggestions': _build_ranked_suggestions(ticket.suggested_solution),
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

