from django.contrib import messages
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render

from .forms import LoginForm, RegisterForm


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
