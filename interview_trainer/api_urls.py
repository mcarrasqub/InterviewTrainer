from django.urls import path
from . import api_views

app_name = 'interview_trainer_api'

urlpatterns = [
    path('send-message/', api_views.send_message, name='api_send_message'),
    path('sessions/', api_views.get_sessions, name='api_get_sessions'),
    path('sessions/<int:session_id>/messages/', api_views.get_session_messages, name='api_get_session_messages'),
    path('sessions/<int:session_id>/timer/', api_views.session_timer_status, name='api_session_timer_status'),
    path('sessions/<int:session_id>/timer/tick/', api_views.session_timer_tick, name='api_session_timer_tick'),
    path('messages/<int:message_id>/', api_views.get_message, name='api_get_message'),
    path('sessions/<int:session_id>/delete/', api_views.delete_session, name='delete_session'),
    path('sessions/delete/', api_views.delete_sessions_bulk, name='delete_sessions_bulk'),
    path('sessions/delete-all/', api_views.delete_all_sessions, name='delete_all_sessions'),
]
