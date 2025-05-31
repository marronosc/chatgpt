import os
from googleapiclient.discovery import build
import logging
from datetime import datetime

# Configurar APIs
api_key = os.environ.get('YOUTUBE_API_KEY')
openai_api_key = os.environ.get('OPENAI_API_KEY')

# Importar OpenAI directamente (versión 1.0+)
try:
    from openai import OpenAI
    if openai_api_key:
        client = OpenAI(api_key=openai_api_key)
        print("✅ OpenAI inicializado correctamente")
    else:
        client = None
        print("❌ OPENAI_API_KEY no encontrada")
except Exception as e:
    client = None
    print(f"❌ Error importando OpenAI: {e}")

if api_key:
    youtube = build('youtube', 'v3', developerKey=api_key)
    print("✅ YouTube API inicializada")
else:
    youtube = None
    print("❌ YOUTUBE_API_KEY no encontrada")

def get_video_transcript(video_id):
    """
    Obtiene la transcripción de un video de YouTube
    """
    if not youtube:
        raise Exception("API de YouTube no configurada")
    
    try:
        print(f"🎥 Obteniendo captions para video: {video_id}")
        
        # Obtener lista de captions disponibles
        captions_request = youtube.captions().list(
            part="snippet",
            videoId=video_id
        )
        captions_response = captions_request.execute()
        
        if not captions_response.get('items'):
            print("❌ No se encontraron captions")
            return None
        
        print(f"📝 Encontrados {len(captions_response['items'])} captions")
        
        # Buscar caption en español o inglés
        caption_id = None
        for caption in captions_response['items']:
            language = caption['snippet']['language']
            print(f"   - Idioma encontrado: {language}")
            if language in ['es', 'es-ES', 'en', 'en-US']:
                caption_id = caption['id']
                print(f"✅ Usando caption en idioma: {language}")
                break
        
        if not caption_id:
            # Si no hay español/inglés, tomar el primero disponible
            caption_id = captions_response['items'][0]['id']
            print("⚠️ Usando primer caption disponible")
        
        # Descargar el contenido de la transcripción
        print("📥 Descargando transcripción...")
        transcript_request = youtube.captions().download(
            id=caption_id,
            tfmt='srt'
        )
        transcript_content = transcript_request.execute()
        
        # Limpiar el contenido SRT
        if isinstance(transcript_content, bytes):
            transcript_content = transcript_content.decode('utf-8')
        
        lines = transcript_content.split('\n')
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
        
        # Limitar a 3000 palabras
        words = transcript_text.split()
        if len(words) > 3000:
            transcript_text = ' '.join(words[:3000]) + "... [transcripción truncada]"
        
        print(f"✅ Transcripción procesada: {len(words)} palabras")
        return transcript_text
        
    except Exception as e:
        print(f"❌ Error obteniendo transcripción: {e}")
        logging.error(f"Error obteniendo transcripción para video {video_id}: {str(e)}")
        return None

def analyze_video_structure(video_id, video_title=""):
    """
    Analiza la estructura de un video usando ChatGPT
    """
    print(f"🧠 Iniciando análisis para video: {video_id}")
    
    try:
        # Verificar OpenAI
        if not client:
            return {
                'success': False,
                'error': 'OpenAI no está configurado correctamente. Verifica la API key.',
                'video_id': video_id
            }
        
        # Obtener transcripción
        transcript = get_video_transcript(video_id)
        
        if not transcript:
            return {
                'success': False,
                'error': 'No se pudo obtener la transcripción del video. Asegúrate de que tenga subtítulos automáticos.',
                'video_id': video_id
            }
        
        # Crear prompt
        prompt = f"""
Analiza esta transcripción de un video de YouTube titulado "{video_title}" y proporciona un análisis estructurado.

FORMATO DE RESPUESTA:

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

TRANSCRIPCIÓN:
{transcript}
"""

        # Llamar a OpenAI
        print("🤖 Enviando a ChatGPT...")
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": "Eres un experto en análisis de contenido de YouTube y estructura narrativa. Proporciona análisis detallados y constructivos."
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
        print("✅ Análisis completado")
        
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
        error_msg = f"Error al analizar el video: {str(e)}"
        print(f"❌ {error_msg}")
        return {
            'success': False,
            'error': error_msg,
            'video_id': video_id
        }

def format_analysis_for_display(analysis_result):
    """
    Formatea el análisis para mostrar en HTML
    """
    return analysis_result

# Debug al importar
print("🚀 Video Analyzer cargado")
print(f"   YouTube API: {'✅' if youtube else '❌'}")
print(f"   OpenAI: {'✅' if client else '❌'}")