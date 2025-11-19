import logging
import profile
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, update_session_auth_hash
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib import messages
from urllib3 import request
from .models import InterviewSession, ChatMessage, UserProfile
from django.http import JsonResponse
from .services import GeminiService
import asyncio

logger = logging.getLogger(__name__)
gemini_service = GeminiService()

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
    + Ahora: puede generar respuesta de IA + audio TTS para esa sesión
    """
    session = get_object_or_404(InterviewSession, id=session_id, user=request.user)
    
    reply_text = None
    audio_url = None
    user_message = None

    try:
        # 🧍‍♂️ 1. Obtener o crear perfil
        profile, created = UserProfile.objects.get_or_create(user=request.user)
        
        # 📋 2. Obtener sesiones del usuario para el sidebar
        sessions = InterviewSession.objects.filter(user=request.user)[:10]

        # 💬 3. Si viene un POST, significa que el usuario envió un mensaje
        if request.method == "POST":
            user_message = request.POST.get("message", "").strip()

            if user_message:
                # (Opcional) aquí podrías construir un conversation_history real
                conversation_history = None  # por ahora lo dejamos así

                # 🧠 4. Llamar a Gemini para texto + audio
                # generate_response_with_tts es async, así que usamos asyncio.run
                result = asyncio.run(
                    gemini_service.generate_response_with_tts(
                        message=user_message,
                        conversation_history=conversation_history,
                        interview_type=session.interview_type if hasattr(session, "interview_type") else "operations",
                        voice_name="Leda",  # o la voz que quieras
                    )
                )

                reply_text = result.get("reply_text")
                audio_url = result.get("audio_url")

                # (Opcional) aquí podrías guardar el mensaje y la respuesta en la BD

        # 🎨 5. Armar el contexto para la plantilla
        context = {
            'profile': profile,
            'sessions': sessions,
            'current_session': session,
            'has_api_key': True,  # ✅ Siempre True porque usas TU API key

            # 🔊 Nuevos campos para el chat con voz:
            'user_message': user_message,
            'reply_text': reply_text,
            'audio_url': audio_url,
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
def profile_settings(request):
    """
    ⚙️ PROPÓSITO: Configuración del perfil del usuario
    📝 QUÉ HACE: Solo preferencias (ya no API key)
    """
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        # Preferencia existente
        preferred_type = request.POST.get('preferred_interview_type', 'general')
        profile.preferred_interview_type = preferred_type
        profile.save()

        # Manejo opcional de cambio de username / contraseña
        new_username = request.POST.get('username', '').strip()
        pw1 = request.POST.get('password1', '')
        pw2 = request.POST.get('password2', '')
        user = request.user
        changed = False

        # Cambiar username si se proporcionó y es distinto
        if new_username and new_username != user.username:
            if User.objects.filter(username=new_username).exclude(pk=user.pk).exists():
                messages.error(request, 'El nombre de usuario ya está en uso.')
                return redirect('interview_trainer:profile_settings')
            user.username = new_username
            changed = True

        # Cambiar contraseña si se proporcionó ambos campos
        if pw1 or pw2:
            if pw1 != pw2:
                messages.error(request, 'Las contraseñas no coinciden.')
                return redirect('interview_trainer:profile_settings')
            if len(pw1) < 6:
                messages.error(request, 'La contraseña debe tener al menos 6 caracteres.')
                return redirect('interview_trainer:profile_settings')
            user.set_password(pw1)
            changed = True

        if changed:
            user.save()
            # Mantener sesión si la contraseña cambió
            try:
                update_session_auth_hash(request, user)
            except Exception:
                pass

        messages.success(request, 'Configuración guardada exitosamente!')
        return redirect('interview_trainer:profile_settings')
    
    return render(request, 'interview_trainer/profile_settings.html', {'profile': profile})

@login_required
def progreso_view(request):
    """
    📈 PROPÓSITO: Página de progreso del usuario
    📝 QUÉ HACE: Muestra los charts de estadísticas del usuario
    """
    return render(request, 'interview_trainer/progreso.html')

@login_required
def progreso_data(request):
    """
    API: Devuelve datos de progreso del usuario para los charts
    """
    user = request.user
    from evaluation.models import FeedbackReport, CompetencyScore, CompetencyDefinition

    # Tomar las sesiones evaluadas más recientes (hasta 12 para una buena vista)
    sessions = InterviewSession.objects.filter(user=user).order_by('created_at')
    sessions = sessions.order_by('-created_at')[:12][::-1]  # ordenar cronológicamente asc

    # Series de evolución por sesión (usar feedback_report.average_score cuando exista)
    sessions_labels = []
    sessions_scores = []
    for s in sessions:
        sessions_labels.append(s.created_at.strftime('%d/%m/%Y'))
        feedback = getattr(s, 'feedback_report', None)
        if feedback and feedback.average_score is not None:
            sessions_scores.append(round(feedback.average_score, 2))
        else:
            # si no hay feedback, colocar None para que la gráfica muestre huecos
            sessions_scores.append(None)
    # Serie de puntajes de gestión del tiempo (por sesión)
    sessions_time_scores = []
    for s in sessions:
        feedback = getattr(s, 'feedback_report', None)
        if feedback and getattr(feedback, 'time_management_score', None) is not None:
            sessions_time_scores.append(round(feedback.time_management_score, 2))
        else:
            sessions_time_scores.append(None)

    # Puntaje promedio calculado sobre feedbacks existentes
    feedbacks = FeedbackReport.objects.filter(session__user=user).order_by('-generated_at')[:50]
    scores = [f.average_score for f in feedbacks if f.average_score is not None]
    average_score = round(sum(scores) / len(scores), 2) if scores else 0
    # Promedio de gestión de tiempo global
    time_scores = [f.time_management_score for f in feedbacks if f.time_management_score is not None]
    average_time_score = round(sum(time_scores) / len(time_scores), 2) if time_scores else 0

    # Competencias: obtener definiciones activas y construir series por cada competencia
    competencies = list(CompetencyDefinition.get_default_competencies())
    skills_labels = [c.name for c in competencies]
    skills_series = {c.name: [] for c in competencies}

    # Para cada sesión, calcular el puntaje promedio por competencia (1-10). Si falta, None.
    for s in sessions:
        for comp in competencies:
            comp_scores = CompetencyScore.objects.filter(session=s, competency_name=comp.name)
            if comp_scores.exists():
                avg = round(sum(cs.score for cs in comp_scores) / comp_scores.count(), 2)
                skills_series[comp.name].append(avg)
            else:
                skills_series[comp.name].append(None)

    # Construir serie acumulada (running average) por competencia
    skills_series_cumulative = {}
    for name, series in skills_series.items():
        cum = []
        ssum = 0.0
        scount = 0
        for v in series:
            if v is not None:
                ssum += v
                scount += 1
                cum.append(round(ssum / scount, 2))
            else:
                # mantener None hasta que haya al menos un valor
                cum.append(None if scount == 0 else round(ssum / scount, 2))
        skills_series_cumulative[name] = cum

    return JsonResponse({
        'average_score': average_score,
        'average_time_score': average_time_score,
        'sessions_labels': sessions_labels,
        'sessions_scores': sessions_scores,
        'sessions_time_scores': sessions_time_scores,
        'skills_labels': skills_labels,
        'skills_series': skills_series,
        'skills_series_cumulative': skills_series_cumulative,
    })

async def chat_tts_page(request):
    if request.method == "POST":
        message = request.POST.get("message")
        result = await gemini_service.generate_response_with_tts(message)
        return render(request, "interview_trainer/chat.html", {
            "reply_text": result["reply_text"],
            "audio_url": result["audio_url"],
        })

    return render(request, "interview_trainer/chat.html")
