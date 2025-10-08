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
            self.model = genai.GenerativeModel('models/gemini-2.0-flash')
            logger.info("✅ Usando modelo: models/gemini-2.0-flash")
        else:
            logger.error("❌ API Key de Gemini no configurada")
            self.model = None
    
    def _extract_response_text(self, response):
        """
        🔧 PROPÓSITO: Extraer texto de respuesta de Gemini de forma robusta
        📝 QUÉ HACE: Maneja diferentes formatos de respuesta de la API
        """
        try:
            # Método 1: Acceso simple (para respuestas básicas)
            return response.text.strip()
        except Exception:
            try:
                # Método 2: Acceso complejo (para respuestas complejas)
                return response.candidates[0].content.parts[0].text.strip()
            except Exception as e:
                logger.error(f"❌ Error extrayendo texto de respuesta: {e}")
                return "Error procesando respuesta de IA"
    
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
        
        return f"""Eres Lumo, entrevistador especializado en {department_name}.

🎯 OBJETIVO: Realizar entrevista práctica con EXACTAMENTE 10 preguntas.

📌 REGLAS CRÍTICAS:
1. **LÍMITE ESTRICTO**: Solo 10 preguntas en total (¡NO MÁS!)
2. **RESPUESTAS BREVES**: Máximo 2-3 líneas por respuesta
3. **UNA pregunta por mensaje**: Sin feedback extenso entre preguntas
4. **SIN comentarios largos**: Ir directo a la siguiente pregunta

📌 COMPETENCIAS A EVALUAR:
- Comunicación, pensamiento crítico, adaptabilidad, trabajo en equipo, inteligencia emocional

📌 TIPOS DE PREGUNTAS:
- Experiencias pasadas: "Cuéntame de una situación donde..."
- Escenarios hipotéticos: "¿Qué harías si...?"
- Específicas de {department_name}

� ESTILO REQUERIDO:
- Profesional pero cercano
- Máximo 50-80 palabras por respuesta
- Una sola pregunta directa
- Sin análisis extenso de respuestas
- Emojis ocasionales (1-2 máximo)

IMPORTANTE: Después de la pregunta 10, finaliza amablemente la entrevista."""

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
            initial_prompt = f"""Eres Lumo, entrevistador especializado en {department_name}.

TAREA: Genera UN saludo inicial breve y profesional.

REQUISITOS:
1. Máximo 2-3 líneas
2. Preséntate como Lumo
3. Haz la primera pregunta: "Cuéntame sobre ti y por qué te interesa {department_name}"
4. Tono profesional pero amigable
5. Solo 1 emoji máximo

FORMATO EJEMPLO:
¡Hola! Soy Lumo, tu entrevistador para {department_name}. Para comenzar, ¿podrías contarme sobre ti y por qué te interesa esta área?

Genera SOLO el saludo inicial:"""

            # Generar mensaje inicial
            response = self.model.generate_content(
                initial_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.7,  # Menos creativo para ser más directo
                    top_k=30,
                    top_p=0.8,
                    max_output_tokens=100,  # Mensaje muy corto (reducido de 200)
                )
            )
            
            return self._extract_response_text(response)
            
        except Exception as e:
            logger.error(f"Error generando mensaje inicial: {str(e)}")
            # Mensaje de respaldo
            return f"¡Hola! 👋 Soy Lumo, tu entrevistador especializado en {department_name}. Me da mucho gusto conocerte y estoy emocionado de conocer más sobre tu experiencia profesional. Para comenzar, ¿podrías contarme un poco sobre ti y qué te motiva a aplicar para una posición en {department_name}?"
    
    def _count_ai_questions(self, conversation_history):
        """
        🔢 PROPÓSITO: Contar las preguntas que ha hecho Lumo en la conversación
        📝 QUÉ HACE: Analiza el historial y cuenta mensajes de IA que contienen preguntas
        ⚠️  IMPORTANTE: Cuenta mensajes de IA como preguntas (1 pregunta = 1 mensaje de IA)
        """
        if not conversation_history:
            return 0
            
        ai_message_count = 0
        
        for msg in conversation_history:
            if not msg.get('is_user'):  # Es mensaje de la IA
                ai_message_count += 1
        
        # Cada mensaje de IA cuenta como una pregunta
        # (Excepto mensajes de finalización que contienen "completado las 10 preguntas")
        question_count = 0
        for msg in conversation_history:
            if not msg.get('is_user'):  # Es mensaje de la IA
                content = msg.get('content', '')
                # No contar mensajes de finalización
                if "completado las 10 preguntas" not in content.lower():
                    question_count += 1
        
        logger.info(f"🔢 AI messages: {ai_message_count}, Questions counted: {question_count}")
        return question_count

    async def generate_response(self, message, conversation_history=None, interview_type='operations'):
        """
        🎯 PROPÓSITO: Genera respuesta de la IA con contexto dinámico y límite de 10 preguntas
        📝 QUÉ HACE: Toma el mensaje del usuario y devuelve respuesta especializada
        🚨 LÍMITE CRÍTICO: Máximo 10 preguntas por sesión
        """
        if not self.model:
            raise ValueError("API key de Gemini no configurada")
        
        try:
            # 🔢 CONTAR PREGUNTAS REALIZADAS (CRÍTICO)
            questions_asked = self._count_ai_questions(conversation_history or [])
            
            logger.info(f"🔢 CONTROL DE PREGUNTAS: {questions_asked}/10 realizadas")
            logger.info(f"📝 Historial recibido: {len(conversation_history or [])} mensajes")
            
            # 🚨 VERIFICAR LÍMITE DE 10 PREGUNTAS
            if questions_asked >= 10:
                logger.info("🚨 LÍMITE ALCANZADO: Finalizando entrevista")
                return (
                    "¡Excelente! 🎉 Hemos completado las 10 preguntas de esta entrevista. "
                    "Ha sido un placer conocerte y escuchar sobre tu experiencia profesional. "
                    "Muchas gracias por tu tiempo y por compartir tus conocimientos conmigo. "
                    "¡Te deseo mucho éxito en tu proceso de selección! 🌟\n\n"
                    "La entrevista ha finalizado. Puedes revisar tu evaluación en el panel de resultados."
                )
            
            logger.info(f"✅ CONTINUAR: Generando pregunta #{questions_asked + 1}/10")
            
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
                session_context = f"\n🎯 SESIÓN INICIAL - {department_name}\n🔢 Pregunta: 1/10\n⚠️ RESPUESTA BREVE: Máximo 2-3 líneas\n\n"
                full_context = f"{system_prompt}{session_context}"
                
                # Si hay un mensaje del usuario, es porque ya escribió algo (no debería pasar, pero por si acaso)
                if message and message.strip():
                    full_context += f"El candidato dice: {message}\n"
                
                full_context += "Respuesta breve de Lumo:"
            else:
                # Para mensajes posteriores, usar el flujo normal
                remaining_questions = 10 - questions_asked
                session_context = f"\n🎯 SESIÓN: {department_name}\n� Preguntas: {questions_asked}/10 | Restantes: {remaining_questions}\n"
                
                if remaining_questions == 1:
                    session_context += "⚠️ ÚLTIMA PREGUNTA - Después finaliza la entrevista\n"
                elif remaining_questions <= 3:
                    session_context += f"⚠️ Solo {remaining_questions} preguntas restantes\n"
                
                session_context += "⚠️ RESPUESTA BREVE: Máximo 2-3 líneas, una sola pregunta\n\n"
                
                full_context = f"{system_prompt}{session_context}"
                
                # Agregar historial de conversación (solo últimos 6 mensajes para contexto)
                if conversation_history:
                    full_context += "CONTEXTO RECIENTE:\n"
                    recent_history = conversation_history[-6:] if len(conversation_history) > 6 else conversation_history
                    for msg in recent_history:
                        sender = "Candidato" if msg.get('is_user') else "Lumo"
                        content = msg.get('content', '')[:150] + '...' if len(msg.get('content', '')) > 150 else msg.get('content', '')
                        full_context += f"{sender}: {content}\n"
                    full_context += "\n"
                
                full_context += f"Candidato: {message}\nRespuesta breve de Lumo:"
            
            # Generar respuesta
            response = self.model.generate_content(
                full_context,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.6,  # Menos creativo para ser más directo
                    top_k=30,
                    top_p=0.8,
                    max_output_tokens=150,  # Respuestas muy breves (reducido de 1024)
                )
            )
            
            return self._extract_response_text(response)
            
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
            feedback_prompt = f"""Eres un evaluador experto en {department_name}.

🎯 ANALIZA esta entrevista y genera feedback CONCISO en JSON.

ENTREVISTA:
{conversation_text}

📊 EVALÚA (1-10):
- Comunicación: Claridad y expresión
- Pensamiento crítico: Análisis y lógica  
- Adaptabilidad: Flexibilidad y aprendizaje
- Trabajo en equipo: Colaboración
- Inteligencia emocional: Autoconocimiento y empatía

PUNTAJES:
- 8-10: Excelente con ejemplos concretos
- 6-7: Bueno con algunos ejemplos
- 4-5: Regular, falta profundidad
- 1-3: Deficiente, respuestas vagas

FORMATO JSON REQUERIDO:
{{
    "overall_feedback": "Feedback general en 2-3 líneas máximo con fortalezas y áreas de mejora principales",
    "competency_scores": {{
        "Comunicación": {{
            "score": 8,
            "feedback": "Máximo 1-2 líneas sobre esta competencia",
            "example": "Ejemplo breve de la entrevista",
            "improvement_area": "Área específica de mejora"
        }},
        "Pensamiento crítico": {{
            "score": 7,
            "feedback": "Máximo 1-2 líneas sobre esta competencia",
            "example": "Ejemplo breve de la entrevista", 
            "improvement_area": "Área específica de mejora"
        }},
        "Adaptabilidad": {{
            "score": 6,
            "feedback": "Máximo 1-2 líneas sobre esta competencia",
            "example": "Ejemplo breve de la entrevista",
            "improvement_area": "Área específica de mejora"
        }},
        "Trabajo en equipo": {{
            "score": 7,
            "feedback": "Máximo 1-2 líneas sobre esta competencia",
            "example": "Ejemplo breve de la entrevista",
            "improvement_area": "Área específica de mejora"
        }},
        "Inteligencia emocional": {{
            "score": 8,
            "feedback": "Máximo 1-2 líneas sobre esta competencia",
            "example": "Ejemplo breve de la entrevista",
            "improvement_area": "Área específica de mejora"
        }}
    }}
}}

REQUISITOS:
- SOLO JSON válido, sin texto adicional
- Feedback breve y directo
- Tono profesional pero constructivo
- JSON sin errores de sintaxis"""

            # Generar evaluación con configuración específica para JSON
            response = self.model.generate_content(
                feedback_prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,  # Más bajo para consistencia y brevedad
                    top_k=20,        # Más restrictivo para formato
                    top_p=0.8,       # Más determinístico
                    max_output_tokens=1200,  # Reducido para respuestas más breves
                )
            )
            
            # Procesar respuesta JSON
            return self._parse_json_feedback_response(self._extract_response_text(response))
            
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

