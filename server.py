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

# Хранилища
captcha_store = {}
reset_tokens = {}  # token -> {'username': username, 'email': email, 'expires': timestamp}

# SMTP настройки из .env
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
SMTP_FROM = os.getenv('SMTP_FROM')

def send_reset_email(to_email, reset_link, username):
    """Отправляет письмо со ссылкой для сброса пароля"""
    subject = "Восстановление пароля Aurora Fin"
    html = f"""
    <html>
    <body>
        <h2>Здравствуйте, {username}!</h2>
        <p>Вы запросили восстановление пароля для аккаунта Aurora Fin.</p>
        <p>Перейдите по ссылке ниже, чтобы установить новый пароль:</p>
        <p><a href="{reset_link}">{reset_link}</a></p>
        <p>Ссылка действительна в течение 1 часа.</p>
        <p>Если вы не запрашивали восстановление, просто проигнорируйте это письмо.</p>
        <br>
        <p>С уважением,<br>Команда Aurora Fin</p>
    </body>
    </html>
    """
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = to_email
    msg.attach(MIMEText(html, 'html'))

    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        return True
    except Exception as e:
        print(f"Ошибка отправки письма: {e}")
        return False

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
    user = get_session_user()
    if user:
        return redirect('/run_aurora_direct')
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

@app.route('/forgot', methods=['POST'])
def forgot():
    data = request.get_json()
    username = data.get('username')
    email = data.get('email')
    
    if not username or not email:
        return jsonify({'success': False, 'message': 'Заполните все поля'}), 400
    
    # Генерируем токен
    token = random.randint(100000, 999999)
    token_str = f"{username}_{token}_{int(time.time())}"
    # Сохраняем токен
    reset_tokens[token_str] = {
        'username': username,
        'email': email,
        'expires': time.time() + 3600  # 1 час
    }
    
    # Ссылка для сброса
    reset_link = f"http://localhost:8080/reset.html?token={token_str}"
    
    # Отправляем письмо
    if send_reset_email(email, reset_link, username):
        return jsonify({'success': True, 'message': 'Письмо отправлено'})
    else:
        return jsonify({'success': False, 'message': 'Не удалось отправить письмо'}), 500

@app.route('/verify_reset', methods=['GET'])
def verify_reset():
    token = request.args.get('token')
    if not token or token not in reset_tokens:
        return jsonify({'valid': False, 'message': 'Недействительный токен'})
    data = reset_tokens[token]
    if data['expires'] < time.time():
        return jsonify({'valid': False, 'message': 'Срок действия истёк'})
    return jsonify({'valid': True, 'username': data['username']})

@app.route('/reset', methods=['POST'])
def reset():
    data = request.get_json()
    token = data.get('token')
    new_password = data.get('new_password')
    if not token or not new_password:
        return jsonify({'success': False, 'message': 'Недостаточно данных'}), 400
    if token not in reset_tokens:
        return jsonify({'success': False, 'message': 'Недействительный токен'}), 400
    reset_data = reset_tokens[token]
    if reset_data['expires'] < time.time():
        return jsonify({'success': False, 'message': 'Срок действия истёк'}), 400
    
    # Здесь нужно обновить пароль в БД. Пока заглушка.
    # В реальном проекте — запрос к БД.
    # Поскольку у нас нет БД, мы просто удаляем токен и возвращаем успех.
    del reset_tokens[token]
    return jsonify({'success': True, 'message': 'Пароль изменён'})

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
    
    # Заглушка: пропускаем любые непустые данные (позже заменим на проверку в БД)
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
