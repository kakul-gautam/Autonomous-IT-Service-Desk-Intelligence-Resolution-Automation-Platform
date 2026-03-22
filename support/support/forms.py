from django import forms

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


class SupportCommentForm(forms.ModelForm):
    class Meta:
        model = SupportComment
        fields = ['comment']
        widgets = {
            'comment': forms.Textarea(attrs={'class': 'form-control', 'rows': 3, 'placeholder': 'Write a helpful comment...'}),
        }
