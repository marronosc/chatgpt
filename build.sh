#!/bin/bash
set -e  # Salir si hay algún error

echo "=== INICIO DEL BUILD ==="
echo "Python version:"
python --version

echo "Pip version:"
pip --version

echo "=== ACTUALIZANDO PIP ==="
pip install --upgrade pip

echo "=== VERIFICANDO REQUIREMENTS.TXT ==="
echo "Contenido de requirements.txt:"
cat requirements.txt
echo "---"

echo "¿Existe requirements.txt?"
ls -la requirements.txt

echo "=== INSTALANDO DEPENDENCIAS DESDE REQUIREMENTS ==="
pip install -r requirements.txt

echo "=== INSTALANDO OPENAI ESPECÍFICAMENTE ==="
echo "Instalando OpenAI 1.35.0..."
pip install openai==1.35.0

echo "=== VERIFICANDO INSTALACIONES ==="
echo "Packages installed:"
pip list | grep -E "(openai|flask|google)"

echo "=== VERIFICANDO OPENAI ESPECÍFICAMENTE ==="
python -c "import openai; print('OpenAI version:', openai.__version__)"

echo "=== VERIFICANDO FLASK ESPECÍFICAMENTE ==="
python -c "import flask; print('Flask version:', flask.__version__)"

echo "=== VERIFICANDO GOOGLE API CLIENT ==="
python -c "import googleapiclient; print('Google API Client importado correctamente')"

echo "=== ESTRUCTURA DE ARCHIVOS ==="
ls -la

echo "=== BUILD COMPLETADO EXITOSAMENTE ==="