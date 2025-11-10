from __future__ import absolute_import, unicode_literals
import logging
import mimetypes
import time
from django.core.files.base import ContentFile
from django.conf import settings

# Intentar importar shared_task; si Celery no está instalado creamos un decorador no-op
try:
    from celery import shared_task
    CELERY_AVAILABLE = True
except Exception:
    CELERY_AVAILABLE = False
    def shared_task(*args, **kwargs):
        def _decorator(func):
            return func
        return _decorator

from .models import ChatMessage
from .services import GeminiService

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def generate_and_save_tts(self, message_id, voice_name=None):
    """Celery task: genera audio TTS usando GeminiService y lo guarda en ChatMessage.audio_file

    Args:
        message_id (int): ID de ChatMessage (IA) donde guardar el audio
        voice_name (str|None): nombre de la voz a usar
    """
    try:
        msg = ChatMessage.objects.get(id=message_id)
    except ChatMessage.DoesNotExist:
        logger.error(f"generate_and_save_tts: mensaje {message_id} no encontrado")
        return {'success': False, 'error': 'Message not found'}

    gemini = GeminiService()
    try:
        tts = gemini.text_to_speech(msg.content, voice_name=voice_name or 'Zephyr')
        if not tts or not tts.get('audio_bytes'):
            logger.warning(f"TTS no retornó audio para mensaje {message_id}")
            return {'success': False, 'error': 'No audio returned'}

        raw = tts['audio_bytes']
        mime = tts.get('mime_type', 'audio/wav')
        ext = mimetypes.guess_extension(mime) or '.wav'
        filename = f"session_{msg.session.id}_msg_{msg.id}_{int(time.time())}{ext}"

        msg.audio_file.save(filename, ContentFile(raw))
        # Guardar nombre de voz si se devolvió
        if tts.get('voice_name'):
            msg.tts_voice = tts.get('voice_name')
        else:
            msg.tts_voice = voice_name or 'Zephyr'

        msg.save()

        logger.info(f"TTS guardado para mensaje {message_id} -> {msg.audio_file.url}")
        return {'success': True, 'audio_url': msg.audio_file.url}

    except Exception as exc:
        logger.exception("Error en generate_and_save_tts: %s", exc)
        return {'success': False, 'error': str(exc)}
