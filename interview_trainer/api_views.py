from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import InterviewSession, ChatMessage, UserProfile
from .services import GeminiService
import asyncio

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
        
        # La sesión debe existir (creada previamente en select_interview_type)
        if not session_id:
            return Response({'error': 'ID de sesión requerido'}, status=status.HTTP_400_BAD_REQUEST)
        
        session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
        
        # Guardar mensaje del usuario
        user_message = ChatMessage.objects.create(
            session=session,
            is_user=True,
            content=message
        )
        
        # Obtener historial de conversación
        conversation_history = []
        recent_messages = session.messages.order_by('timestamp')[:20]
        for msg in recent_messages:
            conversation_history.append({
                'is_user': msg.is_user,
                'content': msg.content
            })
        
        # ✅ Usar TU servicio centralizado (sin API key del usuario)
        gemini_service = GeminiService()
        
        try:
            # Generar respuesta
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ai_response = loop.run_until_complete(
                gemini_service.generate_response(
                    message=message,
                    conversation_history=conversation_history[:-1],
                    interview_type=session.session_type
                )
            )
            loop.close()
            
            # Guardar respuesta de IA
            ai_message = ChatMessage.objects.create(
                session=session,
                is_user=False,
                content=ai_response
            )
            
            # Actualizar contador
            profile, created = UserProfile.objects.get_or_create(user=request.user)
            profile.total_sessions = InterviewSession.objects.filter(user=request.user).count()
            profile.save()
            
            return Response({
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
                }
            })
            
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
