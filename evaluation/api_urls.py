from django.urls import path
from . import api_views

app_name = 'evaluation_api'

urlpatterns = [
    # Evaluación de sesiones
    path('sessions/<int:session_id>/evaluate/', api_views.generate_evaluation, name='api_generate_evaluation'),
    path('sessions/<int:session_id>/feedback/', api_views.get_session_evaluation, name='api_get_evaluation'),
    
    # Analytics de usuario
    path('user/analytics/', api_views.get_user_analytics, name='api_user_analytics'),
    path('user/summary/', api_views.get_user_summary, name='api_user_summary'),
    path('user/competencies/', api_views.get_competency_analysis, name='api_competency_analysis'),
]
