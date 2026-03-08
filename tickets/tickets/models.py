from django.db import models
from django.contrib.auth.models import User

# Ticket model to store IT service desk tickets
class Ticket(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="tickets", null=True, blank=True)

    # Brief title describing the issue
    title = models.CharField(max_length=200)
    
    # Detailed description of the ticket/issue
    description = models.TextField()
    
    # Category of the ticket (e.g., Hardware, Software, Network)
    category = models.CharField(max_length=100, blank=True)
    
    # Priority level (e.g., Low, Medium, High, Critical)
    priority = models.CharField(max_length=50, blank=True)
    
    # AI-generated suggested solution for the ticket
    suggested_solution = models.TextField(blank=True)
    
    # Timestamp when the ticket was created
    created_at = models.DateTimeField(auto_now_add=True)

    # Resolution status for ticket outcome logging (case-based reasoning)
    resolution_status = models.CharField(
        max_length=50,
        default='Pending',
        choices=[
            ('Pending', 'Pending'),
            ('Resolved', 'Resolved'),
            ('Failed', 'Failed'),
        ]
    )

    # Feedback on resolution (enables learning from outcomes)
    resolution_feedback = models.TextField(blank=True)
    
    def __str__(self):
        return f"{self.title} - {self.priority}"
    
    class Meta:
        ordering = ['-created_at']  # Most recent tickets first
