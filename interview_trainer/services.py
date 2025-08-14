import google.generativeai as genai
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

class GeminiService:
    """
    🤖 PROPÓSITO: Maneja toda la comunicación con Google Gemini
    📝 QUÉ HACE: Envía mensajes a la IA y recibe respuestas
    🔑 CAMBIO: Ahora usa TU API key centralizada
    """
    
    def __init__(self):
        # 🔑 USA TU API KEY CENTRALIZADA (no la del usuario)
        self.api_key = settings.GEMINI_API_KEY
        if self.api_key:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel('gemini-1.5-flash')
        else:
            self.model = None
    
    def get_system_prompt(self, interview_type='general'):
        """
        📝 PROPÓSITO: Define la personalidad de Lumo según el tipo de entrevista
        """
        prompts = {
            'general': """Eres Lumo, un entrenador de entrevistas de trabajo experto y amigable. Tu objetivo es ayudar a los candidatos a prepararse para entrevistas reales.

CARACTERÍSTICAS:
- Eres profesional pero cercano
- Haces preguntas relevantes y realistas
- Proporcionas feedback constructivo
- Te adaptas al nivel y área del candidato
- Usas ejemplos prácticos

INSTRUCCIONES:
- Siempre pregunta por el puesto/área antes de empezar
- Haz una pregunta a la vez
- Da feedback específico y actionable
- Mantén un tono motivador
- Usa emojis ocasionalmente para ser más amigable

Responde en español y mantén las respuestas concisas pero útiles.""",

            'technical': """Eres Lumo, especialista en entrevistas técnicas. Te enfocas en:
- Preguntas de algoritmos y estructuras de datos
- Arquitectura de software
- Mejores prácticas de programación
- Code reviews
- Resolución de problemas técnicos

Haz preguntas progresivas, desde básicas hasta avanzadas.""",

            'behavioral': """Eres Lumo, experto en entrevistas comportamentales. Te especializas en:
- Método STAR (Situación, Tarea, Acción, Resultado)
- Preguntas sobre liderazgo y trabajo en equipo
- Resolución de conflictos
- Adaptabilidad y aprendizaje

Ayuda a estructurar respuestas convincentes y auténticas.""",

            'simulation': """Eres Lumo, conduciendo una simulación completa de entrevista. Actúas como un entrevistador real:
- Haz preguntas variadas (técnicas, comportamentales, situacionales)
- Mantén un flujo natural de conversación
- Proporciona feedback al final
- Evalúa comunicación, conocimientos y fit cultural"""
        }
        return prompts.get(interview_type, prompts['general'])
    
    async def generate_response(self, message, conversation_history=None, interview_type='general'):
        """
        🎯 PROPÓSITO: Genera respuesta de la IA
        📝 QUÉ HACE: Toma el mensaje del usuario y devuelve respuesta de Lumo
        """
        if not self.model:
            raise ValueError("API key de Gemini no configurada")
        
        try:
            # Construir contexto completo
            system_prompt = self.get_system_prompt(interview_type)
            full_context = f"{system_prompt}\n\n"
            
            # Agregar historial de conversación
            if conversation_history:
                for msg in conversation_history:
                    sender = "Usuario" if msg.get('is_user') else "Lumo"
                    full_context += f"{sender}: {msg.get('content')}\n"
            
            full_context += f"Usuario: {message}\nLumo:"
            
            # Generar respuesta
            response = self.model.generate_content(
                full_context,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,
                    top_k=40,
                    top_p=0.95,
                    max_output_tokens=1024,
                )
            )
            
            return response.text
            
        except Exception as e:
            logger.error(f"Error generando respuesta con Gemini: {str(e)}")
            raise e
