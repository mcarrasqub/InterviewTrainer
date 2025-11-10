try:
	from .celery import app as celery_app
except Exception:
	# Celery is optional in local/dev environments. If it's not installed or
	# not configured, keep celery_app as None so Django can start.
	celery_app = None

__all__ = ('celery_app',)
