from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from interview_trainer.models import InterviewSession
from .services import EvaluationService, ReportGenerator
from .models import FeedbackReport, UserAnalytics, CompetencyDefinition

@login_required
def session_feedback(request, session_id):
    """
    📊 PROPÓSITO: Mostrar feedback y puntajes de competencias de una sesión
    📝 QUÉ HACE: Muestra evaluación detallada con gráficos y recomendaciones
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    evaluation_service = EvaluationService()
    
    # Obtener evaluación
    evaluation_data = evaluation_service.get_session_evaluation(session)
    
    if not evaluation_data['exists']:
        messages.warning(request, 'El feedback para esta sesión aún no ha sido generado.')
        return redirect('interview_trainer:session_detail', session_id=session_id)
    
    # Preparar datos para el template
    competency_data = evaluation_data['competency_data']
    
    # Calcular promedio y estadísticas
    average_score = evaluation_data['average_score']
    average_percentage = (average_score / 10) * 100
    performance_level = evaluation_data['performance_level']
    
    # Determinar clase CSS para el performance
    if average_score >= 8:
        performance_class = "success"
    elif average_score >= 6:
        performance_class = "info"
    elif average_score >= 4:
        performance_class = "warning"
    else:
        performance_class = "danger"
    
    # Calcular estadísticas de sesión
    messages_list = session.messages.all()
    user_messages = messages_list.filter(is_user=True).count()
    ai_messages = messages_list.filter(is_user=False).count()
    
    context = {
        'session': session,
        'feedback_report': evaluation_data['feedback_report'],
        'competency_data': competency_data,
        'average_score': average_score,
        'average_percentage': average_percentage,
        'performance_level': performance_level,
        'performance_class': performance_class,
        'user_messages': user_messages,
        'ai_messages': ai_messages,
        'session_duration_minutes': evaluation_data['session_duration'],
        'questions_count': ai_messages,  # Usar el conteo de mensajes de AI
        'generated_at': evaluation_data['generated_at'],
    }
    
    return render(request, 'evaluation/session_feedback.html', context)

@login_required
def user_dashboard(request):
    """
    📈 PROPÓSITO: Dashboard principal de analytics del usuario
    """
    evaluation_service = EvaluationService()
    report_generator = ReportGenerator()
    
    # Obtener datos del usuario
    analytics = evaluation_service.get_user_progress(request.user)
    
    # Obtener resumen si hay datos
    summary = None
    if analytics['total_sessions'] > 0:
        summary = report_generator.generate_user_summary_report(request.user)
    
    # Obtener competencias definidas
    competencies = CompetencyDefinition.get_default_competencies()
    
    context = {
        'analytics': analytics,
        'summary': summary,
        'competencies': competencies,
        'has_data': analytics['total_sessions'] > 0
    }
    
    return render(request, 'evaluation/user_dashboard.html', context)

@login_required
def competency_analysis(request):
    """
    🎯 PROPÓSITO: Análisis detallado de competencias del usuario
    """
    evaluation_service = EvaluationService()
    
    # Obtener analytics básicos
    analytics = evaluation_service.get_user_progress(request.user)
    
    if analytics['total_sessions'] == 0:
        messages.info(request, 'Necesitas completar al menos una entrevista para ver el análisis de competencias.')
        return redirect('interview_trainer:select_interview_type')
    
    # Obtener análisis detallado de competencias
    from .models import CompetencyScore
    from django.db.models import Avg, Count, Max, Min
    
    competency_analysis = CompetencyScore.objects.filter(
        session__user=request.user
    ).values('competency_name').annotate(
        avg_score=Avg('score'),
        max_score=Max('score'),
        min_score=Min('score'),
        total_evaluations=Count('id')
    ).order_by('-avg_score')
    
    # Obtener evolución temporal por competencia
    competency_evolution = {}
    for comp_data in competency_analysis:
        comp_name = comp_data['competency_name']
        comp_scores = CompetencyScore.objects.filter(
            session__user=request.user,
            competency_name=comp_name
        ).order_by('created_at')
        
        competency_evolution[comp_name] = [
            {
                'score': score.score,
                'date': score.created_at.strftime('%d/%m'),
                'session_title': score.session.title
            }
            for score in comp_scores
        ]
    
    context = {
        'analytics': analytics,
        'competency_analysis': competency_analysis,
        'competency_evolution': competency_evolution,
    }
    
    return render(request, 'evaluation/competency_analysis.html', context)

@login_required
def evaluation_history(request):
    """
    📋 PROPÓSITO: Historial de todas las evaluaciones del usuario
    """
    # Obtener todas las evaluaciones del usuario
    feedback_reports = FeedbackReport.objects.filter(
        session__user=request.user
    ).order_by('-generated_at').select_related('session')
    
    # Calcular estadísticas
    total_evaluations = feedback_reports.count()
    if total_evaluations > 0:
        avg_score = sum(report.average_score for report in feedback_reports) / total_evaluations
        best_score = max(report.average_score for report in feedback_reports)
        latest_score = feedback_reports.first().average_score if feedback_reports else 0
    else:
        avg_score = best_score = latest_score = 0
    
    context = {
        'feedback_reports': feedback_reports,
        'total_evaluations': total_evaluations,
        'avg_score': round(avg_score, 1),
        'best_score': round(best_score, 1),
        'latest_score': round(latest_score, 1),
    }
    
    return render(request, 'evaluation/evaluation_history.html', context)
