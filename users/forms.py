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


class UserProfileUpdateForm(forms.ModelForm):
	"""Form to update user basic information."""
	first_name = forms.CharField(required=False, max_length=30)
	last_name = forms.CharField(required=False, max_length=30)
	email = forms.EmailField(required=True)

	class Meta:
		model = User
		fields = ('first_name', 'last_name', 'email', 'username')

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'
		# Make username read-only
		self.fields['username'].widget.attrs['readonly'] = True

	def clean_username(self):
		"""Prevent username changes."""
		return self.instance.username


class UserProfileExtendedForm(forms.ModelForm):
	"""Form to update user profile information."""
	class Meta:
		model = UserProfile
		fields = ('department',)

	def __init__(self, *args, **kwargs):
		super().__init__(*args, **kwargs)
		for field in self.fields.values():
			field.widget.attrs['class'] = 'form-control'


class PasswordChangeForm(forms.Form):
	"""Form for users to change their password.
	
	Requires user instance to be passed in __init__ for proper validation
	of current password and Django password validators.
	"""
	current_password = forms.CharField(
		label='Current Password',
		widget=forms.PasswordInput(attrs={'class': 'form-control'})
	)
	new_password = forms.CharField(
		label='New Password',
		widget=forms.PasswordInput(attrs={'class': 'form-control'})
	)
	confirm_password = forms.CharField(
		label='Confirm New Password',
		widget=forms.PasswordInput(attrs={'class': 'form-control'})
	)

	def __init__(self, *args, user=None, **kwargs):
		"""Initialize with user instance for validation."""
		super().__init__(*args, **kwargs)
		self.user = user

	def clean_current_password(self):
		"""Verify the current password is correct."""
		current = self.cleaned_data.get('current_password')
		
		if self.user and current:
			if not self.user.check_password(current):
				raise forms.ValidationError('Current password is incorrect.')
		
		return current

	def clean(self):
		"""Validate password requirements."""
		cleaned_data = super().clean()
		new_pass = cleaned_data.get('new_password')
		confirm_pass = cleaned_data.get('confirm_password')

		if new_pass and confirm_pass and new_pass != confirm_pass:
			raise forms.ValidationError('New passwords do not match.')

		# Validate password length
		if new_pass and len(new_pass) < 8:
			raise forms.ValidationError('Password must be at least 8 characters long.')

		# Use Django password validators if validator module is available
		if new_pass and self.user:
			try:
				from django.contrib.auth.password_validation import validate_password
				validate_password(new_pass, self.user)
			except forms.ValidationError as e:
				self.add_error('new_password', e)

		return cleaned_data
