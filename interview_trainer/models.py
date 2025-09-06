from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

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
    is_completed = models.BooleanField(default=False)  # ¿Ya completó las 10 preguntas?
    questions_asked = models.IntegerField(default=0)  # Contador de preguntas realizadas por Lumo
    
    class Meta:
        ordering = ['-created_at']  # Más recientes primero
    
    def __str__(self):
        return f"{self.user.username} - {self.title}"

class ChatMessage(models.Model):
    """
    💬 PROPÓSITO: Almacena cada mensaje individual del chat
    📝 QUÉ HACE: Guarda tanto mensajes del usuario como respuestas de la IA
    """
    session = models.ForeignKey(InterviewSession, on_delete=models.CASCADE, related_name='messages')
    is_user = models.BooleanField(default=True)  # True = usuario, False = IA
    content = models.TextField()  # El texto del mensaje
    timestamp = models.DateTimeField(default=timezone.now)  # ¿Cuándo se envió?
    
    class Meta:
        ordering = ['timestamp']  # Cronológico
    
    def __str__(self):
        sender = "Usuario" if self.is_user else "IA"
        return f"{sender}: {self.content[:50]}..."

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
