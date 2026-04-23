"""
Analytics module for ticket and AI performance metrics.

Generates real statistics about:
- Ticket resolution rates
- AI effectiveness
- Ticket trends over time
- Category performance
"""

from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
from tickets.models import Ticket


def get_ai_stats():
    """Get basic stats about AI suggestions."""
    all_tickets = Ticket.objects.filter(suggested_solution__isnull=False)
    
    resolved = all_tickets.filter(ai_solution_helpful=True).count()
    escalated = all_tickets.filter(ai_solution_helpful=False).count()
    pending = all_tickets.filter(ai_solution_helpful__isnull=True).count()
    
    total = resolved + escalated
    if total > 0:
        effectiveness = (resolved / total) * 100
    else:
        effectiveness = 0
    
    return {
        'resolved': resolved,
        'escalated': escalated,
        'pending': pending,
        'effectiveness': round(effectiveness, 1),
    }


def get_category_stats():
    """Show how well AI works for each category."""
    # Use database aggregation instead of Python loops to avoid N+1 queries
    from django.db.models import Count, Q
    
    category_stats = Ticket.objects.filter(
        suggested_solution__isnull=False
    ).values('category').annotate(
        total=Count('id'),
        resolved=Count('id', filter=Q(ai_solution_helpful=True)),
        escalated=Count('id', filter=Q(ai_solution_helpful=False))
    ).order_by('-total')
    
    results = []
    for stat in category_stats:
        total_feedback = stat['resolved'] + stat['escalated']
        if total_feedback > 0:
            effectiveness = (stat['resolved'] / total_feedback) * 100
        else:
            effectiveness = 0
        
        results.append({
            'category': stat['category'],
            'total': stat['total'],
            'resolved': stat['resolved'],
            'escalated': stat['escalated'],
            'effectiveness': round(effectiveness, 1),
        })
    
    return sorted(results, key=lambda x: x['effectiveness'], reverse=True)


def get_trending_issues():
    """Get categories where AI is failing the most."""
    unhelpful = Ticket.objects.filter(
        ai_solution_helpful=False
    ).values('category').annotate(
        count=Count('id')
    ).order_by('-count')[:3]
    
    return list(unhelpful)


def get_ticket_analytics(days=30):
    """
    Get comprehensive ticket analytics for the last N days.
    
    Args:
        days: Number of days to analyze (default 30)
    
    Returns:
        dict: Analytics data with real calculations
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    # Filter tickets from the period
    tickets = Ticket.objects.filter(created_at__gte=cutoff_date)
    
    total_tickets = tickets.count()
    
    # Resolution stats
    resolved = tickets.filter(resolution_status='Resolved').count()
    pending = tickets.filter(resolution_status='Pending').count()
    failed = tickets.filter(resolution_status='Failed').count()
    
    resolution_rate = (resolved / total_tickets * 100) if total_tickets > 0 else 0
    
    # AI effectiveness stats
    ai_helpful = tickets.filter(ai_solution_helpful=True).count()
    ai_unhelpful = tickets.filter(ai_solution_helpful=False).count()
    ai_pending = tickets.filter(ai_solution_helpful__isnull=True, suggested_solution__isnull=False).count()
    
    ai_rate = 0
    if (ai_helpful + ai_unhelpful) > 0:
        ai_rate = (ai_helpful / (ai_helpful + ai_unhelpful) * 100)
    
    # Get by category
    category_stats = {}
    for ticket in tickets:
        cat = ticket.category or "Other"
        if cat not in category_stats:
            category_stats[cat] = {'total': 0, 'resolved': 0, 'ai_helpful': 0}
        
        category_stats[cat]['total'] += 1
        if ticket.resolution_status == 'Resolved':
            category_stats[cat]['resolved'] += 1
        if ticket.ai_solution_helpful:
            category_stats[cat]['ai_helpful'] += 1
    
    # Priority distribution
    priority_stats = {}
    for ticket in tickets:
        priority = ticket.priority or "Unknown"
        priority_stats[priority] = priority_stats.get(priority, 0) + 1
    
    # Tickets created per day (for trending)
    daily_tickets = {}
    for i in range(days):
        date = (timezone.now() - timedelta(days=i)).date()
        count = tickets.filter(created_at__date=date).count()
        daily_tickets[str(date)] = count
    
    # Reverse for chronological order
    daily_tickets = dict(sorted(daily_tickets.items()))
    
    return {
        'total_tickets': total_tickets,
        'resolved_count': resolved,
        'pending_count': pending,
        'failed_count': failed,
        'resolution_rate': round(resolution_rate, 1),
        'ai_helpful_count': ai_helpful,
        'ai_unhelpful_count': ai_unhelpful,
        'ai_pending_count': ai_pending,
        'ai_effectiveness': round(ai_rate, 1),
        'category_stats': category_stats,
        'priority_stats': priority_stats,
        'daily_tickets': daily_tickets,
    }


def get_user_analytics(user, days=30):
    """
    Get analytics for a specific user's tickets.
    
    Args:
        user: User object
        days: Number of days to analyze
    
    Returns:
        dict: User-specific analytics
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    
    tickets = Ticket.objects.filter(owner=user, created_at__gte=cutoff_date)
    total = tickets.count()
    
    resolved = tickets.filter(resolution_status='Resolved').count()
    pending = tickets.filter(resolution_status='Pending').count()
    
    resolution_rate = (resolved / total * 100) if total > 0 else 0
    
    # AI helpfulness
    ai_helpful = tickets.filter(ai_solution_helpful=True).count()
    ai_unhelpful = tickets.filter(ai_solution_helpful=False).count()
    
    ai_rate = 0
    if (ai_helpful + ai_unhelpful) > 0:
        ai_rate = (ai_helpful / (ai_helpful + ai_unhelpful) * 100)
    
    return {
        'user': user.username,
        'total_tickets': total,
        'resolved_count': resolved,
        'pending_count': pending,
        'resolution_rate': round(resolution_rate, 1),
        'ai_helpful': ai_helpful,
        'ai_unhelpful': ai_unhelpful,
        'ai_effectiveness': round(ai_rate, 1),
    }


def get_ai_performance_by_category(days=30):
    """
    Analyze AI effectiveness for each category.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        dict: Performance by category with effectiveness %
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    tickets = Ticket.objects.filter(created_at__gte=cutoff_date)
    
    performance = {}
    
    for ticket in tickets:
        cat = ticket.category or "Other"
        if cat not in performance:
            performance[cat] = {
                'total': 0,
                'with_solution': 0,
                'helpful': 0,
                'unhelpful': 0,
                'pending': 0,
            }
        
        performance[cat]['total'] += 1
        
        if ticket.suggested_solution:
            performance[cat]['with_solution'] += 1
            
            if ticket.ai_solution_helpful is True:
                performance[cat]['helpful'] += 1
            elif ticket.ai_solution_helpful is False:
                performance[cat]['unhelpful'] += 1
            else:
                performance[cat]['pending'] += 1
    
    # Calculate effectiveness percentages
    for cat in performance:
        total = performance[cat]['total']
        # Always set solution_coverage (0 if no tickets)
        if total > 0:
            performance[cat]['solution_coverage'] = round(
                performance[cat]['with_solution'] / total * 100, 1
            )
        else:
            performance[cat]['solution_coverage'] = 0
        
        with_feedback = performance[cat]['helpful'] + performance[cat]['unhelpful']
        if with_feedback > 0:
            performance[cat]['effectiveness'] = round(
                performance[cat]['helpful'] / with_feedback * 100, 1
            )
        else:
            performance[cat]['effectiveness'] = 0
    
    return performance


def get_trend_data(days=30):
    """
    Get trend data for charting over time.
    
    Args:
        days: Number of days to analyze
    
    Returns:
        dict: Daily trend data with counts
    """
    cutoff_date = timezone.now() - timedelta(days=days)
    tickets = Ticket.objects.filter(created_at__gte=cutoff_date)
    
    trend = {}
    for i in range(days):
        date = (timezone.now() - timedelta(days=i)).date()
        dt_tickets = tickets.filter(created_at__date=date)
        
        trend[str(date)] = {
            'created': dt_tickets.count(),
            'resolved': dt_tickets.filter(resolution_status='Resolved').count(),
            'pending': dt_tickets.filter(resolution_status='Pending').count(),
        }
    
    # Reverse to chronological order
    trend = dict(sorted(trend.items()))
    
    return trend
