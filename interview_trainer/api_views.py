from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import InterviewSession, ChatMessage, UserProfile
from .services import GeminiService
from asgiref.sync import sync_to_async
import asyncio
import logging

# Importar servicio de evaluación para generación automática
try:
    from evaluation.services import EvaluationService
    EVALUATION_AVAILABLE = True
except ImportError:
    EVALUATION_AVAILABLE = False
    
logger = logging.getLogger(__name__)

# Funciones async para operaciones de base de datos
@sync_to_async
def create_user_message(session, content):
    return ChatMessage.objects.create(
        session=session,
        is_user=True,
        content=content
    )

@sync_to_async
def create_ai_message(session, content):
    return ChatMessage.objects.create(
        session=session,
        is_user=False,
        content=content
    )

@sync_to_async
def get_conversation_history(session):
    """Obtener historial de conversación excluyendo el último mensaje"""
    all_messages = list(session.messages.order_by('timestamp'))
    conversation_history = []
    
    # Todos los mensajes excepto el último (que será el mensaje actual del usuario)
    for msg in all_messages[:-1]:
        conversation_history.append({
            'is_user': msg.is_user,
            'content': msg.content
        })
    
    return conversation_history

@sync_to_async
def update_user_profile(user):
    profile, created = UserProfile.objects.get_or_create(user=user)
    profile.total_sessions = InterviewSession.objects.filter(user=user).count()
    profile.save()
    return profile

async def handle_evaluation_generation(session):
    """Maneja la generación automática de evaluación"""
    if not EVALUATION_AVAILABLE:
        return None
        
    try:
        evaluation_service = EvaluationService()
        
        # Verificar si la sesión puede ser evaluada
        can_eval = await evaluation_service.can_generate_evaluation(session)
        
        if can_eval['can_generate']:
            logger.info(f"🎯 Generando evaluación automática para sesión {session.id}")
            
            # Verificar si ya existe evaluación usando sync_to_async
            has_evaluation = await sync_to_async(
                lambda: hasattr(session, 'feedback_report') and session.feedback_report
            )()
            
            if not has_evaluation:
                # Generar evaluación automáticamente
                evaluation_result = await evaluation_service.generate_session_evaluation(session)
                
                if evaluation_result['success']:
                    evaluation_data = {
                        'evaluation_generated': True,
                        'average_score': evaluation_result['average_score'],
                        'performance_level': evaluation_result['performance_level']
                    }
                    logger.info(f"✅ Evaluación generada: {evaluation_result['average_score']}/10")
                    return evaluation_data
                else:
                    logger.error(f"❌ Error generando evaluación: {evaluation_result.get('error', 'Unknown')}")
            else:
                logger.info(f"📊 Evaluación ya existe para sesión {session.id}")
        else:
            logger.info(f"⏳ Sesión {session.id} no lista para evaluación: {can_eval['reason']}")
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error en evaluación automática: {str(e)}")
        return {'evaluation_error': str(e)}

async def process_message_async(user, message, session_id):
    """Procesa el mensaje de forma asíncrona"""
    try:
        # Obtener sesión usando sync_to_async
        session = await sync_to_async(
            lambda: InterviewSession.objects.get(id=session_id, user=user)
        )()
        
        # Guardar mensaje del usuario
        user_message = await create_user_message(session, message)
        
        # Obtener historial de conversación
        conversation_history = await get_conversation_history(session)
        
        # Debug logging
        logger.info(f"📤 Enviando a Gemini:")
        logger.info(f"   • Mensaje actual: '{message[:50]}...'")
        logger.info(f"   • Historial: {len(conversation_history)} mensajes")
        if conversation_history:
            last_sender = 'Usuario' if conversation_history[-1]['is_user'] else 'Lumo'
            logger.info(f"   • Último en historial: {last_sender}")
        else:
            logger.info(f"   • Historial vacío")
        
        # Generar respuesta
        gemini_service = GeminiService()
        ai_response = await gemini_service.generate_response(
            message=message,
            conversation_history=conversation_history,
            interview_type=session.session_type
        )
        
        # Guardar respuesta de IA
        ai_message = await create_ai_message(session, ai_response)
        
        # Manejar evaluación automática
        evaluation_data = await handle_evaluation_generation(session)
        
        # Actualizar perfil de usuario
        await update_user_profile(user)
        
        return {
            'success': True,
            'session_id': session.id,
            'user_message': {
                'id': user_message.id,
                'content': user_message.content,
                'timestamp': user_message.timestamp.isoformat()
            },
            'ai_response': {
                'id': ai_message.id,
                'content': ai_message.content,
                'timestamp': ai_message.timestamp.isoformat()
            },
            'evaluation': evaluation_data
        }
        
    except Exception as e:
        logger.error(f"Error en process_message_async: {str(e)}")
        raise e

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """
    💬 PROPÓSITO: API para enviar mensajes al chat
    📝 QUÉ HACE: Recibe mensaje del usuario, lo envía a Gemini, guarda respuesta
    ✅ CAMBIO: Ya no necesita API key del usuario
    """
    try:
        message = request.data.get('message', '').strip()
        session_id = request.data.get('session_id')
        
        if not message:
            return Response({'error': 'Mensaje vacío'}, status=status.HTTP_400_BAD_REQUEST)
        
        if not session_id:
            return Response({'error': 'ID de sesión requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        # Procesar mensaje de forma asíncrona
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(
                process_message_async(request.user, message, session_id)
            )
            loop.close()
            
            return Response(result)
            
        except Exception as e:
            return Response({
                'error': f'Error generando respuesta: {str(e)}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        return Response({
            'error': f'Error procesando solicitud: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_sessions(request):
    """
    📋 PROPÓSITO: API para obtener lista de sesiones del usuario
    """
    sessions = InterviewSession.objects.filter(user=request.user)
    
    sessions_data = []
    for session in sessions:
        sessions_data.append({
            'id': session.id,
            'title': session.title,
            'session_type': session.session_type,
            'created_at': session.created_at.isoformat(),
            'message_count': session.messages.count()
        })
    
    return Response({'sessions': sessions_data})

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_session_messages(request, session_id):
    """
    💬 PROPÓSITO: API para obtener mensajes de una sesión específica
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    messages = session.messages.all()
    
    messages_data = []
    for message in messages:
        messages_data.append({
            'id': message.id,
            'is_user': message.is_user,
            'content': message.content,
            'timestamp': message.timestamp.isoformat()
        })
    
    return Response({
        'session': {
            'id': session.id,
            'title': session.title,
            'session_type': session.session_type,
        },
        'messages': messages_data
    })

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    """
    🗑️ PROPÓSITO: API para eliminar una sesión específica
    """
    try:
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        
        # Guardar información antes de eliminar
        session_title = session.title
        messages_count = session.messages.count()
        
        # Eliminar sesión (CASCADE eliminará mensajes automáticamente)
        session.delete()
        
        return Response({
            'success': True,
            'message': f'Sesión "{session_title}" eliminada exitosamente',
            'deleted_messages': messages_count
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error eliminando sesión: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def delete_sessions_bulk(request):
    """
    🗑️ PROPÓSITO: API para eliminar múltiples sesiones
    """
    try:
        session_ids = request.data.get('session_ids', [])
        
        if not session_ids:
            return Response({
                'success': False,
                'error': 'No se proporcionaron IDs de sesiones'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Filtrar solo las sesiones del usuario
        sessions = InterviewSession.objects.filter(
            id__in=session_ids, 
            user=request.user
        )
        
        deleted_count = sessions.count()
        total_messages = sum(session.messages.count() for session in sessions)
        
        # Eliminar sesiones
        sessions.delete()
        
        return Response({
            'success': True,
            'message': f'Se eliminaron {deleted_count} sesiones y {total_messages} mensajes',
            'deleted_sessions': deleted_count,
            'deleted_messages': total_messages
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error eliminando sesiones: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_all_sessions(request):
    """
    🗑️ PROPÓSITO: API para eliminar TODAS las sesiones del usuario
    """
    try:
        sessions = InterviewSession.objects.filter(user=request.user)
        total_sessions = sessions.count()
        total_messages = sum(session.messages.count() for session in sessions)
        
        # Eliminar todas las sesiones
        sessions.delete()
        
        return Response({
            'success': True,
            'message': f'Se eliminaron {total_sessions} sesiones y {total_messages} mensajes',
            'deleted_sessions': total_sessions,
            'deleted_messages': total_messages
        })
        
    except Exception as e:
        return Response({
            'success': False,
            'error': f'Error eliminando todas las sesiones: {str(e)}'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
