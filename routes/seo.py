from flask import Blueprint, request, render_template, redirect, url_for, jsonify
from services.seo_analyzer import search_videos, calculate_average_duration, count_unique_channels
from services.seo_analyzer import get_channel_stats, categorize_videos_by_age, calculate_total_stats
from services.seo_analyzer import format_number, format_date, format_duration
from services.video_analyzer import analyze_video_structure, format_analysis_for_display
import re
import logging

seo_bp = Blueprint('seo', __name__, url_prefix='/seo')

@seo_bp.route('/', methods=['GET', 'POST'])
def seo():
    if request.method == 'POST':
        keyword = request.form['keyword']
        return redirect(url_for('seo.generate_report', keyword=keyword))
    
    return render_template('seo/index.html')

@seo_bp.route('/report/<keyword>')
def generate_report(keyword):
    try:
        videos = search_videos(keyword, max_results=20)
        
        if videos:
            # Añadir video_id extraído de la URL para cada video
            for i, video in enumerate(videos):
                if 'video_url' in video:
                    # Extraer video ID de diferentes formatos de URL
                    video_id = extract_video_id(video['video_url'])
                    video['video_id'] = video_id
                    
                    # Debug logging
                    print(f"Video {i+1}: {video.get('title', 'Sin título')[:50]}...")
                    print(f"  URL: {video['video_url']}")
                    print(f"  Video ID: {video_id}")
                    print(f"  Tiene ID: {'✅' if video_id else '❌'}")
                else:
                    video['video_id'] = None
                    print(f"Video {i+1}: No tiene video_url")
            
            avg_views = sum(video['views'] for video in videos) / len(videos)
            avg_likes = sum(video['likes'] for video in videos) / len(videos)
            avg_comments = sum(video['comments'] for video in videos) / len(videos)
            avg_duration = calculate_average_duration(videos)
            unique_channels_count = count_unique_channels(videos)
            channel_stats = get_channel_stats(videos)
            last_6_months, last_year, older_than_year = categorize_videos_by_age(videos)
            total_stats = calculate_total_stats(videos)
            
            # Contar videos con análisis disponible
            videos_with_analysis = len([v for v in videos if v.get('video_id')])
            print(f"📊 Total videos: {len(videos)}")
            print(f"🧠 Videos con análisis disponible: {videos_with_analysis}")
            
        else:
            avg_views = avg_likes = avg_comments = 0
            avg_duration = None
            unique_channels_count = 0
            channel_stats = {}
            last_6_months = last_year = older_than_year = []
            total_stats = {'total_views': 0, 'total_likes': 0, 'total_comments': 0}

        return render_template('seo/report.html',
            keyword=keyword,
            videos=videos,
            avg_views_videos=avg_views,
            avg_likes_videos=avg_likes,
            avg_comments_videos=avg_comments,
            avg_duration=avg_duration,
            unique_channels_count=unique_channels_count,
            channel_stats=channel_stats,
            last_6_months=last_6_months,
            last_year=last_year,
            older_than_year=older_than_year,
            total_stats=total_stats,
            format_number=format_number,
            format_date=format_date,
            format_duration=format_duration
        )
    except Exception as e:
        error_message = f"Error al generar el informe: {str(e)}"
        logging.error(error_message)
        return render_template('seo/error.html', error=error_message, keyword=keyword)

def extract_video_id(url):
    """
    Extrae el video ID de diferentes formatos de URL de YouTube
    """
    if not url:
        return None
    
    patterns = [
        r'watch\?v=([^&]+)',           # youtube.com/watch?v=ID
        r'youtu\.be/([^?]+)',          # youtu.be/ID
        r'embed/([^?]+)',              # youtube.com/embed/ID
        r'v/([^?]+)',                  # youtube.com/v/ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            video_id = match.group(1)
            # Validar que el ID tenga el formato correcto (11 caracteres)
            if len(video_id) == 11:
                return video_id
    
    return None

@seo_bp.route('/analyze-video/<video_id>')
def analyze_video(video_id):
    """
    Endpoint para analizar la estructura de un video específico
    """
    try:
        video_title = request.args.get('title', '')
        
        print(f"🧠 Analizando video: {video_id}")
        print(f"📝 Título: {video_title}")
        
        # Analizar el video
        analysis_result = analyze_video_structure(video_id, video_title)
        
        if analysis_result['success']:
            # Formatear para mostrar
            formatted_result = format_analysis_for_display(analysis_result)
            return render_template('seo/video_analysis.html', 
                                 result=formatted_result)
        else:
            return render_template('seo/analysis_error.html', 
                                 error=analysis_result['error'],
                                 video_id=video_id)
            
    except Exception as e:
        error_msg = f"Error inesperado: {str(e)}"
        print(f"❌ {error_msg}")
        return render_template('seo/analysis_error.html', 
                             error=error_msg,
                             video_id=video_id)