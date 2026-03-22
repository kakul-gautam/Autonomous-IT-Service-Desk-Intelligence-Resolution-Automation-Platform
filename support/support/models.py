from django.contrib.auth.models import User
from django.db import models


class SupportTicket(models.Model):
    STATUS_OPEN = 'Open'
    STATUS_IN_PROGRESS = 'In Progress'
    STATUS_RESOLVED = 'Resolved'

    STATUS_CHOICES = [
        (STATUS_OPEN, 'Open'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_RESOLVED, 'Resolved'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_tickets')
    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=100)
    labels = models.CharField(max_length=255, blank=True, default='')
    is_highlighted = models.BooleanField(default=False)
    upvotes = models.IntegerField(default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"#{self.id} {self.title} ({self.status})"

    @property
    def labels_list(self) -> list[str]:
        """Return normalized labels as a list from comma-separated storage."""
        if not self.labels:
            return []
        return [part.strip().lower() for part in self.labels.split(',') if part.strip()]

    def save(self, *args, **kwargs):
        """Normalize labels into a deduplicated comma-separated string."""
        if self.labels:
            cleaned: list[str] = []
            seen: set[str] = set()
            for raw in self.labels.split(','):
                token = raw.strip().lower()
                if token and token not in seen:
                    seen.add(token)
                    cleaned.append(token)
            self.labels = ', '.join(cleaned)
        super().save(*args, **kwargs)


class SupportComment(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self) -> str:
        return f"Comment by {self.user.username} on ticket #{self.ticket_id}"


class SupportTicketUpvote(models.Model):
    ticket = models.ForeignKey(SupportTicket, on_delete=models.CASCADE, related_name='upvote_records')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='support_ticket_upvotes')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['ticket', 'user'], name='unique_support_ticket_upvote'),
        ]
        ordering = ['-created_at']

    def __str__(self) -> str:
        return f"{self.user.username} upvoted support ticket #{self.ticket_id}"
