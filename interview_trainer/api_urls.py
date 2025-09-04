from django.urls import path
from . import api_views

app_name = 'interview_trainer_api'

urlpatterns = [
    path('send-message/', api_views.send_message, name='api_send_message'),
    path('sessions/', api_views.get_sessions, name='api_get_sessions'),
    path('sessions/<int:session_id>/messages/', api_views.get_session_messages, name='api_get_session_messages'),
    # ❌ REMOVIDO: save-api-key (ya no es necesario)
]
