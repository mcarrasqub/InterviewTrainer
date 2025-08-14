from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from .models import InterviewSession, ChatMessage, UserProfile

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
                return redirect('chat')
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
def chat(request):
    """
    💬 PROPÓSITO: Página principal del chat
    📝 QUÉ HACE: Muestra interfaz de chat y sesiones anteriores
    ✅ CAMBIO: Ya no verifica API key del usuario
    """
    try:
        # Obtener o crear perfil
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # Obtener sesiones del usuario
        sessions = InterviewSession.objects.filter(user=request.user)[:10]
        
        context = {
            'profile': profile,
            'sessions': sessions,
            'has_api_key': True,  # ✅ Siempre True porque usas TU API key
        }
        return render(request, 'interview_trainer/chat.html', context)
    except Exception as e:
        messages.error(request, f'Error accediendo al chat: {str(e)}')
        return redirect('home')

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
    
    context = {
        'session': session,
        'messages': messages_list,
        'user_messages_count': user_messages_count,
        'ai_messages_count': ai_messages_count,
        'session_duration': session_duration,
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
        return redirect('profile_settings')
    
    return render(request, 'interview_trainer/profile_settings.html', {'profile': profile})
