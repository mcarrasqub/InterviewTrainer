from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from interview_trainer.models import InterviewSession
from .services import EvaluationService, ReportGenerator
from .models import FeedbackReport, CompetencyScore, UserAnalytics
import asyncio
import logging

logger = logging.getLogger(__name__)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def generate_evaluation(request, session_id):
    """
    📊 PROPÓSITO: API para generar evaluación completa
    🎯 QUÉ HACE: Analiza sesión y crea feedback con puntajes
    """
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        evaluation_service = EvaluationService()
        
        # Verificar si se puede generar
        can_eval = evaluation_service.can_generate_evaluation(session)
        if not can_eval['can_generate']:
            return Response({
                'error': can_eval['reason'],
                'existing': can_eval.get('existing', False),
                'questions_count': can_eval.get('questions_count', 0)
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Generar evaluación
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(
            evaluation_service.generate_session_evaluation(session)
        )
        loop.close()
        
        return Response({
            'success': True,
            'message': 'Evaluación generada exitosamente',
            'session_id': session_id,
            'average_score': result['average_score'],
            'performance_level': result['performance_level'],
            'questions_analyzed': result['questions_analyzed'],
            'session_duration': result['session_duration']
        })
        
    except ValueError as e:
        return Response({
            'error': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Error generando evaluación: {str(e)}")
        return Response({
            'error': f'Error interno: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_evaluation(request, session_id):
    """
    📋 PROPÓSITO: API para obtener evaluación existente
    """
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        evaluation_service = EvaluationService()
        
        evaluation_data = evaluation_service.get_session_evaluation(session)
        
        if not evaluation_data['exists']:
            return Response({
                'exists': False,
                'can_generate': evaluation_data['can_generate']['can_generate'],
                'questions_count': evaluation_data['can_generate'].get('questions_count', 0),
                'min_required': evaluation_data['can_generate'].get('min_required', 10),
                'reason': evaluation_data['can_generate']['reason']
            }, status=status.HTTP_404_NOT_FOUND)
        
        return Response({
            'success': True,
            'exists': True,
            'average_score': evaluation_data['average_score'],
            'performance_level': evaluation_data['performance_level'],
            'questions_analyzed': evaluation_data['questions_analyzed'],
            'session_duration': evaluation_data['session_duration'],
            'competency_scores': [
                {
                    'name': comp['name'],
                    'score': comp['score'],
                    'feedback': comp['feedback'],
                    'examples': comp['examples'],
                    'improvement_areas': comp['improvement_areas']
                }
                for comp in evaluation_data['competency_data']
            ],
            'overall_feedback': evaluation_data['feedback_report'].overall_feedback,
            'generated_at': evaluation_data['generated_at'].isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo evaluación: {str(e)}")
        return Response({
            'error': f'Error obteniendo evaluación: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_analytics(request):
    """
    📈 PROPÓSITO: API para obtener analytics del usuario
    """
    try:
        evaluation_service = EvaluationService()
        analytics = evaluation_service.get_user_progress(request.user)
        
        return Response({
            'success': True,
            'analytics': analytics
        })
        
    except Exception as e:
        logger.error(f"Error obteniendo analytics: {str(e)}")
        return Response({
            'error': f'Error obteniendo analytics: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_summary(request):
    """
    📊 PROPÓSITO: API para obtener resumen completo del usuario
    """
    try:
        report_generator = ReportGenerator()
        summary = report_generator.generate_user_summary_report(request.user)
        
        if 'error' in summary:
            return Response({
                'error': summary['error']
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Serializar datos para API
        recent_sessions_data = []
        for session_report in summary['recent_sessions']:
            recent_sessions_data.append({
                'session_title': session_report.session.title,
                'session_type': session_report.session.session_type,
                'average_score': session_report.average_score,
                'performance_level': session_report.performance_level,
                'questions_analyzed': session_report.questions_analyzed,
                'generated_at': session_report.generated_at.isoformat()
            })
        
        return Response({
            'success': True,
            'summary': {
                'user': {
                    'username': summary['user'].username,
                    'first_name': summary['user'].first_name,
                    'last_name': summary['user'].last_name
                },
                'analytics': {
                    'total_sessions': summary['analytics'].total_sessions_evaluated,
                    'average_score': summary['analytics'].average_overall_score,
                    'strongest_competency': summary['analytics'].strongest_competency,
                    'weakest_competency': summary['analytics'].weakest_competency,
                    'total_questions': summary['analytics'].total_questions_answered,
                    'total_time_hours': summary['analytics'].total_session_time_minutes / 60
                },
                'recent_sessions': recent_sessions_data,
                'progress_status': summary['progress_status'],
                'progress_change': summary['progress_change'],
                'generated_at': summary['generated_at'].isoformat()
            }
        })
        
    except Exception as e:
        logger.error(f"Error generando resumen: {str(e)}")
        return Response({
            'error': f'Error generando resumen: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_competency_analysis(request):
    """
    🎯 PROPÓSITO: API para análisis detallado de competencias
    """
    try:
        # Obtener todas las evaluaciones del usuario
        user_scores = CompetencyScore.objects.filter(
            session__user=request.user
        ).select_related('session')
        
        if not user_scores.exists():
            return Response({
                'error': 'No hay evaluaciones disponibles'
            }, status=status.HTTP_404_NOT_FOUND)
        
        # Agrupar por competencia
        from django.db.models import Avg, Count, Max, Min
        competency_analysis = user_scores.values('competency_name').annotate(
            avg_score=Avg('score'),
            max_score=Max('score'),
            min_score=Min('score'),
            total_evaluations=Count('id'),
            latest_score=Max('score')  # Simplificado
        ).order_by('-avg_score')
        
        # Obtener evolución temporal por competencia
        competency_evolution = {}
        for comp_data in competency_analysis:
            comp_name = comp_data['competency_name']
            comp_scores = user_scores.filter(
                competency_name=comp_name
            ).order_by('created_at')[:10]  # Últimas 10
            
            competency_evolution[comp_name] = [
                {
                    'score': score.score,
                    'date': score.created_at.strftime('%d/%m'),
                    'session_title': score.session.title
                }
                for score in comp_scores
            ]
        
        return Response({
            'success': True,
            'competency_analysis': list(competency_analysis),
            'competency_evolution': competency_evolution,
            'total_evaluations': user_scores.count()
        })
        
    except Exception as e:
        logger.error(f"Error en análisis de competencias: {str(e)}")
        return Response({
            'error': f'Error en análisis: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
