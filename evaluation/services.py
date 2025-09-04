import logging
from typing import Dict, List
from django.db import models
from django.contrib.auth.models import User
from interview_trainer.models import InterviewSession, ChatMessage
from interview_trainer.services import GeminiService
from .models import CompetencyScore, FeedbackReport, UserAnalytics, CompetencyDefinition
from django.utils import timezone

logger = logging.getLogger(__name__)

class EvaluationService:
    """
    🎯 PROPÓSITO: Servicio especializado en evaluación y feedback
    📊 QUÉ HACE: Maneja toda la lógica de análisis y puntajes
    """
    
    def __init__(self):
        self.gemini_service = GeminiService()
    
    def can_generate_evaluation(self, session: InterviewSession) -> Dict:
        """
        ✅ PROPÓSITO: Verifica si una sesión puede ser evaluada
        """
        if hasattr(session, 'feedback_report') and session.feedback_report:
            return {
                'can_generate': False,
                'reason': 'Ya existe evaluación',
                'existing': True
            }
        
        questions_count = self._count_session_questions(session)
        min_questions = 15
        
        return {
            'can_generate': questions_count == min_questions,
            'questions_count': questions_count,
            'min_required': min_questions,
            'reason': f'Se necesitan al menos {min_questions} preguntas' if questions_count < min_questions else 'Listo para evaluar'
        }
    
    def _count_session_questions(self, session: InterviewSession) -> int:
        """
        🔢 PROPÓSITO: Cuenta las preguntas realizadas por Lumo
        """
        ai_messages = session.messages.filter(is_user=False)
        questions_count = 0
        
        for message in ai_messages:
            # Contar mensajes que contienen '?'
            if '?' in message.content:
                questions_count += message.content.count('?')
        
        return questions_count
    
    async def generate_session_evaluation(self, session: InterviewSession) -> Dict:
        """
        📊 PROPÓSITO: Genera evaluación completa de una sesión
        """
        # Verificar si se puede evaluar
        can_eval = self.can_generate_evaluation(session)
        if not can_eval['can_generate']:
            raise ValueError(can_eval['reason'])
        
        messages = session.messages.order_by('timestamp')
        
        if messages.count() < 5:
            raise ValueError("Sesión insuficiente para evaluación (mínimo 5 mensajes)")
        
        # Usar GeminiService para generar el análisis
        feedback_data = await self.gemini_service.generate_feedback_and_scores(session, messages)
        
        # Procesar y guardar resultados
        return await self._save_evaluation_results(session, feedback_data, can_eval['questions_count'])
    
    async def _save_evaluation_results(self, session: InterviewSession, feedback_data: Dict, questions_count: int) -> Dict:
        """
        💾 PROPÓSITO: Guarda resultados de evaluación en base de datos
        """
        try:
            # Calcular promedio y métricas
            scores = feedback_data['competency_scores']
            average_score = sum(comp['score'] for comp in scores.values()) / len(scores)
            performance_level = self._get_performance_level(average_score)
            
            # Calcular duración de sesión
            session_duration = self._calculate_session_duration(session)
            
            # Crear reporte principal
            feedback_report = FeedbackReport.objects.create(
                session=session,
                overall_feedback=feedback_data['overall_feedback'],
                average_score=average_score,
                performance_level=performance_level,
                questions_analyzed=questions_count,
                session_duration_minutes=session_duration
            )
            
            # Crear puntajes de competencias
            competency_scores = []
            for comp_name, comp_data in scores.items():
                comp_score = CompetencyScore.objects.create(
                    session=session,
                    competency_name=comp_name,
                    score=comp_data['score'],
                    feedback=comp_data['feedback'],
                    examples=comp_data.get('example', ''),
                    improvement_areas=comp_data.get('improvement_area', '')
                )
                competency_scores.append(comp_score)
            
            # Actualizar analytics del usuario
            await self._update_user_analytics(session.user)
            
            return {
                'success': True,
                'feedback_report': feedback_report,
                'competency_scores': competency_scores,
                'average_score': average_score,
                'performance_level': performance_level,
                'questions_analyzed': questions_count,
                'session_duration': session_duration
            }
            
        except Exception as e:
            logger.error(f"Error guardando evaluación: {str(e)}")
            raise e
    
    def _get_performance_level(self, average_score: float) -> str:
        """
        📊 PROPÓSITO: Determina nivel de performance basado en promedio
        """
        if average_score >= 8.0:
            return "Excelente"
        elif average_score >= 6.0:
            return "Bueno"
        elif average_score >= 4.0:
            return "Regular"
        else:
            return "Necesita Mejora"
    
    def _calculate_session_duration(self, session: InterviewSession) -> int:
        """
        ⏱️ PROPÓSITO: Calcula duración de la sesión en minutos
        """
        messages = session.messages.order_by('timestamp')
        if messages.count() < 2:
            return 0
        
        first_message = messages.first()
        last_message = messages.last()
        duration = last_message.timestamp - first_message.timestamp
        return max(1, duration.seconds // 60)
    
    async def _update_user_analytics(self, user: User):
        """
        📈 PROPÓSITO: Actualiza analytics del usuario
        """
        analytics, created = UserAnalytics.objects.get_or_create(user=user)
        
        # Recalcular estadísticas
        user_reports = FeedbackReport.objects.filter(session__user=user)
        
        if user_reports.exists():
            analytics.total_sessions_evaluated = user_reports.count()
            analytics.average_overall_score = user_reports.aggregate(
                avg_score=models.Avg('average_score')
            )['avg_score'] or 0
            
            # Calcular totales
            analytics.total_questions_answered = user_reports.aggregate(
                total_questions=models.Sum('questions_analyzed')
            )['total_questions'] or 0
            
            analytics.total_session_time_minutes = user_reports.aggregate(
                total_time=models.Sum('session_duration_minutes')
            )['total_time'] or 0
            
            # Encontrar competencia más fuerte y más débil
            all_scores = CompetencyScore.objects.filter(session__user=user)
            if all_scores.exists():
                competency_avgs = all_scores.values('competency_name').annotate(
                    avg_score=models.Avg('score')
                ).order_by('-avg_score')
                
                if competency_avgs:
                    analytics.strongest_competency = competency_avgs.first()['competency_name']
                    analytics.weakest_competency = competency_avgs.last()['competency_name']
            
            analytics.save()
    
    def get_user_progress(self, user: User) -> Dict:
        """
        📈 PROPÓSITO: Obtiene progreso y analytics del usuario (simplificado)
        """
        # Calcular directamente desde FeedbackReport
        user_reports = FeedbackReport.objects.filter(session__user=user)
        
        if not user_reports.exists():
            return {
                'total_sessions': 0,
                'average_score': 0,
                'progress_trend': [],
                'competency_strengths': [],
                'improvement_areas': [],
                'total_questions': 0,
                'total_time_hours': 0,
                'trend': 'insuficiente'
            }
        
        # Estadísticas básicas
        total_sessions = user_reports.count()
        average_score = user_reports.aggregate(
            avg_score=models.Avg('average_score')
        )['avg_score'] or 0
        
        # Obtener tendencia de progreso (últimas 10 sesiones)
        recent_reports = user_reports.order_by('-generated_at')[:10]
        
        progress_trend = [
            {
                'session_title': report.session.title,
                'score': report.average_score,
                'date': report.generated_at.strftime('%d/%m'),
                'performance_level': report.performance_level
            }
            for report in recent_reports
        ]
        
        # Obtener fortalezas y debilidades por competencia
        competency_stats = CompetencyScore.objects.filter(
            session__user=user
        ).values('competency_name').annotate(
            avg_score=models.Avg('score'),
            count=models.Count('id')
        ).order_by('-avg_score')
        
        strengths = [comp for comp in competency_stats if comp['avg_score'] >= 7]
        weaknesses = [comp for comp in competency_stats if comp['avg_score'] < 6]
        
        # Calcular totales
        total_time_minutes = user_reports.aggregate(
            total_time=models.Sum('session_duration_minutes')
        )['total_time'] or 0
        
        return {
            'total_sessions': total_sessions,
            'average_score': round(average_score, 1),
            'strongest_competency': strengths[0]['competency_name'] if strengths else 'N/A',
            'weakest_competency': weaknesses[-1]['competency_name'] if weaknesses else 'N/A',
            'total_questions': 0,  # TODO: Calcular cuando sea necesario
            'total_time_hours': round(total_time_minutes / 60, 1),
            'progress_trend': progress_trend,
            'competency_strengths': strengths,
            'improvement_areas': weaknesses,
            'trend': self._calculate_trend(recent_reports),
            'last_updated': timezone.now()
        }
    
    def _calculate_trend(self, reports):
        """
        📊 PROPÓSITO: Calcula la tendencia de progreso
        """
        if len(reports) < 2:
            return "insuficiente"
        
        recent_avg = sum(r.average_score for r in reports[:2]) / 2
        older_avg = sum(r.average_score for r in reports[2:]) / max(1, len(reports) - 2)
        
        if recent_avg > older_avg + 0.5:
            return "mejorando"
        elif recent_avg < older_avg - 0.5:
            return "bajando"
        else:
            return "estable"
    
    def get_session_evaluation(self, session: InterviewSession) -> Dict:
        """
        📋 PROPÓSITO: Obtiene evaluación existente de una sesión
        """
        try:
            feedback_report = session.feedback_report
            competency_scores = session.competency_scores.all()
            
            # Preparar datos para gráficos
            competency_data = []
            for comp_score in competency_scores:
                competency_data.append({
                    'name': comp_score.competency_name,
                    'score': comp_score.score,
                    'feedback': comp_score.feedback,
                    'examples': comp_score.examples,
                    'improvement_areas': comp_score.improvement_areas,
                    'percentage': (comp_score.score / 10) * 100
                })
            
            return {
                'exists': True,
                'feedback_report': feedback_report,
                'competency_data': competency_data,
                'average_score': feedback_report.average_score,
                'performance_level': feedback_report.performance_level,
                'questions_analyzed': feedback_report.questions_analyzed,
                'session_duration': feedback_report.session_duration_minutes,
                'generated_at': feedback_report.generated_at
            }
            
        except FeedbackReport.DoesNotExist:
            return {
                'exists': False,
                'can_generate': self.can_generate_evaluation(session)
            }

class ReportGenerator:
    """
    📄 PROPÓSITO: Generador de reportes avanzados
    📊 QUÉ HACE: Crea reportes personalizados y exportaciones
    """
    
    def generate_user_summary_report(self, user: User) -> Dict:
        """
        📊 PROPÓSITO: Genera reporte resumen del usuario (simplificado)
        """
        user_reports = FeedbackReport.objects.filter(session__user=user)
        if not user_reports.exists():
            return {'error': 'No hay datos suficientes'}
        
        recent_sessions = user_reports.order_by('-generated_at')[:5]
        
        # Análisis de progreso
        if recent_sessions.count() >= 2:
            latest_score = recent_sessions[0].average_score
            previous_scores = [r.average_score for r in recent_sessions[1:]]
            previous_avg = sum(previous_scores) / len(previous_scores)
            
            progress_change = latest_score - previous_avg
            progress_status = "mejoró" if progress_change > 0.3 else "se mantiene" if abs(progress_change) <= 0.3 else "bajó"
        else:
            progress_status = "insuficiente"
            progress_change = 0
        
        return {
            'user': user,
            'total_sessions': user_reports.count(),
            'average_score': round(user_reports.aggregate(avg=models.Avg('average_score'))['avg'] or 0, 1),
            'recent_sessions': recent_sessions,
            'progress_status': progress_status,
            'progress_change': round(progress_change, 1),
            'generated_at': timezone.now()
        }
