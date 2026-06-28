from flask import Flask, send_from_directory, jsonify, request, redirect, make_response
from flask_cors import CORS
import subprocess
import os
import json
import random
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv
import time

load_dotenv()

app = Flask(__name__)
CORS(app)

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
STREAMLIT_PROCESS = None

captcha_store = {}
reset_tokens = {}

def get_session_user():
    session_cookie = request.cookies.get('session')
    if session_cookie:
        try:
            data = json.loads(session_cookie)
            return data.get('user')
        except:
            pass
    return None

@app.route('/')
def index():
    # Всегда показываем лендинг
    return send_from_directory(PROJECT_DIR, 'index.html')

@app.route('/login.html')
def login_page():
    user = get_session_user()
    if user:
        return redirect('/run_aurora_direct')
    return send_from_directory(PROJECT_DIR, 'login.html')

@app.route('/<path:filename>')
def serve_static(filename):
    return send_from_directory(PROJECT_DIR, filename)

@app.route('/run_aurora_direct')
def run_aurora_direct():
    global STREAMLIT_PROCESS
    user = get_session_user()
    if not user:
        return redirect('/login.html')
    try:
        script_path = os.path.join(PROJECT_DIR, 'Аврора 6.2.py')
        if os.path.exists(script_path):
            if STREAMLIT_PROCESS is None or STREAMLIT_PROCESS.poll() is not None:
                STREAMLIT_PROCESS = subprocess.Popen(
                    ['streamlit', 'run', script_path, '--server.port', '8501'],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL
                )
            return redirect('http://localhost:8501')
        else:
            return "<h1>Ошибка</h1><p>Файл Аврора 6.2.py не найден</p>", 404
    except Exception as e:
        return f"<h1>Ошибка</h1><p>{e}</p>", 500

@app.route('/captcha')
def captcha():
    a = random.randint(1, 10)
    b = random.randint(1, 10)
    op = random.choice(['+', '-'])
    if op == '+':
        answer = a + b
        expr = f"{a} + {b} = ?"
    else:
        if a < b:
            a, b = b, a
        answer = a - b
        expr = f"{a} - {b} = ?"
    client_ip = request.remote_addr
    captcha_store[client_ip] = answer
    return jsonify({'expression': expr})

@app.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    remember = data.get('remember', False)
    captcha_input = data.get('captcha', '').strip()
    
    client_ip = request.remote_addr
    expected = captcha_store.get(client_ip)
    if expected is None or str(expected) != captcha_input:
        return jsonify({'success': False, 'message': 'Неверная капча'}), 401
    captcha_store.pop(client_ip, None)
    
    if username and password:
        resp = make_response(jsonify({'success': True, 'message': 'OK'}))
        if remember:
            expires = 30*24*60*60
        else:
            expires = None
        resp.set_cookie('session', json.dumps({'user': username}), max_age=expires, httponly=True, samesite='Lax')
        return resp
    else:
        return jsonify({'success': False, 'message': 'Неверные данные'}), 401

@app.route('/logout', methods=['POST'])
def logout():
    resp = make_response(jsonify({'success': True}))
    resp.set_cookie('session', '', expires=0)
    return resp

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
