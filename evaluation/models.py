from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class CompetencyScore(models.Model):
    """
    📊 PROPÓSITO: Puntajes detallados por competencia
    📝 QUÉ HACE: Almacena evaluación específica de cada competencia
    """
    session = models.ForeignKey('interview_trainer.InterviewSession', on_delete=models.CASCADE, related_name='competency_scores')
    competency_name = models.CharField(max_length=100)
    score = models.IntegerField()  # 1-10
    feedback = models.TextField()

    
    class Meta:
        unique_together = ['session', 'competency_name']
        verbose_name = "Puntaje de Competencia"
        verbose_name_plural = "Puntajes de Competencias"
    
    def __str__(self):
        return f"{self.session.user.username} - {self.competency_name}: {self.score}/10"

class FeedbackReport(models.Model):
    """
    📋 PROPÓSITO: Reporte completo de evaluación
    📝 QUÉ HACE: Almacena el feedback general y métricas de la sesión
    """
    session = models.OneToOneField('interview_trainer.InterviewSession', on_delete=models.CASCADE, related_name='feedback_report')
    overall_feedback = models.TextField()
    average_score = models.FloatField()
    performance_level = models.CharField(max_length=50)  # Excelente, Bueno, etc.
    session_duration_minutes = models.IntegerField(default=0)
    generated_at = models.DateTimeField(default=timezone.now)
    is_final = models.BooleanField(default=True)
    
    class Meta:
        verbose_name = "Reporte de Feedback"
        verbose_name_plural = "Reportes de Feedback"
        ordering = ['-generated_at']
    
    def __str__(self):
        return f"Feedback: {self.session.title} - {self.average_score:.1f}/10"
    
    def get_performance_color_class(self):
        """
        🎨 PROPÓSITO: Retorna clase CSS según el nivel de performance
        """
        if self.average_score >= 8.0:
            return "success"
        elif self.average_score >= 6.0:
            return "info"
        elif self.average_score >= 4.0:
            return "warning"
        else:
            return "danger"

class UserAnalytics(models.Model):
    """
    📈 PROPÓSITO: Analytics y progreso del usuario
    📝 QUÉ HACE: Mantiene estadísticas históricas del desempeño
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='analytics')
    total_sessions_evaluated = models.IntegerField(default=0)
    average_overall_score = models.FloatField(default=0)
    strongest_competency = models.CharField(max_length=100, blank=True)
    weakest_competency = models.CharField(max_length=100, blank=True)
    total_questions_answered = models.IntegerField(default=0)
    total_session_time_minutes = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "Analytics de Usuario"
        verbose_name_plural = "Analytics de Usuarios"
    
    def __str__(self):
        return f"Analytics: {self.user.username} - {self.average_overall_score:.1f}/10"
    
    def get_performance_trend(self):
        """
        📊 PROPÓSITO: Retorna tendencia de progreso (mejorando/estable/bajando)
        """
        reports = FeedbackReport.objects.filter(
            session__user=self.user
        ).order_by('-generated_at')[:5]
        
        if reports.count() < 2:
            return "insuficiente"
        
        recent_avg = sum(r.average_score for r in reports[:2]) / 2
        older_avg = sum(r.average_score for r in reports[2:]) / max(1, reports.count() - 2)
        
        if recent_avg > older_avg + 0.5:
            return "mejorando"
        elif recent_avg < older_avg - 0.5:
            return "bajando"
        else:
            return "estable"

class CompetencyDefinition(models.Model):
    """
    📖 PROPÓSITO: Definiciones y criterios de evaluación para cada competencia
    📝 QUÉ HACE: Mantiene la información estándar de cada competencia
    """
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    evaluation_criteria = models.TextField()
    icon = models.CharField(max_length=50, default="⭐")
    is_active = models.BooleanField(default=True)
    order = models.IntegerField(default=0)
    
    class Meta:
        verbose_name = "Definición de Competencia"
        verbose_name_plural = "Definiciones de Competencias"
        ordering = ['order', 'name']
    
    def __str__(self):
        return f"{self.icon} {self.name}"
    
    @classmethod
    def get_default_competencies(cls):
        """
        🎯 PROPÓSITO: Retorna las competencias por defecto
        """
        defaults = [
            {
                'name': 'Comunicación',
                'description': 'Capacidad de expresar ideas de forma clara y efectiva',
                'evaluation_criteria': 'Claridad, estructura, capacidad de expresar ideas',
                'icon': '🗣️',
                'order': 1
            },
            {
                'name': 'Pensamiento crítico',
                'description': 'Habilidad para analizar problemas y encontrar soluciones',
                'evaluation_criteria': 'Análisis, lógica, resolución de problemas',
                'icon': '🧠',
                'order': 2
            },
            {
                'name': 'Adaptabilidad',
                'description': 'Flexibilidad ante cambios y nuevas situaciones',
                'evaluation_criteria': 'Flexibilidad, manejo de cambios, aprendizaje',
                'icon': '🔄',
                'order': 3
            },
            {
                'name': 'Trabajo en equipo',
                'description': 'Capacidad de colaborar efectivamente con otros',
                'evaluation_criteria': 'Colaboración, liderazgo, habilidades interpersonales',
                'icon': '👥',
                'order': 4
            },
            {
                'name': 'Inteligencia emocional',
                'description': 'Manejo de emociones propias y de otros',
                'evaluation_criteria': 'Autoconocimiento, empatía, manejo de emociones',
                'icon': '❤️',
                'order': 5
            }
        ]
        
        for competency_data in defaults:
            cls.objects.get_or_create(
                name=competency_data['name'],
                defaults=competency_data
            )
        
        return cls.objects.filter(is_active=True).order_by('order')
