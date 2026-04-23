from django.urls import path

from .views import (
	login_view, logout_view, register_view,
	profile_view, edit_profile_view, change_password_view
)


urlpatterns = [
	path('register/', register_view, name='register'),
	path('login/', login_view, name='login'),
	path('logout/', logout_view, name='logout'),
	
	# Profile management
	path('profile/', profile_view, name='profile_view'),
	path('profile/edit/', edit_profile_view, name='edit_profile'),
	path('profile/password/', change_password_view, name='change_password'),
]
