import logging
import profile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from urllib3 import request
from .models import InterviewSession, ChatMessage, UserProfile

logger = logging.getLogger(__name__)

def home(request):
    """
    🏠 PROPÓSITO: Página de inicio/landing
    📝 QUÉ HACE: Muestra información sobre Lumo y botones de registro/login
    """
    return render(request, 'interview_trainer/home.html')

def register(request):
    """
    📝 PROPÓSITO: Registro de nuevos usuarios
    📝 QUÉ HACE: Crea cuenta nueva y perfil automáticamente
    """
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                # ✅ Crear perfil automáticamente (sin API key)
                UserProfile.objects.get_or_create(user=user)
                login(request, user)
                messages.success(request, '¡Cuenta creada exitosamente!')
                return redirect('interview_trainer:home')
            except Exception as e:
                messages.error(request, f'Error creando la cuenta: {str(e)}')
        else:
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f'{field}: {error}')
    else:
        form = UserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@login_required
def select_interview_type(request):
    """
    🎭 PROPÓSITO: Selección del tipo de entrevista antes de iniciar
    📝 QUÉ HACE: Permite elegir el rol del entrevistador
    """
    if request.method == 'POST':
        interview_type = request.POST.get('interview_type', 'operations')
        session_title = request.POST.get('session_title', f'Sesión {interview_type}')
        
        # Crear nueva sesión con el tipo seleccionado
        session = InterviewSession.objects.create(
            user=request.user,
            session_type=interview_type,
            title=session_title
        )
        
        # 🎯 GENERAR MENSAJE INICIAL DE LUMO AUTOMÁTICAMENTE
        try:
            from .services import GeminiService
            import asyncio
            
            gemini_service = GeminiService()
            
            # ✅ USAR EL MÉTODO DEL SERVICIO
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            initial_message = loop.run_until_complete(
                gemini_service.generate_initial_welcome(interview_type)
            )
            loop.close()
            
            # Guardar el mensaje inicial de Lumo
            ChatMessage.objects.create(
                session=session,
                is_user=False,  # Es mensaje de la IA
                content=initial_message
            )
            
            logger.info(f"Mensaje inicial generado para sesión {session.id}")
            messages.success(request, f'¡Sesión {session.get_session_type_display()} iniciada!')
            
        except Exception as e:
            # Si falla, usar mensaje de respaldo específico
            department_names = {
                'operations': 'Operaciones y Producción',
                'sales_marketing': 'Ventas y Marketing',
                'finance': 'Finanzas y Administración',
                'hr': 'Recursos Humanos (Talento Humano)',
                'it': 'Tecnología de la Información (TI / IT)',
                'rd': 'Investigación y Desarrollo (I+D)',
                'customer_support': 'Atención al Cliente y Soporte',
                'management': 'Dirección General y Estratégica',
                'health': 'Salud y Medicina'
            }
            
            dept_name = department_names.get(interview_type, 'Operaciones y Producción')
            fallback_message = f"¡Hola! 👋 Soy Lumo, tu entrevistador especializado en {dept_name}. Me da mucho gusto conocerte y estoy emocionado de conocer más sobre tu experiencia profesional. Para comenzar, ¿podrías contarme un poco sobre ti y qué te motiva a aplicar para una posición en {dept_name}?"
            
            ChatMessage.objects.create(
                session=session,
                is_user=False,
                content=fallback_message
            )
            logger.error(f"Error generando mensaje inicial: {str(e)}")
        
        return redirect('interview_trainer:chat_session', session_id=session.id)
    
    # Obtener perfil para sugerencias
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    context = {
        'profile': profile,
        'interview_types': InterviewSession.INTERVIEW_TYPES
    }
    return render(request, 'interview_trainer/select_type.html', context)

@login_required
def chat_session(request, session_id):
    """
    💬 PROPÓSITO: Chat de una sesión específica
    📝 QUÉ HACE: Muestra interfaz de chat para una sesión ya creada
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    
    try:
        # Obtener o crear perfil
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Obtener sesiones del usuario para el sidebar
        sessions = InterviewSession.objects.filter(user=request.user)[:10]
        
        context = {
            'profile': profile,
            'sessions': sessions,
            'current_session': session,
            'has_api_key': True,  # ✅ Siempre True porque usas TU API key
        }
        return render(request, 'interview_trainer/chat.html', context)
    except Exception as e:
        messages.error(request, f'Error accediendo al chat: {str(e)}')
        return redirect('interview_trainer:home')

@login_required
def chat(request):
    """
    💬 PROPÓSITO: Vista principal del chat - redirige a selección
    📝 QUÉ HACE: Redirige a la selección de tipo de entrevista
    """
    try:
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        sessions = InterviewSession.objects.filter(user=request.user)[:10]
        context = {
            'profile': profile,
            'sessions': sessions,
            'current_session': None,
            'has_api_key': True,
        }
        return render(request, 'interview_trainer/chat.html', context)
    except Exception as e:
        messages.error(request, f'Error accediendo al chat: {str(e)}')
        return redirect('interview_trainer:home')

@login_required
def session_detail(request, session_id):
    """
    📊 PROPÓSITO: Ver detalles de una sesión específica
    📝 QUÉ HACE: Muestra historial completo de una conversación
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    messages_list = session.messages.all()
    
    # Calcular estadísticas
    user_messages_count = messages_list.filter(is_user=True).count()
    ai_messages_count = messages_list.filter(is_user=False).count()
    
    # Calcular duración
    if messages_list.exists():
        first_message = messages_list.first()
        last_message = messages_list.last()
        duration = last_message.timestamp - first_message.timestamp
        session_duration = f"{duration.seconds // 60} min"
    else:
        session_duration = "0 min"
    
    # Verificar si existe evaluación
    has_evaluation = hasattr(session, 'feedback_report')
    
    context = {
        'session': session,
        'messages': messages_list,
        'user_messages_count': user_messages_count,
        'ai_messages_count': ai_messages_count,
        'session_duration': session_duration,
        'has_evaluation': has_evaluation,
    }
    return render(request, 'interview_trainer/session_detail.html', context)

@login_required
def profile_settings(request):
    """
    ⚙️ PROPÓSITO: Configuración del perfil del usuario
    📝 QUÉ HACE: Solo preferencias (ya no API key)
    """
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        preferred_type = request.POST.get('preferred_interview_type', 'general')
        profile.preferred_interview_type = preferred_type
        profile.save()
        
        messages.success(request, 'Configuración guardada exitosamente!')
        return redirect('interview_trainer:profile_settings')
    
    return render(request, 'interview_trainer/profile_settings.html', {'profile': profile})
