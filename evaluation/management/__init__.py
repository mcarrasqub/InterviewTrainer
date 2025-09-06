from django.core.management.base import BaseCommand
from interview_trainer.models import InterviewSession
from evaluation.services import EvaluationService
import asyncio

class Command(BaseCommand):
    help = 'Prueba el sistema de evaluación'

    def add_arguments(self, parser):
        parser.add_argument('--session-id', type=int, help='ID de la sesión para evaluar')

    def handle(self, *args, **options):
        session_id = options.get('session_id')
        
        if not session_id:
            # Mostrar sesiones disponibles para evaluación
            sessions = InterviewSession.objects.all().order_by('-created_at')[:10]
            
            self.stdout.write("📊 ANÁLISIS DE SESIONES PARA EVALUACIÓN:\n")
            
            evaluation_service = EvaluationService()
            
            for session in sessions:
                can_eval = evaluation_service.can_generate_evaluation(session)
                
                messages = session.messages.all()
                user_msgs = messages.filter(is_user=True).count()
                ai_msgs = messages.filter(is_user=False).count()
                
                status = "✅ EVALUABLE" if can_eval['can_generate'] else "❌ NO LISTO"
                has_evaluation = "📊 EVALUADO" if hasattr(session, 'feedback_report') and session.feedback_report else "📝 SIN EVALUAR"
                
                self.stdout.write(
                    f"ID: {session.id:2d} | {status} | {has_evaluation} | "
                    f"Msgs: {messages.count():2d} (👤{user_msgs:2d} 🤖{ai_msgs:2d}) | "
                    f"Preguntas: {can_eval['questions_count']:2d}/10 | "
                    f"Respuestas: {can_eval['user_responses']:2d}/9 | "
                    f"Usuario: {session.user.username}"
                )
                self.stdout.write(f"     Razón: {can_eval['reason']}\n")
            
            self.stdout.write("💡 Uso: python manage.py test_evaluation --session-id <ID>")
            return
        
        # Evaluar sesión específica
        try:
            session = InterviewSession.objects.get(id=session_id)
            evaluation_service = EvaluationService()
            
            self.stdout.write(f"🎯 EVALUANDO SESIÓN {session_id}")
            self.stdout.write(f"   Usuario: {session.user.username}")
            self.stdout.write(f"   Tipo: {session.get_session_type_display()}")
            
            # Verificar si se puede evaluar
            can_eval = evaluation_service.can_generate_evaluation(session)
            self.stdout.write(f"   Estado: {can_eval['reason']}")
            
            if not can_eval['can_generate']:
                if can_eval.get('existing'):
                    self.stdout.write("📊 MOSTRANDO EVALUACIÓN EXISTENTE:")
                    report = session.feedback_report
                    self.stdout.write(f"   Puntaje promedio: {report.average_score:.1f}/10")
                    self.stdout.write(f"   Nivel: {report.performance_level}")
                    self.stdout.write(f"   Feedback: {report.overall_feedback[:100]}...")
                else:
                    self.stdout.write("❌ No se puede evaluar esta sesión aún")
                return
            
            # Generar evaluación
            self.stdout.write("🔄 Generando evaluación...")
            
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(
                    evaluation_service.generate_session_evaluation(session)
                )
                loop.close()
                
                self.stdout.write("✅ EVALUACIÓN COMPLETADA:")
                self.stdout.write(f"   📊 Puntaje promedio: {result['average_score']:.1f}/10")
                self.stdout.write(f"   🏆 Nivel de rendimiento: {result['performance_level']}")
                self.stdout.write(f"   ⏱️  Duración: {result['session_duration']} min")
                self.stdout.write(f"   💬 Feedback general: {result['overall_feedback'][:150]}...")
                
                self.stdout.write("\n📈 PUNTAJES POR COMPETENCIA:")
                for comp_name, score_data in result['competency_scores'].items():
                    self.stdout.write(f"   • {comp_name}: {score_data['score']}/10")
                    self.stdout.write(f"     {score_data['feedback']}")
                
            except Exception as e:
                self.stdout.write(f"❌ Error generando evaluación: {str(e)}")
                
        except InterviewSession.DoesNotExist:
            self.stdout.write(f"❌ Sesión {session_id} no encontrada")
