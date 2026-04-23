from django import forms
from django.core.exceptions import ValidationError
import re

from .models import SupportComment, SupportTicket


_SUSPICIOUS_INPUT_PATTERN = re.compile(
    r"(;|--|/\*|\*/|\bunion\b|\bselect\b|\binsert\b|\bupdate\b|\bdelete\b|\bdrop\b|\balter\b)",
    flags=re.IGNORECASE,
)


def _validate_safe_text(value, field_name):
    if value and _SUSPICIOUS_INPUT_PATTERN.search(value):
        raise ValidationError(f'{field_name} contains unsafe content.')
    return value


class SupportTicketForm(forms.ModelForm):
    class Meta:
        model = SupportTicket
        fields = ['title', 'description', 'category', 'labels']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Short issue title'}),
            'description': forms.Textarea(attrs={'class': 'form-control', 'rows': 6, 'placeholder': 'Describe your issue in detail'}),
            'category': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Category (e.g. Billing, Access, Feature, Bug)'}),
            'labels': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'bug, urgent, network'}),
        }

    def clean_title(self):
        title = (self.cleaned_data.get('title') or '').strip()
        if not title:
            raise ValidationError('Title is required.')
        if len(title) < 4:
            raise ValidationError('Title must be at least 4 characters.')
        return _validate_safe_text(title, 'Title')

    def clean_description(self):
        description = (self.cleaned_data.get('description') or '').strip()
        if not description:
            raise ValidationError('Description is required.')
        if len(description) < 10:
            raise ValidationError('Description must be at least 10 characters.')
        return _validate_safe_text(description, 'Description')

    def clean_category(self):
        category = (self.cleaned_data.get('category') or '').strip()
        if not category:
            raise ValidationError('Category is required.')
        return _validate_safe_text(category, 'Category')

    def clean_labels(self):
        labels = (self.cleaned_data.get('labels') or '').strip()
        return _validate_safe_text(labels, 'Labels')


class SupportCommentForm(forms.ModelForm):
    class Meta:
        model = SupportComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a helpful comment...'}),
        }

    def clean_comment(self):
        comment = (self.cleaned_data.get('comment') or '').strip()
        if not comment:
            raise ValidationError('Comment cannot be empty.')
        if len(comment) < 3:
            raise ValidationError('Comment must be at least 3 characters.')
        return _validate_safe_text(comment, 'Comment')
