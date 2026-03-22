from django.urls import path

from . import views


urlpatterns = [
    path('', views.support_list, name='support_list'),
    path('create/', views.support_create, name='support_create'),
    path('<int:ticket_id>/upvote/', views.upvote_ticket, name='support_upvote'),
    path('<int:ticket_id>/', views.support_detail, name='support_detail'),
]
