"""
Export utilities for tickets.

Allows users to export their tickets to CSV format.
"""

import csv
from django.http import HttpResponse
from django.utils.text import slugify


def export_tickets_to_csv(user, tickets):
    """
    Export tickets to CSV format.
    
    Args:
        user: The user requesting the export
        tickets: QuerySet of tickets to export
    
    Returns:
        HttpResponse with CSV file for download
    """
    # Create CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="tickets_{slugify(user.username)}.csv"'
    
    # Create CSV writer
    writer = csv.writer(response)
    
    # Write header row
    writer.writerow([
        'ID', 'Title', 'Description', 'Category', 'Priority', 
        'Status', 'Created Date', 'AI Helpful'
    ])
    
    # Write ticket data rows
    for ticket in tickets:
        ai_result = ""
        if ticket.ai_solution_helpful is True:
            ai_result = "Helpful"
        elif ticket.ai_solution_helpful is False:
            ai_result = "Not Helpful"
        else:
            ai_result = "Pending"
        
        writer.writerow([
            ticket.id,
            ticket.title,
            (ticket.description or "")[:50],  # Handle None description
            ticket.category,
            ticket.priority,
            ticket.resolution_status,
            ticket.created_at.strftime('%Y-%m-%d %H:%M'),
            ai_result
        ])
    
    return response
