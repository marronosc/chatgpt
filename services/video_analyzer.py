import os
import openai
from googleapiclient.discovery import build
import logging
from datetime import datetime

# Configurar APIs
api_key = os.environ.get('YOUTUBE_API_KEY')
openai.api_key = os.environ.get('OPENAI_API_KEY')

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

        # Llamar a ChatGPT
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system", 
                    "content": "Eres un experto en análisis de contenido de YouTube y estructura narrativa. Proporciona análisis detallados y constructivos para ayudar a creadores a mejorar sus videos."
                },
                {
                    "role": "user", 
                    "content": prompt
                }
            ],
            max_tokens=1500,
            temperature=0.7
        )
        
        analysis = response.choices[0].message.content.strip()
        
        return {
            'success': True,
            'video_id': video_id,
            'video_title': video_title,
            'analysis': analysis,
            'transcript_length': len(transcript.split()),
            'analyzed_at': datetime.now(),
            'transcript_preview': transcript[:300] + "..." if len(transcript) > 300 else transcript
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