from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from interview_trainer.models import InterviewSession
from .services import EvaluationService, ReportGenerator
from .models import FeedbackReport, UserAnalytics, CompetencyDefinition
from django.db.models import Avg, Window, F
from django.db.models.functions import Rank


def evaluate_time_management(session):
    """
    Calcula la evaluación de gestión del tiempo para una `InterviewSession`.

    Retorna una tupla: (feedback_text, score_float)

    Reglas (heurísticas simples):
    - Tiempo permitido por defecto: session.total_time_allowed (segundos).
    - Si el tiempo usado está en el rango 80%-100% del permitido => score 10 (óptimo uso del tiempo).
    - Si usó menos del 80% => score proporcional (0-10) escalado hasta un mínimo de 4.
    - Si excedió el tiempo => penalización proporcional (10/percent) con minimo 0.
    - Devuelve feedback textual con consejos.
    """
    # Seguridad: revisar que existen los datos necesarios
    try:
        total_allowed = int(getattr(session, 'total_time_allowed', 900) or 900)
        total_used = int(getattr(session, 'total_time_used', 0) or 0)
    except Exception:
        return ('No hay datos de tiempo suficientes para evaluar.', None)

    if total_allowed <= 0:
        return ('Evaluación de tiempo no disponible (configuración inválida).', None)

    percent = float(total_used) / float(total_allowed) if total_allowed else 0.0

    # Categorías y cálculo de score
    if 0.8 <= percent <= 1.0:
        score = 10.0
        feedback = (
            'Excelente gestión del tiempo: aprovechaste el período de práctica de manera equilibrada. '
            'Mantén el ritmo y usa los últimos minutos para sintetizar tus respuestas.'
        )
    elif percent < 0.8:
        # Contestó notablemente más rápido que el tiempo recomendado
        # Escalamos linealmente hasta 0.8 como el punto óptimo
        scale = percent / 0.8 if 0.8 > 0 else 0
        raw_score = 10.0 * scale
        score = max(4.0, round(raw_score, 1))
        feedback = (
            'Contestaste más rápido de lo recomendado. ' 
            'Intenta desarrollar un poco más tus respuestas y aprovechar el tiempo para ofrecer ejemplos concretos y estructura (situación, tarea, acción, resultado).'
        )
    else:
        # percent > 1.0: excedió el tiempo
        # Penalizamos de forma inversa proporcional
        raw = 10.0 / percent
        score = max(0.0, round(raw, 1))
        feedback = (
            'Te excediste del tiempo ideal. Trata de sintetizar mejor y practicar respuestas concisas; ' 
            'puedes usar bullets y enfocarte en lo esencial (causa, acción, resultado).' 
            f' Tiempo usado: {total_used // 60}m {total_used % 60}s, Tiempo ideal: {total_allowed // 60}m.'
        )

    return (feedback, float(score) if score is not None else None)

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
        'responses_count': user_messages,
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

@login_required
def global_ranking(request, role_slug='it'):
    """
    🏆 PROPÓSITO: Muestra el ranking global de usuarios para un rol específico.
    """
    # Obtener todos los tipos de entrevista para el selector
    all_roles = InterviewSession.INTERVIEW_TYPES

    # Filtrar reportes de feedback para el rol seleccionado
    feedback_reports = FeedbackReport.objects.filter(
        session__session_type=role_slug
    ).select_related('session__user')

    # Calcular el puntaje promedio por usuario para ese rol
    user_scores = feedback_reports.values(
        'session__user__username', 'session__user_id'
    ).annotate(
        average_score=Avg('average_score')
    ).order_by('-average_score')

    # Añadir el ranking usando Window functions
    ranked_users = user_scores.annotate(
        rank=Window(
            expression=Rank(),
            order_by=F('average_score').desc()
        )
    )

    # Obtener la posición del usuario actual
    current_user_rank = None
    for user in ranked_users:
        if user['session__user_id'] == request.user.id:
            current_user_rank = user
            break

    # Obtener el nombre legible del rol
    selected_role_name = dict(all_roles).get(role_slug, 'General')

    context = {
        'ranked_users': ranked_users[:20],  # Top 20
        'current_user_rank': current_user_rank,
        'all_roles': all_roles,
        'selected_role': role_slug,
        'selected_role_name': selected_role_name,
    }
    return render(request, 'evaluation/global_ranking.html', context)
