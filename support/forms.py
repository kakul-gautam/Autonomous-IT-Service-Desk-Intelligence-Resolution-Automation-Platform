from django import forms
from django.core.exceptions import ValidationError

from .models import SupportComment, SupportTicket


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
        return title

    def clean_description(self):
        description = (self.cleaned_data.get('description') or '').strip()
        if not description:
            raise ValidationError('Description is required.')
        return description

    def clean_category(self):
        category = (self.cleaned_data.get('category') or '').strip()
        if not category:
            raise ValidationError('Category is required.')
        return category


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
        return comment
