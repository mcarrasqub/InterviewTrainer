from django.urls import path
from . import api_views
from .api_views import delete_session

app_name = 'interview_trainer_api'

urlpatterns = [
    path('send-message/', api_views.send_message, name='api_send_message'),
    path('sessions/', api_views.get_sessions, name='api_get_sessions'),
    path('sessions/<int:session_id>/messages/', api_views.get_session_messages, name='api_get_session_messages'),
    path('sessions/<int:session_id>/delete/', delete_session, name='delete_session'),
]
