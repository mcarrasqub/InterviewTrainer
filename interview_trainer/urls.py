from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('chat/', views.chat, name='chat'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('profile/', views.profile_settings, name='profile_settings'),
]