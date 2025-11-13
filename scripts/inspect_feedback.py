import os
import sys
import django

# Asegurar que la raíz del proyecto esté en sys.path. Cuando se ejecuta
# un script dentro de `scripts/`, Python pone ese directorio en sys.path[0],
# por lo que el paquete `lumo_project` (en el padre) no es importable por
# defecto. Añadimos la carpeta padre al path.
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lumo_project.settings')
django.setup()
from interview_trainer.models import InterviewSession
from evaluation.models import FeedbackReport

sessions = InterviewSession.objects.all().order_by('-created_at')[:20]
print('Checked', sessions.count(), 'sessions')
for s in sessions:
    print('---')
    print('Session id:', s.id, 'title:', s.title, 'user:', s.user.username)
    fr = getattr(s, 'feedback_report', None)
    if not fr:
        print('  No FeedbackReport')
    else:
        print('  FeedbackReport id:', fr.id)
        print('   time_evaluation_enabled:', fr.time_evaluation_enabled)
        print('   time_management_score:', repr(fr.time_management_score))
        print('   feedback_time:', repr(fr.feedback_time))
        print('   session_duration_minutes:', fr.session_duration_minutes)
        print('   average_score:', fr.average_score)
        print('   overall_feedback length:', len(fr.overall_feedback or ''))
