#!/usr/bin/env python3
"""
Herramienta de diagnóstico rápida para verificar las puntuaciones de gestión de tiempo.

Ejemplo de uso:
  python scripts\check_time_scores.py --username sgallo
  python scripts\check_time_scores.py --username sgallo --session 8

El script imprime JSON similar a lo que devuelve `progreso_data` y lista los
`FeedbackReport` del usuario con `time_management_score` y `feedback_time`.
"""
import os
import sys
import json
import argparse

# Ajustar path para que el paquete lumo_project sea importable
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'lumo_project.settings')
import django
django.setup()

from django.contrib.auth.models import User
from interview_trainer.models import InterviewSession
from evaluation.models import FeedbackReport, CompetencyScore, CompetencyDefinition
from django.db.models import Avg


def build_progreso_data(user):
    sessions = InterviewSession.objects.filter(user=user).order_by('created_at')
    sessions = sessions.order_by('-created_at')[:12][::-1]

    sessions_labels = []
    sessions_scores = []
    sessions_time_scores = []

    for s in sessions:
        sessions_labels.append(s.created_at.strftime('%d/%m/%Y'))
        feedback = getattr(s, 'feedback_report', None)
        if feedback and feedback.average_score is not None:
            sessions_scores.append(round(feedback.average_score, 2))
        else:
            sessions_scores.append(None)

        if feedback and getattr(feedback, 'time_management_score', None) is not None:
            sessions_time_scores.append(round(feedback.time_management_score, 2))
        else:
            sessions_time_scores.append(None)

    # Global averages
    feedbacks = FeedbackReport.objects.filter(session__user=user).order_by('-generated_at')[:50]
    scores = [f.average_score for f in feedbacks if f.average_score is not None]
    average_score = round(sum(scores) / len(scores), 2) if scores else 0
    time_scores = [f.time_management_score for f in feedbacks if f.time_management_score is not None]
    average_time_score = round(sum(time_scores) / len(time_scores), 2) if time_scores else None

    # competencies series (simplified)
    competencies = list(CompetencyDefinition.get_default_competencies())
    skills_series = {c.name: [] for c in competencies}

    for s in sessions:
        for comp in competencies:
            comp_scores = CompetencyScore.objects.filter(session=s, competency_name=comp.name)
            if comp_scores.exists():
                avg = round(sum(cs.score for cs in comp_scores) / comp_scores.count(), 2)
                skills_series[comp.name].append(avg)
            else:
                skills_series[comp.name].append(None)

    # cumulative
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
                cum.append(None if scount == 0 else round(ssum / scount, 2))
        skills_series_cumulative[name] = cum

    return {
        'average_score': average_score,
        'average_time_score': average_time_score,
        'sessions_labels': sessions_labels,
        'sessions_scores': sessions_scores,
        'sessions_time_scores': sessions_time_scores,
        'skills_labels': [c.name for c in competencies],
        'skills_series': skills_series,
        'skills_series_cumulative': skills_series_cumulative,
    }


def list_feedback_reports(user):
    qs = FeedbackReport.objects.filter(session__user=user).order_by('-generated_at')
    out = []
    for f in qs:
        out.append({
            'id': f.id,
            'session_id': f.session.id,
            'generated_at': f.generated_at.isoformat(),
            'average_score': f.average_score,
            'time_evaluation_enabled': f.time_evaluation_enabled,
            'time_management_score': f.time_management_score,
            'feedback_time_preview': (f.feedback_time or '')[:200]
        })
    return out


def show_session_detail(session):
    print(f"Session {session.id} - {session.title}")
    print('  total_time_allowed:', session.total_time_allowed)
    print('  total_time_used:', session.total_time_used)
    fr = getattr(session, 'feedback_report', None)
    if fr:
        print('  feedback id:', fr.id)
        print('   time_management_score:', fr.time_management_score)
        print('   feedback_time (preview):', (fr.feedback_time or '')[:300])
    else:
        print('  No FeedbackReport for this session')


def main():
    parser = argparse.ArgumentParser(description='Check time management scores and progreso data for a user')
    parser.add_argument('--username', '-u', required=True, help='Username to inspect')
    parser.add_argument('--session', '-s', type=int, help='Show details for a specific session id')
    args = parser.parse_args()

    try:
        user = User.objects.get(username=args.username)
    except User.DoesNotExist:
        print('User not found:', args.username)
        sys.exit(2)

    data = build_progreso_data(user)
    print('\n== progreso_data JSON ==')
    print(json.dumps(data, indent=2, ensure_ascii=False))

    print('\n== FeedbackReport list ==')
    reports = list_feedback_reports(user)
    print(json.dumps(reports, indent=2, ensure_ascii=False))

    if args.session:
        try:
            s = InterviewSession.objects.get(id=args.session, user=user)
            print('\n== Session detail ==')
            show_session_detail(s)
        except InterviewSession.DoesNotExist:
            print('Session not found or not owned by user:', args.session)


if __name__ == '__main__':
    main()
