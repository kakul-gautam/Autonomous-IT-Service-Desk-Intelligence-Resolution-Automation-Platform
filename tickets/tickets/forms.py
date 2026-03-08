from django import forms
from .models import Ticket

# Form for creating and editing tickets
# Uses ModelForm to automatically generate form fields from the Ticket model
class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        # Fields to include in the form
        fields = ['title', 'description']
        
        # Optional: Add widgets to customize form rendering
        widgets = {
            'title': forms.TextInput(attrs={'placeholder': 'Brief title of the issue', 'class': 'form-control'}),
            'description': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Detailed description', 'class': 'form-control'}),
        }
