from django.urls import path
from . import views

# URL patterns for the tickets app
# These routes handle ticket-related functionality
urlpatterns = [
    # Main tickets page - create new ticket form
    path('', views.create_ticket, name='create_ticket'),
]
