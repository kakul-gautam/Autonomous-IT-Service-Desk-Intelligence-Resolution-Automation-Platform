from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    priority = models.CharField(
        max_length=50,
        blank=True,
        choices=[
            ('High', 'High'),
            ('Medium', 'Medium'),
            ('Low', 'Low'),
        ],
        default='Medium'
    )
    
    # AI-generated suggested solution for the ticket
    suggested_solution = models.TextField(blank=True, null=True)
    
    # Timestamp when the ticket was created
    created_at = models.DateTimeField(auto_now_add=True)

    # ================================================================
    # AI SUGGESTION TRACKING & FEEDBACK
    # ================================================================
    # Track whether user found the AI suggestion helpful
    ai_solution_helpful = models.BooleanField(
        null=True,
        blank=True,
        default=None,
        help_text="True=helpful, False=not helpful, None=not yet reviewed"
    )
    
    # Track if ticket was resolved using AI suggestion
    resolved_by_ai = models.BooleanField(
        default=False,
        help_text="Whether the AI solution resolved the issue"
    )
    
    # Timestamp when user acted on AI suggestion
    ai_action_timestamp = models.DateTimeField(null=True, blank=True)
    
    # User feedback message (why AI suggestion helped or didn't help)
    ai_feedback_text = models.TextField(blank=True, help_text="User's feedback on the AI suggestion")

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
    
    def mark_ai_solution_helpful(self, feedback_text=''):
        """Mark that the user found the AI solution helpful"""
        self.ai_solution_helpful = True
        self.resolved_by_ai = True
        self.resolution_status = 'Resolved'
        self.ai_action_timestamp = timezone.now()
        self.ai_feedback_text = feedback_text
        self.save(update_fields=[
            'ai_solution_helpful', 
            'resolved_by_ai', 
            'resolution_status', 
            'ai_action_timestamp',
            'ai_feedback_text'
        ])
    
    def mark_ai_solution_unhelpful(self, feedback_text=''):
        """Mark that the user needs more help"""
        self.ai_solution_helpful = False
        self.ai_action_timestamp = timezone.now()
        self.ai_feedback_text = feedback_text
        self.save(update_fields=[
            'ai_solution_helpful',
            'ai_action_timestamp',
            'ai_feedback_text'
        ])
    
    def __str__(self):
        return f"{self.title} - {self.priority}"
    
    class Meta:
        ordering = ['-created_at']  # Most recent tickets first


class TicketComment(models.Model):
    """
    Comments on tickets for collaborative discussion.
    
    Allows team members to discuss and share solutions on tickets.
    """
    ticket = models.ForeignKey(
        Ticket,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    author = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='ticket_comments'
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['created_at']
    
    def __str__(self):
        return f"Comment by {self.author.username} on ticket #{self.ticket.id}"
