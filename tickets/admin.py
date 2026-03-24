from django.contrib import admin
from .models import Ticket

# Register Ticket model to make it accessible in Django admin panel
@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    # Display these fields in the admin list view
    list_display = ['title', 'category', 'priority', 'created_at']
    
    # Add filters in the right sidebar
    list_filter = ['priority', 'category', 'created_at']
    
    # Enable search functionality
    search_fields = ['title', 'description']
    
    # Make these fields read-only
    readonly_fields = ['created_at']
