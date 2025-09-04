from django.urls import path
from . import views

app_name = 'interview_trainer'

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('chat/', views.chat, name='chat'),
    path('select-type/', views.select_interview_type, name='select_interview_type'),
    path('chat/<int:session_id>/', views.chat_session, name='chat_session'),
    path('session/<int:session_id>/', views.session_detail, name='session_detail'),
    path('profile/', views.profile_settings, name='profile_settings'),
]