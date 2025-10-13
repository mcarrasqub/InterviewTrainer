# Copilot Instructions for InterviewTrainer

## Project Overview
InterviewTrainer is a Django-based web application for managing interview sessions, user profiles, and feedback. The project is organized into modular Django apps: `interview_trainer` and `evaluation`, with a central configuration in `lumo_project`.

## Architecture & Key Components
- **Apps:**
  - `interview_trainer`: Handles user profiles, interview sessions, chat, and related views.
  - `evaluation`: Manages session feedback, evaluation logic, and related admin/services.
- **Templates:** Organized by app, e.g., `templates/interview_trainer/` and `templates/evaluation/`.
- **Database:** Uses SQLite (`db.sqlite3`).
- **Entry Point:** `manage.py` for all Django management commands.
- **Settings:** Centralized in `lumo_project/settings.py`.

## Developer Workflows
- **Run Server:**
  - Use `run.bat` or `python manage.py runserver`.
- **Migrations:**
  - Apply with `python manage.py migrate`.
- **Testing:**
  - Tests are in `tests.py` within each app and in `evaluation/management/commands/test_evaluation.py`.
  - Run with `python manage.py test`.
- **Database Fixes:**
  - Use `fix_database.bat` for DB-related maintenance.
- **URL Fixes:**
  - Use `fix_urls.bat` for URL-related maintenance.

## Patterns & Conventions
- **API Endpoints:** Defined in `api_urls.py` and `api_views.py` per app.
- **Services:** Business logic is separated into `services.py` in each app.
- **Admin Customization:** See `admin.py` in each app for Django admin extensions.
- **Management Commands:** Custom commands are in `evaluation/management/commands/`.
- **Migrations:** All migration files are under each app's `migrations/` directory.
- **Templates:** Use `{% extends %}` and `{% block %}` for inheritance; see `base.html` and app-specific bases.

## Integration Points
- **External Dependencies:**
  - All Python dependencies are listed in `requirements.txt`.
- **Cross-App Communication:**
  - Apps communicate via Django models, views, and services.

## Examples
- To add a new API endpoint, update `api_urls.py` and implement logic in `api_views.py` and/or `services.py`.
- To customize feedback, edit `evaluation/views.py` and corresponding templates in `templates/evaluation/`.

## References
- **Key Files:**
  - `lumo_project/settings.py`, `interview_trainer/models.py`, `evaluation/services.py`, `templates/base.html`
- **Scripts:**
  - `run.bat`, `fix_database.bat`, `fix_urls.bat`

---
_If any section is unclear or missing, please provide feedback to improve these instructions._
