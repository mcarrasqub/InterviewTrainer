import google.generativeai as genai
from django.conf import settings
import logging
import json
from django.utils import timezone

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
    
    def get_system_prompt(self, interview_type='operations'):
        """
        📝 PROPÓSITO: Define la personalidad y metodología de Lumo según el área
        🎯 MÉTODOS: Combina STAR y SJT para evaluar competencias
        """
        # Mapeo de códigos a nombres legibles
        department_names = {
            'operations': 'Operaciones y Producción',
            'sales_marketing': 'Ventas y Marketing',
            'finance': 'Finanzas y Administración',
            'hr': 'Recursos Humanos (Talento Humano)',
            'it': 'Tecnología de la Información (TI / IT)',
            'rd': 'Investigación y Desarrollo (I+D)',
            'customer_support': 'Atención al Cliente y Soporte',
            'management': 'Dirección General y Estratégica',
            'health': 'Salud y Medicina'
        }
        
        department_name = department_names.get(interview_type, 'Operaciones y Producción')
        
        return f"""Eres Lumo, un entrenador de entrevistas especializado en el área de {department_name}. 

📌 MÉTODOS A UTILIZAR:
- **STAR (Situation, Task, Action, Result)**: Formula preguntas que lleven al candidato a estructurar sus respuestas siguiendo este modelo.
- **SJT (Situational Judgment Test)**: Presenta escenarios hipotéticos del área de {department_name} y pide al candidato que explique cómo actuaría.

📌 COMPETENCIAS A EVALUAR:
1. Comunicación
2. Pensamiento crítico
3. Adaptabilidad
4. Trabajo en equipo
5. Inteligencia emocional

🎯 OBJETIVO:
- Evaluar cómo el candidato aplica estas competencias en situaciones reales y simuladas.
- Hacer preguntas abiertas que permitan ejemplos concretos (STAR).
- Hacer escenarios hipotéticos que midan juicio y toma de decisiones (SJT).

📌 INSTRUCCIONES PARA LA ENTREVISTA:
1. **Contexto**: Estás entrevistando para una posición en {department_name}.
2. **Preguntas Posteriores**:
    - La entrevista debe consistir en 10-15 preguntas
   - Haz preguntas con formato STAR (ejemplo: "Cuéntame de una situación donde tuviste que resolver un conflicto en tu equipo").
   - Haz preguntas SJT (ejemplo: "Imagina que un cliente clave se queja de un error importante. ¿Qué harías?").
   - Asegúrate de cubrir todas las competencias en el transcurso de la entrevista.
3. **Estilo**:
   - Una sola pregunta a la vez.
   - Lenguaje profesional pero cercano.
   - Usa ejemplos del área de {department_name}.
   - Puedes usar emojis ocasionalmente para hacerlo más amigable.

OBJETIVO FINAL:
Ayudar al candidato a prepararse para una entrevista real en {department_name}, practicando con preguntas que evalúan competencias clave usando STAR y SJT (no menciones explicitamente STAR o SJT)"""

    async def generate_initial_welcome(self, interview_type='operations'):
        """
        🎯 PROPÓSITO: Genera SOLO el mensaje inicial de bienvenida
        📝 QUÉ HACE: Crea un saludo específico para iniciar la entrevista
        """
        if not self.model:
            raise ValueError("API key de Gemini no configurada")
        
        try:
            # Mapeo de tipos a nombres
            department_names = {
                'operations': 'Operaciones y Producción',
                'sales_marketing': 'Ventas y Marketing', 
                'finance': 'Finanzas y Administración',
                'hr': 'Recursos Humanos (Talento Humano)',
                'it': 'Tecnología de la Información (TI / IT)',
                'rd': 'Investigación y Desarrollo (I+D)',
                'customer_support': 'Atención al Cliente y Soporte',
                'management': 'Dirección General y Estratégica',
                'health': 'Salud y Medicina'
            }
            
            department_name = department_names.get(interview_type, 'Operaciones y Producción')
            
            # Prompt específico para mensaje inicial
            initial_prompt = f"""Eres Lumo, un entrevistador profesional especializado en {department_name}.

Tu tarea es generar UN MENSAJE INICIAL de bienvenida para comenzar una entrevista de trabajo.

INSTRUCCIONES:
1. Saluda de forma profesional pero amigable
2. Preséntate como Lumo, tu entrevistador especializado en {department_name}
3. Menciona que realizarás una entrevista para evaluar competencias
4. Haz la primera pregunta típica: "Cuéntame un poco sobre ti y qué te motiva a aplicar para una posición en {department_name}"
5. Usa un tono profesional pero cercano
6. Máximo 3-4 líneas
7. Usa algún emoji para ser más amigable

EJEMPLO:
¡Hola! 👋 Soy Lumo, tu entrevistador especializado en {department_name}. Me da mucho gusto conocerte y estoy emocionado de conocer más sobre tu experiencia profesional. Para comenzar, ¿podrías contarme un poco sobre ti y qué te motiva a aplicar para una posición en {department_name}?

Genera SOLO el mensaje inicial:"""

            # Generar mensaje inicial
            response = self.model.generate_content(
                initial_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.8,  # Más creativo para variedad
                    top_k=40,
                    top_p=0.9,
                    max_output_tokens=200,  # Mensaje corto
                )
            )
            
            return response.text.strip()
            
        except Exception as e:
            logger.error(f"Error generando mensaje inicial: {str(e)}")
            # Mensaje de respaldo
            return f"¡Hola! 👋 Soy Lumo, tu entrevistador especializado en {department_name}. Me da mucho gusto conocerte y estoy emocionado de conocer más sobre tu experiencia profesional. Para comenzar, ¿podrías contarme un poco sobre ti y qué te motiva a aplicar para una posición en {department_name}?"
    
    async def generate_response(self, message, conversation_history=None, interview_type='operations'):
        """
        🎯 PROPÓSITO: Genera respuesta de la IA con contexto dinámico
        📝 QUÉ HACE: Toma el mensaje del usuario y devuelve respuesta especializada
        """
        if not self.model:
            raise ValueError("API key de Gemini no configurada")
        
        try:
            # Construir contexto completo con información dinámica
            system_prompt = self.get_system_prompt(interview_type)
            
            # Agregar contexto de la sesión actual
            department_names = {
                'operations': 'Operaciones y Producción',
                'sales_marketing': 'Ventas y Marketing', 
                'finance': 'Finanzas y Administración',
                'hr': 'Recursos Humanos (Talento Humano)',
                'it': 'Tecnología de la Información (TI / IT)',
                'rd': 'Investigación y Desarrollo (I+D)',
                'customer_support': 'Atención al Cliente y Soporte',
                'management': 'Dirección General y Estratégica',
                'health': 'Salud y Medicina'
            }
            
            department_name = department_names.get(interview_type, 'Operaciones y Producción')
            
            # 🎯 DETECTAR SI ES EL PRIMER MENSAJE (SIN HISTORIAL)
            is_first_message = not conversation_history or len(conversation_history) == 0
            
            if is_first_message:
                # Para el primer mensaje, usar prompt específico
                session_context = f"\n🎯 CONTEXTO DE SESIÓN INICIAL:\n- Departamento: {department_name}\n- ESTE ES EL PRIMER MENSAJE: Genera el saludo inicial de bienvenida siguiendo las instrucciones del prompt\n- NO hay historial previo, empieza la entrevista\n\n"
                full_context = f"{system_prompt}{session_context}"
                
                # Si hay un mensaje del usuario, es porque ya escribió algo (no debería pasar, pero por si acaso)
                if message and message.strip():
                    full_context += f"El candidato dice: {message}\n"
                
                full_context += "Entrevistador (Lumo):"
            else:
                # Para mensajes posteriores, usar el flujo normal
                session_context = f"\n🎯 CONTEXTO DE SESIÓN ACTUAL:\n- Departamento: {department_name}\n- Tipo de entrevista: Especializada en {department_name}\n- Número de mensajes previos: {len(conversation_history)}\n\n"
                
                full_context = f"{system_prompt}{session_context}"
                
                # Agregar historial de conversación
                if conversation_history:
                    full_context += "HISTORIAL DE CONVERSACIÓN:\n"
                    for msg in conversation_history:
                        sender = "Candidato" if msg.get('is_user') else "Entrevistador (Lumo)"
                        full_context += f"{sender}: {msg.get('content')}\n"
                    full_context += "\n"
                
                full_context += f"Candidato: {message}\nEntrevistador (Lumo):"
            
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
        
    async def generate_feedback_and_scores(self, session, messages):
        """
        🎯 PROPÓSITO: Analiza toda la entrevista y genera feedback con puntajes de competencias
        📊 QUÉ HACE: Evalúa cada competencia del 1-10 con feedback detallado en formato JSON
        """
        if not self.model:
            raise ValueError("Modelo de IA no configurado")

        try:
            # Mapeo de tipos a nombres
            department_names = {
                'operations': 'Operaciones y Producción',
                'sales_marketing': 'Ventas y Marketing', 
                'finance': 'Finanzas y Administración',
                'hr': 'Recursos Humanos (Talento Humano)',
                'it': 'Tecnología de la Información (TI / IT)',
                'rd': 'Investigación y Desarrollo (I+D)',
                'customer_support': 'Atención al Cliente y Soporte',
                'management': 'Dirección General y Estratégica',
                'health': 'Salud y Medicina'
            }
            
            department_name = department_names.get(session.session_type, 'Operaciones y Producción')
            
            # Construir historial completo de la entrevista
            conversation_text = ""
            for msg in messages:
                sender = "Candidato" if msg.is_user else "Entrevistador"
                conversation_text += f"{sender}: {msg.content}\n"

            # Prompt de evaluación con formato JSON
            feedback_prompt = f"""Eres un evaluador experto de entrevistas de trabajo especializado en {department_name}.

🎯 TU TAREA: Analizar esta entrevista completa y generar un feedback detallado en formato JSON.

HISTORIAL COMPLETO DE LA ENTREVISTA:
{conversation_text}

📊 COMPETENCIAS A EVALUAR (Puntaje 1-10):
1. **Comunicación**: Claridad, estructura, capacidad de expresar ideas
2. **Pensamiento crítico**: Análisis, lógica, resolución de problemas
3. **Adaptabilidad**: Flexibilidad, manejo de cambios, aprendizaje
4. **Trabajo en equipo**: Colaboración, liderazgo, habilidades interpersonales
5. **Inteligencia emocional**: Autoconocimiento, empatía, manejo de emociones

CRITERIOS DE PUNTAJE:
- 8-10: Excelente, respuestas muy sólidas con ejemplos concretos
- 6-7: Bueno, respuestas adecuadas con algunos ejemplos
- 4-5: Regular, respuestas básicas, falta profundidad
- 1-3: Deficiente, respuestas vagas o insuficientes

FORMATO DE RESPUESTA REQUERIDO (JSON VÁLIDO):
{{
    "overall_feedback": "Un párrafo de 3-4 líneas con feedback general del desempeño que incluya areas de mejora y fortalezas específicas",
    "competency_scores": {{
        "Comunicación": {{
            "score": 8,
            "feedback": "Feedback específico de 1-2 líneas sobre esta competencia",
            "example": "Ejemplo concreto extraído de la entrevista",
            "improvement_area": "Área específica de mejora"
        }},
        "Pensamiento crítico": {{
            "score": 7,
            "feedback": "Feedback específico de 1-2 líneas sobre esta competencia",
            "example": "Ejemplo concreto extraído de la entrevista",
            "improvement_area": "Área específica de mejora"
        }},
        "Adaptabilidad": {{
            "score": 6,
            "feedback": "Feedback específico de 1-2 líneas sobre esta competencia",
            "example": "Ejemplo concreto extraído de la entrevista",
            "improvement_area": "Área específica de mejora"
        }},
        "Trabajo en equipo": {{
            "score": 7,
            "feedback": "Feedback específico de 1-2 líneas sobre esta competencia",
            "example": "Ejemplo concreto extraído de la entrevista",
            "improvement_area": "Área específica de mejora"
        }},
        "Inteligencia emocional": {{
            "score": 8,
            "feedback": "Feedback específico de 1-2 líneas sobre esta competencia",
            "example": "Ejemplo concreto extraído de la entrevista",
            "improvement_area": "Área específica de mejora"
        }}
    }}
}}

IMPORTANTE: 
- Responde ÚNICAMENTE con el JSON válido, sin texto adicional
- Sé constructivo y específico en las áreas de mejora
- Mantén un tono profesional pero alentador
- Asegúrate de que el JSON sea válido (sin comas finales, comillas correctas)"""

            # Generar evaluación con configuración específica para JSON
            response = self.model.generate_content(
                feedback_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.2,  # Más bajo para consistencia en formato
                    top_k=10,        # Más restrictivo para formato
                    top_p=0.7,       # Más determinístico
                    max_output_tokens=2048,
                )
            )
            
            # Procesar respuesta JSON
            return self._parse_json_feedback_response(response.text)
            
        except Exception as e:
            logger.error(f"Error generando feedback: {str(e)}")
            raise e

    def _parse_json_feedback_response(self, response_text: str) -> dict:
        """
        🔧 PROPÓSITO: Parsea la respuesta JSON de la IA
        📝 QUÉ HACE: Convierte JSON a diccionario con validación robusta
        """
        try:
            # Limpiar respuesta (remover markdown si existe)
            json_text = response_text.strip()
            
            # Remover bloques de código markdown si existen
            if json_text.startswith('```json'):
                json_text = json_text.replace('```json', '').replace('```', '').strip()
            elif json_text.startswith('```'):
                json_text = json_text.replace('```', '').strip()
            
            # Parsear JSON
            feedback_data = json.loads(json_text)
            
            # Validar estructura requerida
            if not isinstance(feedback_data, dict):
                raise ValueError("Respuesta no es un diccionario")
                
            if 'overall_feedback' not in feedback_data:
                raise ValueError("Falta 'overall_feedback'")
                
            if 'competency_scores' not in feedback_data:
                raise ValueError("Falta 'competency_scores'")
            
            # Validar competencias requeridas
            required_competencies = [
                'Comunicación', 'Pensamiento crítico', 'Adaptabilidad', 
                'Trabajo en equipo', 'Inteligencia emocional'
            ]
            
            competency_scores = feedback_data['competency_scores']
            for comp in required_competencies:
                if comp not in competency_scores:
                    logger.warning(f"Competencia faltante: {comp}")
                    # Agregar competencia con valores por defecto
                    competency_scores[comp] = {
                        'score': 7,
                        'feedback': 'Evaluación pendiente',
                        'example': 'Por determinar',
                        'improvement_area': 'Análisis en proceso'
                    }
                else:
                    # Validar estructura de cada competencia
                    comp_data = competency_scores[comp]
                    if not isinstance(comp_data, dict):
                        raise ValueError(f"Datos de competencia {comp} inválidos")
                    
                    # Validar campos requeridos con valores por defecto
                    comp_data.setdefault('score', 7)
                    comp_data.setdefault('feedback', 'Evaluación pendiente')
                    comp_data.setdefault('example', 'Por determinar')
                    comp_data.setdefault('improvement_area', 'Análisis en proceso')
                    
                    # Validar que score esté en rango 1-10
                    try:
                        score = int(comp_data['score'])
                        if not (1 <= score <= 10):
                            logger.warning(f"Score fuera de rango para {comp}: {score}")
                            comp_data['score'] = max(1, min(10, score))
                        else:
                            comp_data['score'] = score
                    except (ValueError, TypeError):
                        logger.warning(f"Score inválido para {comp}")
                        comp_data['score'] = 7
            
            return feedback_data
            
        except json.JSONDecodeError as e:
            logger.error(f"Error parseando JSON: {str(e)}")
            logger.error(f"Respuesta recibida: {response_text[:500]}...")
            return self._get_fallback_feedback()
            
        except Exception as e:
            logger.error(f"Error procesando feedback: {str(e)}")
            return self._get_fallback_feedback()
    
    def _get_fallback_feedback(self) -> dict:
        """
        🆘 PROPÓSITO: Feedback de emergencia si falla el parsing
        """
        return {
            'overall_feedback': 'Se completó la entrevista exitosamente. El análisis detallado estará disponible próximamente tras revisión del sistema.',
            'competency_scores': {
                'Comunicación': {
                    'score': 7,
                    'feedback': 'Evaluación en proceso - sistema procesando respuestas',
                    'example': 'Por determinar tras análisis completo',
                    'improvement_area': 'Recomendaciones disponibles próximamente'
                },
                'Pensamiento crítico': {
                    'score': 7,
                    'feedback': 'Evaluación en proceso - sistema procesando respuestas',
                    'example': 'Por determinar tras análisis completo',
                    'improvement_area': 'Recomendaciones disponibles próximamente'
                },
                'Adaptabilidad': {
                    'score': 7,
                    'feedback': 'Evaluación en proceso - sistema procesando respuestas',
                    'example': 'Por determinar tras análisis completo',
                    'improvement_area': 'Recomendaciones disponibles próximamente'
                },
                'Trabajo en equipo': {
                    'score': 7,
                    'feedback': 'Evaluación en proceso - sistema procesando respuestas',
                    'example': 'Por determinar tras análisis completo',
                    'improvement_area': 'Recomendaciones disponibles próximamente'
                },
                'Inteligencia emocional': {
                    'score': 7,
                    'feedback': 'Evaluación en proceso - sistema procesando respuestas',
                    'example': 'Por determinar tras análisis completo',
                    'improvement_area': 'Recomendaciones disponibles próximamente'
                }
            }
        }

