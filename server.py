from flask import Flask, send_from_directory, jsonify, request, redirect
from flask_cors import CORS
import subprocess
import os
import signal
import sys

app = Flask(__name__)
CORS(app)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
STREAMLIT_PROCESS = None

@app.route('/')
def index():
    return send_from_directory(PROJECT_DIR, 'index.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(PROJECT_DIR, filename)

@app.route('/run_aurora_direct')
def run_aurora_direct():
    global STREAMLIT_PROCESS
    try:
        script_path = os.path.join(PROJECT_DIR, 'Аврора 6.2.py')
        if os.path.exists(script_path):
            # Запускаем Streamlit на порту 8501
            STREAMLIT_PROCESS = subprocess.Popen(
                ['streamlit', 'run', script_path, '--server.port', '8501'],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            # Перенаправляем на Streamlit
            return redirect('http://localhost:8501')
        else:
            return "<h1>Ошибка</h1><p>Файл Аврора 6.2.py не найден</p>", 404
    except Exception as e:
        return f"<h1>Ошибка</h1><p>{e}</p>", 500

@app.route('/run_aurora', methods=['POST'])
def run_aurora():
    try:
        script_path = os.path.join(PROJECT_DIR, 'Аврора 6.2.py')
        if not os.path.exists(script_path):
            return jsonify({'success': False, 'message': 'Файл Аврора 6.2.py не найден'})
        subprocess.Popen(['streamlit', 'run', script_path, '--server.port', '8501'],
                         stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL)
        return jsonify({'success': True, 'message': 'Аврора 6.2 запущена на порту 8501!'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
