from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class InterviewSession(models.Model):
    """
    🎯 PROPÓSITO: Almacena cada sesión de entrenamiento de entrevista
    📝 QUÉ HACE: Guarda información básica de cada conversación
    """
    INTERVIEW_TYPES = [
        ('technical', 'Técnica'),
        ('behavioral', 'Comportamental'),
        ('simulation', 'Simulación Completa'),
        ('general', 'General'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)  # ¿De quién es la sesión?
    session_type = models.CharField(max_length=20, choices=INTERVIEW_TYPES)  # ¿Qué tipo de entrevista?
    title = models.CharField(max_length=200)  # Título descriptivo
    created_at = models.DateTimeField(default=timezone.now)  # ¿Cuándo se creó?
    updated_at = models.DateTimeField(auto_now=True)  # ¿Cuándo se actualizó?
    is_active = models.BooleanField(default=True)  # ¿Está activa?
    
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

class UserProfile(models.Model):
    """
    👤 PROPÓSITO: Información adicional del usuario
    📝 QUÉ HACE: Guarda preferencias y estadísticas (YA NO API KEY)
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    preferred_interview_type = models.CharField(max_length=20, choices=InterviewSession.INTERVIEW_TYPES, default='general')
    total_sessions = models.IntegerField(default=0)  # Contador de sesiones
    # ❌ REMOVIDO: gemini_api_key (ya no es necesario)
    created_at = models.DateTimeField(default=timezone.now)
    
    def __str__(self):
        return f"Perfil de {self.user.username}"
