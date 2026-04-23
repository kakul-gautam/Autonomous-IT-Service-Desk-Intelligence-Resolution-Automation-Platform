from django.urls import path
from . import views

# URL patterns for the tickets app
# These routes handle ticket-related functionality
urlpatterns = [
    # Main tickets page - create new ticket form
    path('', views.create_ticket, name='create_ticket'),
    
    # Ticket detail - view full ticket with AI suggestion
    path('<int:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    
    # AI Suggestion Actions
    path('<int:ticket_id>/ai/helpful/', views.mark_ai_helpful, name='mark_ai_helpful'),
    path('<int:ticket_id>/ai/unhelpful/', views.mark_ai_unhelpful, name='mark_ai_unhelpful'),
    
    # Comments
    path('<int:ticket_id>/comment/', views.add_comment, name='add_comment'),
    path('comment/<int:comment_id>/delete/', views.delete_comment, name='delete_comment'),
    
    # Export feature
    path('export/csv/', views.export_my_tickets, name='export_tickets'),
]
