from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.shortcuts import redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User

from .forms import LoginForm, RegisterForm, UserProfileUpdateForm, UserProfileExtendedForm, PasswordChangeForm
from .models import UserProfile


def register_view(request):
	if request.user.is_authenticated:
		return redirect('dashboard_home')

	if request.method == 'POST':
		form = RegisterForm(request.POST)
		if form.is_valid():
			form.save()
			messages.success(request, 'Account created successfully. Please log in.')
			return redirect('login')
	else:
		form = RegisterForm()

	return render(request, 'users/register.html', {'form': form})


def login_view(request):
	if request.user.is_authenticated:
		return redirect('dashboard_home')

	if request.method == 'POST':
		form = LoginForm(request, data=request.POST)
		if form.is_valid():
			user = form.get_user()
			login(request, user)
			messages.success(request, 'Logged in successfully.')
			return redirect('dashboard_home')
	else:
		form = LoginForm(request)

	return render(request, 'users/login.html', {'form': form})


def logout_view(request):
	logout(request)
	messages.info(request, 'You have been logged out.')
	return redirect('login')


@login_required
def profile_view(request):
	"""Display user profile information."""
	try:
		profile = request.user.profile
	except UserProfile.DoesNotExist:
		profile = UserProfile.objects.create(user=request.user)

	# Get ticket statistics
	all_tickets = request.user.tickets.all()
	resolved_count = all_tickets.filter(resolution_status='Resolved').count()
	pending_count = all_tickets.filter(resolution_status='Pending').count()

	context = {
		'user': request.user,
		'profile': profile,
		'total_tickets': all_tickets.count(),
		'resolved_count': resolved_count,
		'pending_count': pending_count,
	}
	return render(request, 'users/profile_dashboard.html', context)


@login_required
def edit_profile_view(request):
	"""Edit user profile information."""
	try:
		profile = request.user.profile
	except UserProfile.DoesNotExist:
		profile = UserProfile.objects.create(user=request.user)

	if request.method == 'POST':
		user_form = UserProfileUpdateForm(request.POST, instance=request.user)
		profile_form = UserProfileExtendedForm(request.POST, instance=profile)

		if user_form.is_valid() and profile_form.is_valid():
			user_form.save()
			profile_form.save()
			messages.success(request, 'Profile updated successfully.')
			return redirect('profile_view')
	else:
		user_form = UserProfileUpdateForm(instance=request.user)
		profile_form = UserProfileExtendedForm(instance=profile)

	context = {
		'user_form': user_form,
		'profile_form': profile_form,
		'profile': profile,
	}
	return render(request, 'users/edit_profile.html', context)


@login_required
def change_password_view(request):
	"""Change user password."""
	if request.method == 'POST':
		form = PasswordChangeForm(request.POST, user=request.user)
		if form.is_valid():
			new_password = form.cleaned_data.get('new_password')

			# Update password using the authenticated user object
			request.user.set_password(new_password)
			request.user.save()
			
			# Re-authenticate user to keep them logged in
			# Use update_session_auth_hash to maintain session
			from django.contrib.auth import update_session_auth_hash
			update_session_auth_hash(request, request.user)
			
			messages.success(request, 'Password changed successfully.')
			return redirect('profile_view')
	else:
		form = PasswordChangeForm(user=request.user)

	context = {'form': form}
	return render(request, 'users/change_password.html', context)
