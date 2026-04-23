from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.db import transaction, IntegrityError
from django.db.models import F, Q
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.http import HttpResponseForbidden
import logging

from .forms import SupportCommentForm, SupportTicketForm
from .models import SupportTicket, SupportTicketUpvote

logger = logging.getLogger(__name__)


@login_required
def support_list(request):
    tickets = SupportTicket.objects.select_related('user')
    if request.user.is_staff:
        tickets = tickets.all()
    else:
        tickets = tickets.filter(user=request.user)

    search = request.GET.get('search', '').strip()
    status = request.GET.get('status', '').strip()
    category = request.GET.get('category', '').strip()

    if search:
        tickets = tickets.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search)
        )

    valid_statuses = {choice[0] for choice in SupportTicket.STATUS_CHOICES}
    if status in valid_statuses:
        tickets = tickets.filter(status=status)
    else:
        status = ''

    if category:
        tickets = tickets.filter(category__iexact=category)

    category_options = (
        SupportTicket.objects.exclude(category='')
        .values_list('category', flat=True)
        .distinct()
        .order_by('category')
    )

    filtered_tickets = list(tickets.order_by('-is_highlighted', '-created_at'))
    voted_ticket_ids = set(
        SupportTicketUpvote.objects.filter(user=request.user, ticket__in=filtered_tickets)
        .values_list('ticket_id', flat=True)
    )

    context = {
        'tickets': filtered_tickets,
        'search': search,
        'selected_status': status,
        'selected_category': category,
        'status_choices': SupportTicket.STATUS_CHOICES,
        'category_options': category_options,
        'active_filter_count': int(bool(search)) + int(bool(status)) + int(bool(category)),
        'voted_ticket_ids': voted_ticket_ids,
        'return_to': request.get_full_path(),
    }
    return render(request, 'support/support_list.html', context)


@login_required
@require_http_methods(["POST"])
def upvote_ticket(request, ticket_id):
    """
    Security: @login_required ensures only authenticated users can upvote
    Security: @require_http_methods(['POST']) prevents GET requests and XSS attacks
    """
    visible_tickets = SupportTicket.objects.all() if request.user.is_staff else SupportTicket.objects.filter(user=request.user)
    ticket = get_object_or_404(visible_tickets, id=ticket_id)

    try:
        with transaction.atomic():
            upvote, created = SupportTicketUpvote.objects.get_or_create(ticket=ticket, user=request.user)
            if created:
                SupportTicket.objects.filter(id=ticket.id).update(upvotes=F('upvotes') + 1)
                messages.success(request, 'Upvote added.')
                logger.info('Support ticket upvoted: ticket_id=%s user_id=%s', ticket.id, request.user.id)
            else:
                messages.info(request, 'You already upvoted this issue.')
    except (IntegrityError, ValueError) as e:
        logger.error('Error in support upvote: %s', str(e), exc_info=True)
        messages.error(request, 'Unable to register your upvote right now.')

    next_url = request.POST.get('next', '').strip()
    if next_url.startswith('/support'):
        return redirect(next_url)
    return redirect('support_list')


@login_required
@require_http_methods(["GET", "POST"])
def support_create(request):
    """
    Security: @login_required ensures only authenticated users can create support tickets
    Security: @require_http_methods limits to safe GET and POST-only methods
    """
    prefill = request.GET.get('prefill', '').strip()

    if request.method == 'POST':
        form = SupportTicketForm(request.POST)
        if form.is_valid():
            try:
                ticket = form.save(commit=False)
                ticket.user = request.user
                ticket.save()
                logger.info('Support ticket created: ticket_id=%s user_id=%s', ticket.id, request.user.id)
                messages.success(request, 'Support issue created successfully.')
                return redirect('support_detail', ticket_id=ticket.id)
            except (IntegrityError, ValidationError, ValueError) as e:
                logger.error('Error in support ticket creation: %s', str(e), exc_info=True)
                messages.error(request, 'Unable to create support issue right now.')
    else:
        initial_data = {'description': prefill} if prefill else {}
        form = SupportTicketForm(initial=initial_data)

    return render(request, 'support/support_create.html', {'form': form})


@login_required
@require_http_methods(["GET", "POST"])
def support_detail(request, ticket_id):
    visible_tickets = SupportTicket.objects.select_related('user')
    if not request.user.is_staff:
        visible_tickets = visible_tickets.filter(user=request.user)
    ticket = get_object_or_404(visible_tickets, id=ticket_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        try:
            if action == 'add_comment':
                comment_form = SupportCommentForm(request.POST)
                if comment_form.is_valid():
                    comment = comment_form.save(commit=False)
                    comment.ticket = ticket
                    comment.user = request.user
                    comment.save()
                    logger.info('Support comment added: ticket_id=%s user_id=%s', ticket.id, request.user.id)
                    messages.success(request, 'Comment added.')
                    return redirect('support_detail', ticket_id=ticket.id)
            elif action == 'update_status':
                if not request.user.is_staff:
                    logger.warning('Unauthorized support status update attempt: ticket_id=%s user_id=%s', ticket.id, request.user.id)
                    return HttpResponseForbidden('You are not authorized to update issue status.')
                new_status = request.POST.get('status', ticket.status)
                allowed = {choice[0] for choice in SupportTicket.STATUS_CHOICES}
                if new_status in allowed:
                    ticket.status = new_status
                    ticket.save(update_fields=['status'])
                    logger.info('Support status updated: ticket_id=%s status=%s staff_id=%s', ticket.id, new_status, request.user.id)
                    messages.success(request, 'Issue status updated.')
                return redirect('support_detail', ticket_id=ticket.id)
            elif action == 'mark_resolved':
                if not request.user.is_staff:
                    logger.warning('Unauthorized mark_resolved attempt: ticket_id=%s user_id=%s', ticket.id, request.user.id)
                    return HttpResponseForbidden('You are not authorized to resolve issues.')
                ticket.status = SupportTicket.STATUS_RESOLVED
                ticket.save(update_fields=['status'])
                logger.info('Support marked resolved: ticket_id=%s staff_id=%s', ticket.id, request.user.id)
                messages.success(request, 'Issue marked as Resolved.')
                return redirect('support_detail', ticket_id=ticket.id)
            elif action == 'mark_in_progress':
                if not request.user.is_staff:
                    logger.warning('Unauthorized mark_in_progress attempt: ticket_id=%s user_id=%s', ticket.id, request.user.id)
                    return HttpResponseForbidden('You are not authorized to update issue progress.')
                ticket.status = SupportTicket.STATUS_IN_PROGRESS
                ticket.save(update_fields=['status'])
                logger.info('Support marked in progress: ticket_id=%s staff_id=%s', ticket.id, request.user.id)
                messages.success(request, 'Issue marked as In Progress.')
                return redirect('support_detail', ticket_id=ticket.id)
            elif action == 'toggle_highlight':
                if not request.user.is_staff:
                    logger.warning('Unauthorized toggle_highlight attempt: ticket_id=%s user_id=%s', ticket.id, request.user.id)
                    return HttpResponseForbidden('You are not authorized to highlight issues.')
                ticket.is_highlighted = not ticket.is_highlighted
                ticket.save(update_fields=['is_highlighted'])
                logger.info('Support highlight toggled: ticket_id=%s highlighted=%s staff_id=%s', ticket.id, ticket.is_highlighted, request.user.id)
                if ticket.is_highlighted:
                    messages.success(request, 'Issue highlighted as important.')
                else:
                    messages.info(request, 'Issue highlight removed.')
                return redirect('support_detail', ticket_id=ticket.id)
            elif action == 'delete_issue':
                if not request.user.is_staff:
                    logger.warning('Unauthorized delete_issue attempt: ticket_id=%s user_id=%s', ticket.id, request.user.id)
                    return HttpResponseForbidden('You are not authorized to delete issues.')
                ticket_id_to_delete = ticket.id
                ticket.delete()
                logger.info('Support issue deleted: ticket_id=%s staff_id=%s', ticket_id_to_delete, request.user.id)
                messages.success(request, 'Issue deleted successfully.')
                return redirect('support_list')
            else:
                comment_form = SupportCommentForm()
        except (ValidationError, IntegrityError, ValueError) as e:
            logger.error('Error in support detail action: action=%s ticket_id=%s error=%s', action, ticket.id, str(e), exc_info=True)
            messages.error(request, 'Unable to process this support action right now.')
            return redirect('support_detail', ticket_id=ticket.id)
    else:
        comment_form = SupportCommentForm()

    comments = ticket.comments.select_related('user').all()
    context = {
        'ticket': ticket,
        'comments': comments,
        'comment_form': comment_form,
    }
    return render(request, 'support/support_detail.html', context)
