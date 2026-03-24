from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
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
    """
    User dashboard - shows personal ticket analytics only.
    Admins are redirected to the admin analytics dashboard.
    """
    # Redirect admins to admin dashboard
    if _is_admin_user(request.user):
        return redirect('admin_dashboard')
    
    # Generate simulated metrics on each load
    generate_metrics()

    is_admin_user = False  # This is user dashboard, not admin
    tickets = Ticket.objects.filter(owner=request.user).order_by('-created_at')

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
        if not request.user.is_staff:
            return redirect('incidents_home')

        ticket = get_object_or_404(Ticket, id=ticket_id)
        status = request.POST.get('status')
        feedback = request.POST.get('feedback', '')
        
        if status in ['Resolved', 'Failed']:
            ticket.resolution_status = status
            ticket.resolution_feedback = feedback
            ticket.save()
    
    return redirect('incidents_home')


@login_required
@staff_member_required(login_url='dashboard_home')
def admin_dashboard(request):
    """
    Admin analytics dashboard — restricted to staff/superusers.
    Displays system-wide statistics, ticket analytics, and user metrics.
    """
    from django.contrib.auth.models import User
    
    # User statistics
    total_users = User.objects.count()
    admin_users = User.objects.filter(is_staff=True).count()
    
    # Ticket statistics (ALL tickets, system-wide)
    all_tickets = Ticket.objects.all()
    total_tickets = all_tickets.count()
    
    # Priority distribution
    high_priority = all_tickets.filter(priority__iexact='High').count()
    medium_priority = all_tickets.filter(priority__iexact='Medium').count()
    low_priority = all_tickets.filter(priority__iexact='Low').count()
    
    # Category distribution
    category_stats = {}
    for ticket in all_tickets:
        cat = ticket.category or 'Unknown'
        category_stats[cat] = category_stats.get(cat, 0) + 1
    
    category_labels = list(category_stats.keys())
    category_counts = list(category_stats.values())
    
    # Priority stats for chart
    priority_labels = ['High', 'Medium', 'Low']
    priority_counts = [high_priority, medium_priority, low_priority]
    
    # Resolution status distribution
    resolved_count = all_tickets.filter(resolution_status='Resolved').count()
    pending_count = all_tickets.filter(resolution_status='Pending').count()
    failed_count = all_tickets.filter(resolution_status='Failed').count()
    
    # Calculate success rate
    success_rate = 0
    if total_tickets > 0:
        success_rate = round((resolved_count / total_tickets) * 100, 1)
    
    # Recent tickets
    recent_tickets = all_tickets.order_by('-created_at')[:10]
    
    # Convert to JSON for chart.js
    context = {
        'total_users': total_users,
        'admin_users': admin_users,
        'total_tickets': total_tickets,
        'high_priority': high_priority,
        'medium_priority': medium_priority,
        'low_priority': low_priority,
        'resolved_count': resolved_count,
        'pending_count': pending_count,
        'failed_count': failed_count,
        'success_rate': success_rate,
        'recent_tickets': recent_tickets,
        
        # For charts
        'category_labels_json': json.dumps(category_labels),
        'category_counts_json': json.dumps(category_counts),
        'priority_labels_json': json.dumps(priority_labels),
        'priority_counts_json': json.dumps(priority_counts),
        'resolution_labels_json': json.dumps(['Resolved', 'Pending', 'Failed']),
        'resolution_counts_json': json.dumps([resolved_count, pending_count, failed_count]),
    }
    
    return render(request, 'dashboard/admin_dashboard.html', context)

