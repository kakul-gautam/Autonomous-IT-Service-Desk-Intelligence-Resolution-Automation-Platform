from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from tickets.models import Ticket
from monitoring.models import SystemMetric
from monitoring.simulator import generate_metrics
import logging
import json


logger = logging.getLogger(__name__)


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
    Supports filtering by status, priority, and category.
    """
    # Redirect admins to admin dashboard
    if _is_admin_user(request.user):
        return redirect('admin_dashboard')
    
    # Generate simulated metrics on each load
    generate_metrics()

    is_admin_user = False  # This is user dashboard, not admin
    tickets = Ticket.objects.filter(owner=request.user).order_by('-created_at')
    
    # Apply filters from GET parameters
    status_filter = request.GET.get('status', '')
    priority_filter = request.GET.get('priority', '')
    category_filter = request.GET.get('category', '')
    
    if status_filter:
        tickets = tickets.filter(resolution_status__iexact=status_filter)
    if priority_filter:
        tickets = tickets.filter(priority__iexact=priority_filter)
    if category_filter:
        tickets = tickets.filter(category__iexact=category_filter)

    total_tickets = tickets.count()
    high_priority_count = tickets.filter(priority__iexact='High').count()
    medium_priority_count = tickets.filter(priority__iexact='Medium').count()

    # ================================================================
    # AI SUGGESTION METRICS
    # ================================================================
    ai_resolved_count = tickets.filter(ai_solution_helpful=True).count()
    ai_unhelpful_count = tickets.filter(ai_solution_helpful=False).count()
    ai_pending_count = tickets.filter(ai_solution_helpful__isnull=True, suggested_solution__isnull=False).count()
    
    # Calculate AI effectiveness
    ai_tickets_with_feedback = ai_resolved_count + ai_unhelpful_count
    ai_effectiveness = (
        (ai_resolved_count / ai_tickets_with_feedback * 100) 
        if ai_tickets_with_feedback > 0 else 0
    )
    
    # Get recently resolved tickets via AI
    recently_resolved_by_ai = tickets.filter(
        ai_solution_helpful=True
    ).order_by('-ai_action_timestamp')[:5]

    # Category stats - use database aggregation instead of Python loops
    from django.db.models import Count
    category_stats = tickets.values('category').annotate(count=Count('id'))
    category_labels = [stat['category'] for stat in category_stats]
    category_counts = [stat['count'] for stat in category_stats]

    # Priority stats - normalized to avoid duplicate variations (Medium showing 3 times)
    high_priority_count = tickets.filter(priority__iexact='High').count()
    medium_priority_count = tickets.filter(priority__iexact='Medium').count()
    low_priority_count = tickets.filter(priority__iexact='Low').count()
    
    priority_labels = ['High', 'Medium', 'Low']
    priority_counts = [high_priority_count, medium_priority_count, low_priority_count]

    # Monitoring metrics
    metrics = SystemMetric.objects.order_by('-created_at')[:20]

    cpu_list = [m.cpu_usage for m in metrics][::-1]
    memory_list = [m.memory_usage for m in metrics][::-1]
    network_list = [m.network_usage for m in metrics][::-1]

    # Anomaly metrics (Isolation Forest results)
    anomaly_count = SystemMetric.objects.filter(is_anomaly=True).count()
    recent_anomalies = SystemMetric.objects.filter(is_anomaly=True).order_by('-created_at')[:5]

    # Get available categories and statuses for filter options
    all_user_tickets = Ticket.objects.filter(owner=request.user)
    categories = sorted(set(t.category for t in all_user_tickets if t.category))
    statuses = ['Pending', 'Resolved', 'Failed']
    priorities = ['High', 'Medium', 'Low']

    context = {
        'tickets': tickets,
        'is_admin_user': is_admin_user,
        'total_tickets': total_tickets,
        'high_priority_count': high_priority_count,
        'medium_priority_count': medium_priority_count,
        'anomaly_count': anomaly_count,
        'recent_anomalies': recent_anomalies,
        
        # AI metrics
        'ai_resolved_count': ai_resolved_count,
        'ai_unhelpful_count': ai_unhelpful_count,
        'ai_pending_count': ai_pending_count,
        'ai_effectiveness': f"{ai_effectiveness:.1f}",
        'recently_resolved_by_ai': recently_resolved_by_ai,

        # Filter options
        'status_filter': status_filter,
        'priority_filter': priority_filter,
        'category_filter': category_filter,
        'categories': categories,
        'statuses': statuses,
        'priorities': priorities,

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
@staff_member_required(login_url='dashboard_home')
@require_http_methods(["POST"])
def update_ticket_resolution(request, ticket_id):
    """
    POST endpoint to update ticket resolution status.
    Admin marks ticket as Resolved/Failed for outcome logging.
    """
    try:
        ticket = get_object_or_404(Ticket, id=ticket_id)
        status = request.POST.get('status')
        feedback = request.POST.get('feedback', '')

        if status in ['Resolved', 'Failed']:
            ticket.resolution_status = status
            ticket.resolution_feedback = feedback
            ticket.save(update_fields=['resolution_status', 'resolution_feedback'])
            logger.info('Ticket resolution updated: ticket_id=%s status=%s staff_id=%s', ticket_id, status, request.user.id)
        else:
            messages.error(request, 'Invalid resolution status provided.')
    except Exception as exc:
        logger.error('Failed to update ticket resolution: ticket_id=%s staff_id=%s error=%s', ticket_id, request.user.id, str(exc), exc_info=True)
        messages.error(request, 'Unable to update resolution right now.')

    return redirect('incidents_home')


@login_required
@staff_member_required(login_url='dashboard_home')
def admin_dashboard(request):
    """
    COMPREHENSIVE Admin Dashboard — restricted to staff/superusers.
    Displays system-wide statistics, ticket analytics, AI effectiveness, and user metrics.
    
    Includes:
    - System health score
    - Ticket creation trends (30 days)
    - Resolution rates with detailed metrics
    - AI effectiveness by category and priority
    - User performance metrics (top performers)
    - Problem areas identification (trending issues)
    - Category performance rankings
    - Priority distribution across system
    """
    from django.contrib.auth.models import User
    from tickets.analytics import (
        get_ticket_analytics, 
        get_ai_performance_by_category,
        get_trend_data,
        get_category_stats,
        get_trending_issues
    )
    
    try:
        # Get 30-day analytics data
        analytics = get_ticket_analytics(days=30)
        ai_by_category = get_ai_performance_by_category(days=30)
        trends = get_trend_data(days=30)

        # Get expert insights
        trending_issues = get_trending_issues()  # Categories where AI is struggling
        category_performance = get_category_stats()  # Ranked by AI effectiveness
    except Exception as exc:
        logger.error('Admin dashboard analytics load failed: staff_id=%s error=%s', request.user.id, str(exc), exc_info=True)
        messages.error(request, 'Analytics are temporarily unavailable. Showing basic data only.')
        analytics = {
            'category_stats': {},
            'priority_stats': {},
            'resolution_rate': 0,
            'ai_effectiveness': 0,
            'total_tickets': 0,
            'resolved_count': 0,
            'pending_count': 0,
            'failed_count': 0,
        }
        ai_by_category = {}
        trends = {}
        trending_issues = []
        category_performance = []
    
    # Get user metrics
    users = User.objects.all()
    user_metrics = []
    for user in users:
        if user.is_staff:
            continue  # Skip admins
        user_tickets = Ticket.objects.filter(owner=user)
        if user_tickets.exists():
            resolved = user_tickets.filter(resolution_status='Resolved').count()
            total = user_tickets.count()
            user_metrics.append({
                'username': user.username,
                'total_tickets': total,
                'resolved': resolved,
                'resolution_rate': round((resolved/total*100) if total > 0 else 0, 1)
            })
    user_metrics = sorted(user_metrics, key=lambda x: x['resolution_rate'], reverse=True)
    
    # Prepare chart data
    category_labels = list(analytics['category_stats'].keys())
    category_resolved = [analytics['category_stats'][cat]['resolved'] for cat in category_labels]
    category_coverage = [analytics['category_stats'][cat]['total'] for cat in category_labels]
    
    # Priority data
    priority_labels = list(analytics['priority_stats'].keys())
    priority_counts = list(analytics['priority_stats'].values())
    
    # Daily trend data
    trend_dates = list(trends.keys())
    trend_created = [trends[date]['created'] for date in trend_dates]
    trend_resolved = [trends[date]['resolved'] for date in trend_dates]
    trend_pending = [trends[date]['pending'] for date in trend_dates]
    
    # AI effectiveness by category
    ai_categories = list(ai_by_category.keys())
    ai_effectiveness_rates = [ai_by_category[cat]['effectiveness'] for cat in ai_categories]
    ai_coverage_rates = [ai_by_category[cat]['solution_coverage'] for cat in ai_categories]
    
    # Calculate system health score
    avg_resolution_rate = analytics['resolution_rate']
    avg_ai_effectiveness = analytics['ai_effectiveness']
    system_health = round((avg_resolution_rate + avg_ai_effectiveness) / 2, 1)
    
    # Recent tickets
    recent_tickets = Ticket.objects.all().order_by('-created_at')[:10]
    
    # User statistics
    total_users = User.objects.count()
    admin_users = User.objects.filter(is_staff=True).count()
    
    context = {
        # Analytics data
        'analytics': analytics,
        'ai_by_category': ai_by_category,
        'trends': trends,
        'trending_issues': trending_issues,
        'category_performance': category_performance,
        'user_metrics': user_metrics,
        'system_health': system_health,
        
        # Basic metrics
        'total_users': total_users,
        'admin_users': admin_users,
        'total_tickets': analytics['total_tickets'],
        'recent_tickets': recent_tickets,
        'success_rate': analytics['resolution_rate'],
        
        # JSON for charts
        'category_labels_json': json.dumps(category_labels),
        'category_resolved_json': json.dumps(category_resolved),
        'category_coverage_json': json.dumps(category_coverage),
        'priority_labels_json': json.dumps(priority_labels),
        'priority_counts_json': json.dumps(priority_counts),
        'trend_dates_json': json.dumps(trend_dates),
        'trend_created_json': json.dumps(trend_created),
        'trend_resolved_json': json.dumps(trend_resolved),
        'trend_pending_json': json.dumps(trend_pending),
        'ai_categories_json': json.dumps(ai_categories),
        'ai_effectiveness_json': json.dumps(ai_effectiveness_rates),
        'ai_coverage_json': json.dumps(ai_coverage_rates),
        'resolution_labels_json': json.dumps(['Resolved', 'Pending', 'Failed']),
        'resolution_counts_json': json.dumps([
            analytics['resolved_count'],
            analytics['pending_count'],
            analytics['failed_count']
        ]),
    }
    


    return render(request, 'dashboard/admin_dashboard.html', context)

