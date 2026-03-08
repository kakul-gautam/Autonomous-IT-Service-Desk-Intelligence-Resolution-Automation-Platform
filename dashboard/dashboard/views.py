from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from tickets.models import Ticket
from monitoring.models import SystemMetric
from monitoring.simulator import generate_metrics
import json


def _is_admin_user(user):
    if user.is_superuser or user.is_staff:
        return True
    profile = getattr(user, 'profile', None)
    return bool(profile and profile.role == 'ADMIN')


def _ticket_queryset_for_user(user):
    if _is_admin_user(user):
        return Ticket.objects.all().order_by('-created_at')
    return Ticket.objects.filter(owner=user).order_by('-created_at')


@login_required
def dashboard_view(request):

    # Generate simulated metrics on each load
    generate_metrics()

    is_admin_user = _is_admin_user(request.user)
    tickets = _ticket_queryset_for_user(request.user)

    total_tickets = tickets.count()
    high_priority_count = tickets.filter(priority__iexact='High').count()
    medium_priority_count = tickets.filter(priority__iexact='Medium').count()

    # Category stats
    category_data = {}
    for t in tickets:
        category_data[t.category] = category_data.get(t.category, 0) + 1

    category_labels = list(category_data.keys())
    category_counts = list(category_data.values())

    # Priority stats
    priority_data = {}
    for t in tickets:
        priority_data[t.priority] = priority_data.get(t.priority, 0) + 1

    priority_labels = list(priority_data.keys())
    priority_counts = list(priority_data.values())

    # Monitoring metrics
    metrics = SystemMetric.objects.order_by('-created_at')[:20]

    cpu_list = [m.cpu_usage for m in metrics][::-1]
    memory_list = [m.memory_usage for m in metrics][::-1]
    network_list = [m.network_usage for m in metrics][::-1]

    # Anomaly metrics (Isolation Forest results)
    anomaly_count = SystemMetric.objects.filter(is_anomaly=True).count()
    recent_anomalies = SystemMetric.objects.filter(is_anomaly=True).order_by('-created_at')[:5]

    context = {
        'tickets': tickets,
        'is_admin_user': is_admin_user,
        'total_tickets': total_tickets,
        'high_priority_count': high_priority_count,
        'medium_priority_count': medium_priority_count,
        'anomaly_count': anomaly_count,
        'recent_anomalies': recent_anomalies,

        # Convert everything to JSON for JS
        'category_labels_json': json.dumps(category_labels),
        'category_counts_json': json.dumps(category_counts),
        'priority_labels_json': json.dumps(priority_labels),
        'priority_counts_json': json.dumps(priority_counts),

        'cpu_list_json': json.dumps(cpu_list),
        'memory_list_json': json.dumps(memory_list),
        'network_list_json': json.dumps(network_list),
    }

    return render(request, 'dashboard/dashboard.html', context)


@login_required
def incidents_view(request):
    """
    Resolution outcome logging dashboard.
    Shows ticket resolution statistics and allows admins to mark outcomes.
    Implements feedback learning: outcomes inform future recommendations.
    """
    
    # Resolution outcome statistics
    is_admin_user = _is_admin_user(request.user)
    visible_tickets = _ticket_queryset_for_user(request.user)

    total_tickets = visible_tickets.count()
    resolved_count = visible_tickets.filter(resolution_status='Resolved').count()
    failed_count = visible_tickets.filter(resolution_status='Failed').count()
    pending_count = visible_tickets.filter(resolution_status='Pending').count()
    
    # Calculate success rate
    success_rate = 0
    if total_tickets > 0:
        success_rate = int((resolved_count / total_tickets) * 100)
    
    # Get all tickets
    tickets = visible_tickets
    
    context = {
        'is_admin_user': is_admin_user,
        'total_tickets': total_tickets,
        'resolved_count': resolved_count,
        'failed_count': failed_count,
        'pending_count': pending_count,
        'success_rate': success_rate,
        'tickets': tickets,
    }
    
    return render(request, 'dashboard/incidents.html', context)


@login_required
def update_ticket_resolution(request, ticket_id):
    """
    POST endpoint to update ticket resolution status.
    Admin marks ticket as Resolved/Failed for outcome logging.
    """
    if request.method == 'POST':
        queryset = _ticket_queryset_for_user(request.user)
        ticket = get_object_or_404(queryset, id=ticket_id)
        status = request.POST.get('status')
        feedback = request.POST.get('feedback', '')
        
        if status in ['Resolved', 'Failed']:
            ticket.resolution_status = status
            ticket.resolution_feedback = feedback
            ticket.save()
    
    return redirect('incidents_home')

