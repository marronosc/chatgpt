import os
from googleapiclient.discovery import build
import logging
from datetime import datetime

# Configurar APIs
api_key = os.environ.get('YOUTUBE_API_KEY')
openai_api_key = os.environ.get('OPENAI_API_KEY')

# Intentar importar OpenAI y manejar diferentes versiones
client = None
openai_version = None

try:
    from openai import OpenAI
    # Nueva versión (1.0+)
    if openai_api_key:
        client = OpenAI(api_key=openai_api_key)
        openai_version = "new"
        logging.info("OpenAI versión nueva (1.0+) inicializada correctamente")
except ImportError:
    try:
        import openai
        # Versión antigua (0.x)
        if openai_api_key:
            openai.api_key = openai_api_key
            openai_version = "old"
            logging.info("OpenAI versión antigua (0.x) inicializada correctamente")
    except ImportError:
        client = None
        openai_version = None
        logging.error("No se pudo importar OpenAI")

if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
else:
    youtube = None

def get_video_transcript(video_id):
    """
    Obtiene la transcripción de un video de YouTube
    """
    if not youtube:
        raise Exception("API de YouTube no configurada")
    
    try:
        # Primero intentar obtener captions automáticos
        captions_request = youtube.captions().list(
            part="snippet",
            videoId=video_id
        )
        captions_response = captions_request.execute()
        
        if not captions_response.get('items'):
            return None
        
        # Buscar caption en español o inglés
        caption_id = None
        for caption in captions_response['items']:
            language = caption['snippet']['language']
            if language in ['es', 'es-ES', 'en', 'en-US']:
                caption_id = caption['id']
                break
        
        if not caption_id:
            # Si no hay español/inglés, tomar el primero disponible
            caption_id = captions_response['items'][0]['id']
        
        # Obtener el contenido de la transcripción
        transcript_request = youtube.captions().download(
            id=caption_id,
            tfmt='srt'  # Formato SRT
        )
        transcript_content = transcript_request.execute()
        
        # Limpiar el contenido SRT (remover timestamps y números)
        lines = transcript_content.decode('utf-8').split('\n')
        clean_transcript = []
        
        for line in lines:
            line = line.strip()
            # Saltar líneas vacías, números de secuencia y timestamps
            if (line and 
                not line.isdigit() and 
                '-->' not in line and
                not line.startswith('<')):
                clean_transcript.append(line)
        
        transcript_text = ' '.join(clean_transcript)
        
        # Limitar a 3000 palabras para no exceder límites de ChatGPT
        words = transcript_text.split()
        if len(words) > 3000:
            transcript_text = ' '.join(words[:3000]) + "... [transcripción truncada]"
        
        return transcript_text
        
    except Exception as e:
        logging.error(f"Error obteniendo transcripción para video {video_id}: {str(e)}")
        return None

def analyze_video_structure(video_id, video_title=""):
    """
    Analiza la estructura de un video usando ChatGPT
    """
    try:
        # Verificar que tenemos OpenAI configurado
        if not openai_api_key:
            return {
                'success': False,
                'error': 'OpenAI API key no configurada en las variables de entorno.',
                'video_id': video_id
            }
        
        if not client and openai_version != "old":
            return {
                'success': False,
                'error': 'Cliente OpenAI no pudo ser inicializado. Verifica la configuración.',
                'video_id': video_id
            }
        
        # Obtener transcripción
        transcript = get_video_transcript(video_id)
        
        if not transcript:
            return {
                'success': False,
                'error': 'No se pudo obtener la transcripción del video. El video podría no tener subtítulos automáticos o estar en un idioma no soportado.',
                'video_id': video_id
            }
        
        # Crear prompt para ChatGPT
        prompt = f"""
Analiza esta transcripción de un video de YouTube titulado "{video_title}" y proporciona un análisis estructurado:

**INSTRUCCIONES:**
1. Identifica las diferentes secciones del video
2. Evalúa la efectividad de cada elemento
3. Da recomendaciones específicas de mejora
4. Asigna una puntuación del 1 al 10

**FORMATO DE RESPUESTA:**

🎯 **INTRO/HOOK (0-30 segundos)**
- **Técnica utilizada:** [Describe cómo captura la atención]
- **Promesa/Expectativa:** [Qué promete al viewer]
- **Efectividad:** [1-10] [Explicación breve]

📚 **DESARROLLO (Cuerpo principal)**
- **Estructura:** [Lineal/Por puntos/Narrativa/etc.]
- **Técnicas de retención:** [Qué usa para mantener atención]
- **Ritmo:** [Rápido/Moderado/Lento y por qué]
- **Transiciones:** [Cómo conecta las ideas]

🚀 **CALL-TO-ACTION**
- **Tipo:** [Suscripción/Like/Comentario/Link/etc.]
- **Momento:** [Cuándo aparece en el video]
- **Claridad:** [1-10] [Qué tan claro es]

📊 **PUNTUACIÓN GENERAL**
- **Estructura:** [1-10]
- **Engagement:** [1-10]
- **Profesionalismo:** [1-10]
- **TOTAL:** [1-10]

💡 **RECOMENDACIONES**
- [3-5 mejoras específicas que harían el video más efectivo]

---
**TRANSCRIPCIÓN A ANALIZAR:**
{transcript}
"""

        # Llamar a ChatGPT (compatible con ambas versiones)
        messages = [
            {
                "role": "system", 
                "content": "Eres un experto en análisis de contenido de YouTube y estructura narrativa. Proporciona análisis detallados y constructivos para ayudar a creadores a mejorar sus videos."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        
        analysis = ""
        
        if openai_version == "new" and client:
            # Nueva versión OpenAI (1.0+)
            logging.info("Usando OpenAI versión nueva para análisis")
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            analysis = response.choices[0].message.content.strip()
            
        elif openai_version == "old":
            # Versión antigua OpenAI (0.x)
            logging.info("Usando OpenAI versión antigua para análisis")
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=messages,
                max_tokens=1500,
                temperature=0.7
            )
            analysis = response.choices[0].message.content.strip()
            
        else:
            raise Exception("No se pudo inicializar OpenAI. Verifica la instalación y la API key.")
        
        return {
            'success': True,
            'video_id': video_id,
            'video_title': video_title,
            'analysis': analysis,
            'transcript_length': len(transcript.split()),
            'analyzed_at': datetime.now(),
            'transcript_preview': transcript[:300] + "..." if len(transcript) > 300 else transcript,
            'openai_version': openai_version
        }
        
    except Exception as e:
        logging.error(f"Error analizando video {video_id}: {str(e)}")
        return {
            'success': False,
            'error': f"Error al analizar el video: {str(e)}",
            'video_id': video_id
        }

def format_analysis_for_display(analysis_result):
    """
    Formatea el análisis para mostrar en HTML
    """
    if not analysis_result['success']:
        return analysis_result
    
    # Convertir el análisis de texto a formato estructurado
    analysis_text = analysis_result['analysis']
    
    # Separar secciones usando emojis como delimitadores
    sections = {}
    current_section = ""
    current_content = []
    
    lines = analysis_text.split('\n')
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detectar nuevas secciones por emojis
        if '🎯' in line and 'INTRO' in line.upper():
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'intro'
            current_content = []
        elif '📚' in line and 'DESARROLLO' in line.upper():
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'desarrollo'
            current_content = []
        elif '🚀' in line and 'CALL' in line.upper():
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'cta'
            current_content = []
        elif '📊' in line and 'PUNTUACIÓN' in line.upper():
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'puntuacion'
            current_content = []
        elif '💡' in line and 'RECOMENDACIONES' in line.upper():
            if current_section:
                sections[current_section] = '\n'.join(current_content)
            current_section = 'recomendaciones'
            current_content = []
        else:
            current_content.append(line)
    
    # Añadir la última sección
    if current_section:
        sections[current_section] = '\n'.join(current_content)
    
    analysis_result['sections'] = sections
    return analysis_result

def test_openai_connection():
    """
    Función de prueba para verificar la conexión con OpenAI
    """
    try:
        if not openai_api_key:
            return {"success": False, "error": "API key no configurada"}
        
        if openai_version == "new" and client:
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Di hola"}],
                max_tokens=10
            )
            return {"success": True, "version": "new", "response": response.choices[0].message.content}
            
        elif openai_version == "old":
            import openai
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[{"role": "user", "content": "Di hola"}],
                max_tokens=10
            )
            return {"success": True, "version": "old", "response": response.choices[0].message.content}
        
        else:
            return {"success": False, "error": "OpenAI no inicializado"}
            
    except Exception as e:
        return {"success": False, "error": str(e)}

# Información de debug para logs
logging.info(f"Video Analyzer inicializado:")
logging.info(f"  - YouTube API: {'✅' if youtube else '❌'}")
logging.info(f"  - OpenAI API: {'✅' if openai_api_key else '❌'}")
logging.info(f"  - OpenAI Version: {openai_version or 'No detectada'}")
logging.info(f"  - Cliente OpenAI: {'✅' if client else ('✅ (v0.x)' if openai_version == 'old' else '❌')}")