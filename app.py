from flask import Flask, render_template
import os

# Importar los blueprints
from routes.extractor import extractor_bp
from routes.seo import seo_bp
from routes.keyword_position import keyword_position_bp
from routes.thumbnail_comparison import thumbnail_comparison_bp
from routes.video_activity import video_activity_bp
from routes.keyword_research import keyword_research_bp  # Nuevo

app = Flask(__name__)

# Registrar los blueprints
app.register_blueprint(extractor_bp)
app.register_blueprint(seo_bp)
app.register_blueprint(keyword_position_bp)
app.register_blueprint(thumbnail_comparison_bp)
app.register_blueprint(video_activity_bp)
app.register_blueprint(keyword_research_bp)  # Nuevo

@app.route('/')
def index():
    return render_template('index.html')

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=False)