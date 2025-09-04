from django.urls import path
from . import views

app_name = 'evaluation'

urlpatterns = [
    # Vistas principales
    path('session/<int:session_id>/feedback/', views.session_feedback, name='session_feedback'),
    path('dashboard/', views.user_dashboard, name='user_dashboard'),
    path('competencies/', views.competency_analysis, name='competency_analysis'),
    path('history/', views.evaluation_history, name='evaluation_history'),
]
