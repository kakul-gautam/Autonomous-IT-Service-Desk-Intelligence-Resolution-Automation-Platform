from django.urls import path
from . import views

# URL patterns for the dashboard app
# These routes handle dashboard-related functionality
urlpatterns = [
    # Main dashboard page - displays charts and statistics
    path('', views.dashboard_view, name='dashboard_home'),
    
    # Incidents and resolution outcomes page
    path('incidents/', views.incidents_view, name='incidents_home'),
    
    # Update ticket resolution status (POST)
    path('ticket/<int:ticket_id>/resolve/', views.update_ticket_resolution, name='resolve_ticket'),
]
