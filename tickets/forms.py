from django import forms
from django.core.exceptions import ValidationError
from .models import Ticket, TicketComment
from .security import (
    validate_ticket_title,
    validate_ticket_description,
    is_safe_from_sql_injection
)


class TicketForm(forms.ModelForm):
    """Form for creating tickets."""
    
    class Meta:
        model = Ticket
        fields = ['title', 'description']
        
        widgets = {
            'title': forms.TextInput(attrs={
                'placeholder': 'Brief title of the issue',
                'class': 'form-control',
                'maxlength': '200',
                'required': 'required'
            }),
            'description': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Describe your issue',
                'class': 'form-control',
                'maxlength': '5000',
                'required': 'required'
            }),
        }

    def clean_title(self):
        """Check that title is valid and safe."""
        title = self.cleaned_data.get('title', '').strip()
        
        try:
            cleaned_title = validate_ticket_title(title)
        except ValidationError:
            raise
        
        # Check for SQL injection
        if not is_safe_from_sql_injection(cleaned_title):
            raise ValidationError('Title contains dangerous characters.')
        
        return cleaned_title

    def clean_description(self):
        """Check that description is valid."""
        description = self.cleaned_data.get('description', '').strip()
        
        try:
            cleaned_desc = validate_ticket_description(description)
        except ValidationError:
            raise
        
        # Check for SQL injection
        if not is_safe_from_sql_injection(cleaned_desc):
            raise ValidationError('Description contains dangerous characters.')
        
        return cleaned_desc
    
    def clean(self):
        """Make sure description is different from title."""
        cleaned_data = super().clean()
        title = cleaned_data.get('title', '')
        description = cleaned_data.get('description', '')
        
        if title and description and title.lower() == description.lower():
            raise ValidationError('Description should be more detailed than title.')
        
        return cleaned_data


class TicketCommentForm(forms.ModelForm):
    """Form for adding comments to tickets."""
    
    class Meta:
        model = TicketComment
        fields = ['text']
        
        widgets = {
            'text': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add a comment or suggestion...',
                'class': 'form-control',
                'maxlength': '1000'
            }),
        }
    
    def clean_text(self):
        """Validate comment text."""
        text = self.cleaned_data.get('text', '').strip()
        
        if len(text) < 5:
            raise ValidationError('Comment must be at least 5 characters.')
        
        if len(text) > 1000:
            raise ValidationError('Comment cannot be longer than 1000 characters.')
        
        return text
