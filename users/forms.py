from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile


class RegisterForm(UserCreationForm):
	email = forms.EmailField(required=False)
	department = forms.CharField(required=False, max_length=100)

	class Meta:
		model = User
		fields = ('username', 'email', 'password1', 'password2', 'department')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'

	def save(self, commit=True):
		user = super().save(commit=False)
		user.email = self.cleaned_data.get('email', '')
		if commit:
			user.save()
			profile, _ = UserProfile.objects.get_or_create(user=user)
			profile.department = self.cleaned_data.get('department', '')
			profile.save()
		return user


class LoginForm(AuthenticationForm):
	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'
