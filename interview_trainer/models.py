from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from django.apps import apps
from datetime import timedelta

class InterviewSession(models.Model):
    """
    🎯 PROPÓSITO: Almacena cada sesión de entrenamiento de entrevista
    📝 QUÉ HACE: Guarda información básica de cada conversación
    """
    INTERVIEW_TYPES = [
        ('operations', 'Operaciones y Producción'),
        ('sales_marketing', 'Ventas y Marketing'),
        ('finance', 'Finanzas y Administración'),
        ('hr', 'Recursos Humanos (Talento Humano)'),
        ('it', 'Tecnología de la Información (TI / IT)'),
        ('rd', 'Investigación y Desarrollo (I+D)'),
        ('customer_support', 'Atención al Cliente y Soporte'),
        ('management', 'Dirección General y Estratégica'),
        ('health', 'Salud y Medicina'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ¿De quién es la sesión?
    session_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES)  # ¿Qué tipo de entrevista?
    title = models.CharField(max_length=200)  # Título descriptivo
    created_at = models.DateTimeField(default=timezone.now)  # ¿Cuándo se creó?
    updated_at = models.DateTimeField(auto_now=True)  # ¿Cuándo se actualizó?
    is_active = models.BooleanField(default=True)  # ¿Está activa?
    is_completed = models.BooleanField(default=False)  # ¿Ya completó las 7 preguntas?
    questions_asked = models.IntegerField(default=0)  # Contador de preguntas realizadas por Lumo
    # ---- Time management fields (15 minutes default = 900 seconds) ----
    start_time = models.DateTimeField(null=True, blank=True)
    end_time = models.DateTimeField(null=True, blank=True)
    total_time_allowed = models.IntegerField(default=900, help_text='Tiempo total permitido en segundos')
    total_time_used = models.IntegerField(default=0, help_text='Tiempo utilizado acumulado en segundos')
    is_paused = models.BooleanField(default=False)
    # Internal helper to track when the timer was last (re)started/resumed
    last_resume_time = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']  # Más recientes primero
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

    # ---------------- Timer control helpers ----------------
    def start_timer(self):
        """
        Inicia el cronómetro de la sesión. Resetea el tiempo usado y establece start_time.
        """
        now = timezone.now()
        self.start_time = now
        self.last_resume_time = now
        self.end_time = None
        self.total_time_used = 0
        self.is_paused = False
        self.save(update_fields=['start_time', 'last_resume_time', 'end_time', 'total_time_used', 'is_paused'])

    def pause_timer(self):
        """
        Pausa el cronómetro: acumula el tiempo desde la última reanudación hasta ahora.
        """
        if self.is_paused:
            return
        if not self.last_resume_time:
            # Nothing to accumulate
            self.is_paused = True
            self.save(update_fields=['is_paused'])
            return
        now = timezone.now()
        elapsed = now - self.last_resume_time
        # acumulamos segundos
        self.total_time_used += int(elapsed.total_seconds())
        self.last_resume_time = None
        self.is_paused = True
        self.save(update_fields=['total_time_used', 'last_resume_time', 'is_paused'])

    def resume_timer(self):
        """
        Reanuda el cronómetro desde el momento actual.
        """
        if not self.is_paused and self.last_resume_time:
            return
        now = timezone.now()
        self.last_resume_time = now
        self.is_paused = False
        self.save(update_fields=['last_resume_time', 'is_paused'])

    def finish_timer(self, interrupted=False):
        """
        Finaliza el cronómetro. Calcula el total_time_used, fija end_time e intenta crear/actualizar
        el FeedbackReport asociado con la evaluación de gestión del tiempo.

        Si `interrupted` es True, la evaluación de tiempo se deshabilita (según requisito).
        """
        now = timezone.now()
        # Si está corriendo, acumulamos el tiempo desde la última reanudación
        if not self.is_paused and self.last_resume_time:
            elapsed = now - self.last_resume_time
            self.total_time_used += int(elapsed.total_seconds())
            self.last_resume_time = None

        self.end_time = now
        self.is_paused = False
        self.is_completed = True
        # Guardar campos básicos del temporizador
        self.save(update_fields=['total_time_used', 'last_resume_time', 'end_time', 'is_paused', 'is_completed'])

        # Crear o actualizar la evaluación (FeedbackReport) asociada
        try:
            FeedbackReport = apps.get_model('evaluation', 'FeedbackReport')
        except LookupError:
            # Si el app registry no tiene el modelo (por ejemplo en migrations), no hacemos nada
            return

        # preparar valores básicos para el reporte
        session_minutes = int(round(self.total_time_used / 60.0))

        feedback_report, created = FeedbackReport.objects.get_or_create(
            session=self,
            defaults={
                'overall_feedback': '',
                'average_score': 0.0,
                'performance_level': '',
                'session_duration_minutes': session_minutes,
            }
        )

        # Si la entrevista fue interrumpida, desactivar evaluación de tiempo
        if interrupted:
            feedback_report.time_evaluation_enabled = False
            feedback_report.time_management_score = None
            feedback_report.feedback_time = 'Evaluación de tiempo deshabilitada por interrupción de la entrevista.'
        else:
            # Llamamos a la función que calcula la evaluación de gestión del tiempo
            try:
                # Import local para evitar importaciones circulares al importar evaluation.views en nivel módulo
                from evaluation.views import evaluate_time_management
                feedback_text, score = evaluate_time_management(self)
                feedback_report.time_evaluation_enabled = True
                feedback_report.time_management_score = score
                feedback_report.feedback_time = feedback_text
            except Exception:
                # Si falla la evaluación, dejar marcado como no habilitado
                feedback_report.time_evaluation_enabled = False
                feedback_report.time_management_score = None
                feedback_report.feedback_time = 'No fue posible calcular la evaluación de tiempo.'

        feedback_report.session_duration_minutes = session_minutes
        feedback_report.generated_at = now
        feedback_report.save()

class ChatMessage(models.Model):
    """
    💬 PROPÓSITO: Almacena cada mensaje individual del chat
    📝 QUÉ HACE: Guarda tanto mensajes del usuario como respuestas de la IA
    """
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='messages')
    is_user = models.BooleanField(default=True)  # True = usuario, False = IA
    content = models.TextField()  # El texto del mensaje
    timestamp = models.DateTimeField(default=timezone.now)  # ¿Cuándo se envió?
    # Archivo de audio TTS asociado (opcional)
    audio_file = models.FileField(upload_to='chat_audio/', null=True, blank=True)
    # Nombre de la voz utilizada para TTS (opcional)
    tts_voice = models.CharField(max_length=100, null=True, blank=True)
    
    class Meta:
        ordering = ['timestamp']  # Cronológico
    
    def __str__(self):
        sender = "Usuario" if self.is_user else "IA"
        audio_marker = " [audio]" if self.audio_file else ""
        return f"{sender}: {self.content[:50]}...{audio_marker}"

# class CompetencyScore(models.Model):
#     """
#     📊 PROPÓSITO: Almacena puntajes detallados por competencia
#     📝 QUÉ HACE: Guarda evaluación específica de cada habilidad evaluada
#     """
#     session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='scores')
#     competency = models.CharField(max_length=50)  # 'comunicacion', 'pensamiento_critico', etc.
#     score = models.IntegerField()  # Puntaje 1-10
#     feedback = models.TextField()  # Comentarios específicos de la competencia
    
#     class Meta:
#         unique_together = ['session', 'competency']  # Una sola evaluación por competencia por sesión
    
#     def __str__(self):
#         return f"{self.session.user.username} - {self.competency}: {self.score}/10"

class UserProfile(models.Model):
    """
    👤 PROPÓSITO: Información adicional del usuario
    📝 QUÉ HACE: Guarda preferencias y estadísticas (YA NO API KEY)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_interview_type = models.CharField(max_length=20, choices=InterviewSession.INTERVIEW_TYPES, default='operations')
    total_sessions = models.IntegerField(default=0)  # Contador de sesiones
    # ❌ REMOVIDO: gemini_api_key (ya no es necesario)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
