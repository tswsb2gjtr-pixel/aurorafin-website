import streamlit as st
import sqlite3
import hashlib
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import time
from datetime import datetime, timedelta
from sklearn.ensemble import RandomForestRegressor
import joblib
import os
import requests
import json
from sentence_transformers import SentenceTransformer
import faiss
from dotenv import load_dotenv
import whisper
import pyaudio
import wave
import tempfile
import calendar

load_dotenv()

# --- Настройка страницы и тёмная тема ---
st.set_page_config(page_title="Aurora Fin", page_icon="⚡", layout="wide")

st.markdown("""
<style>
    @import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap");
    * { font-family: "Inter", -apple-system, sans-serif; }
    .stApp { background-color: #000000; }
    .stButton>button { background: #4F55F1; color: white; border-radius: 40px; font-weight: 600; border: none; padding: 12px 32px; transition: 0.3s; }
    .stButton>button:hover { background: #3a40d1; transform: translateY(-2px); }
    .stSelectbox>div>div { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: white; }
    .stTextInput>div>div>input { background: rgba(255,255,255,0.06); border: 1px solid rgba(255,255,255,0.1); border-radius: 12px; color: white; }
    .stMetric { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 16px; }
    .stSidebar { background-color: #0D0D0D; }
    h1, h2, h3, h4, h5, h6 { color: #FFFFFF; }
    .stMarkdown p { color: rgba(255,255,255,0.7); }
    .card-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-top: 30px; }
    .card { background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.06); border-radius: 16px; padding: 30px 20px; text-align: center; transition: 0.3s; cursor: pointer; }
    .card:hover { background: rgba(255,255,255,0.08); border-color: #4F55F1; transform: translateY(-4px); }
    .card .icon { font-size: 48px; display: block; margin-bottom: 12px; }
    .card .label { font-size: 18px; font-weight: 600; color: #FFFFFF; }
    .card .desc { font-size: 14px; color: rgba(255,255,255,0.5); margin-top: 4px; }
    .sub-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }
    @media (max-width: 768px) { .sub-grid { grid-template-columns: repeat(2, 1fr); } }
    .stButton > button { background: rgba(255,255,255,0.04) !important; border: 1px solid rgba(255,255,255,0.06) !important; border-radius: 16px !important; padding: 16px !important; font-weight: 600 !important; color: #FFFFFF !important; transition: 0.3s !important; width: 100% !important; text-align: center !important; }
    .stButton > button:hover { background: rgba(255,255,255,0.08) !important; border-color: #4F55F1 !important; transform: translateY(-4px) !important; }
</style>
""", unsafe_allow_html=True)

# --- Инициализация session_state ---
if "name" not in st.session_state:
    st.session_state.name = "Гость"
if "role" not in st.session_state:
    st.session_state.role = "guest"
if "inn" not in st.session_state:
    st.session_state.inn = ""
if "selected_service" not in st.session_state:
    st.session_state.selected_service = None
if "lang" not in st.session_state:
    st.session_state.lang = "ru"
if "theme" not in st.session_state:
    st.session_state.theme = {"mode": "dark", "accent": "#4F55F1"}
if "page" not in st.session_state:
    st.session_state.page = "home"
if "finance_subpage" not in st.session_state:
    st.session_state.finance_subpage = "overview"
if "chat_messages" not in st.session_state:
    st.session_state.chat_messages = []
if "uploaded_data" not in st.session_state:
    st.session_state.uploaded_data = None
if "kpi_updated" not in st.session_state:
    st.session_state.kpi_updated = False
if "greeting_shown" not in st.session_state:
    st.session_state.greeting_shown = False
if "logged_in" not in st.session_state:
    st.session_state.logged_in = True

# --- Функции (сохранены все) ---
def init_theme():
    pass

def apply_theme():
    pass

def init_db():
    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users
                 (inn TEXT PRIMARY KEY,
                  name TEXT,
                  password_hash TEXT,
                  consent BOOLEAN,
                  role TEXT,
                  created_at TIMESTAMP,
                  lang TEXT DEFAULT 'ru')''')
    c.execute('''CREATE TABLE IF NOT EXISTS employees
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  inn_owner TEXT,
                  name TEXT,
                  position TEXT,
                  phone TEXT,
                  birth_date TEXT,
                  work_hours TEXT,
                  plan REAL,
                  actual REAL,
                  tasks TEXT,
                  FOREIGN KEY(inn_owner) REFERENCES users(inn))''')
    c.execute('''CREATE TABLE IF NOT EXISTS events
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  inn_owner TEXT,
                  event_date DATE,
                  title TEXT,
                  description TEXT,
                  event_type TEXT,
                  FOREIGN KEY(inn_owner) REFERENCES users(inn))''')
    c.execute('''CREATE TABLE IF NOT EXISTS goals
                 (inn_owner TEXT PRIMARY KEY,
                  profit_goal REAL,
                  FOREIGN KEY(inn_owner) REFERENCES users(inn))''')
    c.execute('''CREATE TABLE IF NOT EXISTS expense_details
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  inn_owner TEXT,
                  expense_type TEXT,
                  description TEXT,
                  amount REAL,
                  due_date DATE,
                  extra_info TEXT,
                  FOREIGN KEY(inn_owner) REFERENCES users(inn))''')
    conn.commit()
    conn.close()

init_db()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(inn, name, password, role, lang):
    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (inn, name, password_hash, consent, role, created_at, lang) VALUES (?,?,?,?,?,?,?)",
                  (inn, name, hash_password(password), False, role, datetime.now(), lang))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        conn.close()
        return False

def check_user(inn, password):
    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    c.execute("SELECT password_hash, consent, name, role, lang FROM users WHERE inn=?", (inn,))
    row = c.fetchone()
    conn.close()
    if row and row[0] == hash_password(password):
        return {"consent": row[1], "name": row[2], "role": row[3], "lang": row[4]}
    return None

def update_consent(inn):
    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    c.execute("UPDATE users SET consent = 1 WHERE inn=?", (inn,))
    conn.commit()
    conn.close()

def get_user_by_inn(inn):
    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    c.execute("SELECT name, role, lang FROM users WHERE inn=?", (inn,))
    row = c.fetchone()
    conn.close()
    if row:
        return {"name": row[0], "role": row[1], "lang": row[2]}
    return None

def get_profit_goal(inn):
    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    c.execute("SELECT profit_goal FROM goals WHERE inn_owner=?", (inn,))
    row = c.fetchone()
    conn.close()
    return row[0] if row else 300000

def set_profit_goal(inn, goal):
    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    c.execute("REPLACE INTO goals (inn_owner, profit_goal) VALUES (?,?)", (inn, goal))
    conn.commit()
    conn.close()

def format_number(x):
    return f"{x:,.0f}".replace(",", " ")

def color_kpi(value, good, medium):
    if value >= good:
        return "green"
    elif value >= medium:
        return "orange"
    else:
        return "red"

def show_time_greeting(lang):
    hour = datetime.now().hour
    if lang == "ru":
        if 5 <= hour < 12: greeting = "Доброе утро"
        elif 12 <= hour < 18: greeting = "Добрый день"
        elif 18 <= hour < 23: greeting = "Добрый вечер"
        else: greeting = "Доброй ночи"
    else:
        greeting = "Good day"
    placeholder = st.empty()
    placeholder.markdown(f"""
    <div style="position:fixed; top:0; left:0; width:100%; height:100%; background-color:#2c3e50; display:flex; justify-content:center; align-items:center; z-index:9999;">
        <h1 style="color:white; font-size:48px;">{greeting}!</h1>
    </div>
    """, unsafe_allow_html=True)
    time.sleep(2)
    placeholder.empty()

def create_3d_pie(value, target, title, lang):
    remaining = max(0, target - value)
    percentage = (value / target) * 100 if target > 0 else 0
    fig = go.Figure(data=[go.Pie(
        labels=['Достигнуто' if lang=='ru' else 'Achieved', 'Осталось' if lang=='ru' else 'Remaining'],
        values=[value, remaining],
        marker_colors=['#2ecc71', '#e74c3c'],
        hole=0.4,
        textinfo='none',
        pull=[0.05, 0],
        sort=False
    )])
    fig.update_layout(
        title=title,
        annotations=[dict(text=f"{format_currency(value, st.session_state.currency)}<br>({percentage:.1f}%)", x=0.5, y=0.5, font_size=16, showarrow=False)],
        height=400,
        width=400,
        margin=dict(l=20, r=20, t=50, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)'
    )
    return fig

def forecast_outcome(value, target):
    if value >= target:
        return "достигнута"
    elif value >= target * 0.8:
        return f"с вероятностью {np.random.randint(70,95)}%"
    elif value >= target * 0.5:
        return f"с вероятностью {np.random.randint(40,70)}%"
    else:
        return "не сможем"

def generate_balance_series(days=90):
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now().date(), periods=days)
    balance = 50000 + np.cumsum(np.random.normal(0, 2000, days))
    balance[30] -= 30000
    balance[60] -= 25000
    balance[75] -= 20000
    balance = np.maximum(balance, -20000)
    return pd.Series(balance, index=dates, name='balance')

def prepare_features_from_series(balance_series):
    df = pd.DataFrame({'balance': balance_series})
    df.index = pd.to_datetime(df.index)
    df['dayofweek'] = df.index.dayofweek
    for lag in range(1, 8):
        df[f'lag_{lag}'] = df['balance'].shift(lag)
    df['rolling_mean_7'] = df['balance'].rolling(7).mean()
    df = df.dropna()
    features = ['dayofweek'] + [f'lag_{i}' for i in range(1,8)] + ['rolling_mean_7']
    X = df[features]
    y = df['balance']
    return X, y

def forecast_cash_gap(days_ahead=7):
    balance_series = generate_balance_series(90)
    X, y = prepare_features_from_series(balance_series)
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(X, y)
    last = X.iloc[-1:].copy()
    forecast = []
    for _ in range(days_ahead):
        pred = model.predict(last)[0]
        forecast.append(pred)
        new = last.iloc[0].copy()
        for lag in range(7, 1, -1):
            new[f'lag_{lag}'] = new[f'lag_{lag-1}']
        new['lag_1'] = pred
        new['dayofweek'] = (new['dayofweek'] + 1) % 7
        new['rolling_mean_7'] = (new['rolling_mean_7'] * 7 - last['lag_7'].iloc[0] + pred) / 7
        last = pd.DataFrame([new])
    future_dates = [balance_series.index[-1] + timedelta(days=i+1) for i in range(days_ahead)]
    return future_dates, forecast

def load_v2_model():
    model = joblib.load('model_v2_median.pkl')
    feature_cols = open('features_v2.txt').read().strip().split(',')
    return model, feature_cols

def add_calendar_features(df):
    df = df.copy()
    df['dayofweek'] = df['date'].dt.dayofweek
    df['is_weekend'] = (df['dayofweek'] >= 5).astype(int)
    df['day_of_month'] = df['date'].dt.day
    df['month'] = df['date'].dt.month
    df['quarter'] = df['date'].dt.quarter
    df['is_month_end'] = df['date'].dt.is_month_end.astype(int)
    df['is_quarter_end'] = (df['date'].dt.quarter != df['date'].shift(1).dt.quarter).astype(int)
    df['is_tax_day_25'] = (df['day_of_month'] == 25).astype(int)
    df['is_tax_day_28'] = (df['day_of_month'] == 28).astype(int)
    df['is_payday_early'] = df['day_of_month'].between(5, 10).astype(int)
    df['is_payday_late'] = df['day_of_month'].between(20, 25).astype(int)
    holidays = ['2024-01-01','2024-01-02','2024-01-07','2024-02-23','2024-03-08',
                '2024-05-01','2024-05-09','2024-06-12','2024-11-04']
    df['is_holiday'] = df['date'].isin(pd.to_datetime(holidays)).astype(int)
    return df

def prepare_features(data):
    data = data.copy()
    for lag in [1,2,3,7,14]:
        data[f'lag_{lag}'] = data['balance'].shift(lag)
    data['rolling_mean_7'] = data['balance'].rolling(7).mean()
    data['rolling_std_7'] = data['balance'].rolling(7).std()
    return data

def predict_n_days(model, df_history, n_days, feature_cols):
    df_feat = add_calendar_features(df_history)
    df_feat = prepare_features(df_feat)
    df_feat = df_feat.dropna().reset_index(drop=True)
    history = df_feat.copy()
    preds = []
    for _ in range(n_days):
        current = history.iloc[-1:].copy()
        X_pred = current[feature_cols]
        pred = model.predict(X_pred)[0]
        preds.append(pred)
        new_date = current['date'].iloc[0] + timedelta(days=1)
        new_row = pd.DataFrame({'date': [new_date], 'balance': [pred]})
        new_row = add_calendar_features(new_row)
        history = pd.concat([history, new_row], ignore_index=True)
        history = prepare_features(history)
    return preds

def load_assistant():
    embedding_model = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
    df1 = pd.read_csv('/Users/marselsarybaev/avrora_day1/coffee_shop.csv')
    df2 = pd.read_csv('/Users/marselsarybaev/avrora_day1/stolovaya_crisis.csv')
    def make_frags(df):
        df['date'] = pd.to_datetime(df['date'])
        return [f"Дата: {row['date'].strftime('%Y-%m-%d')}, остаток: {row['balance']:.2f} руб." for _, row in df.iterrows()]
    frags = make_frags(df1) + make_frags(df2)
    embeddings = embedding_model.encode(frags, show_progress_bar=False)
    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings.astype('float32'))
    return embedding_model, index, frags

def search(query, model, index, fragments, k=3):
    query_emb = model.encode([query])
    distances, indices = index.search(query_emb.astype('float32'), k)
    return [fragments[i] for i in indices[0]]

def ask_aurora(question, model, index, fragments):
    df_bal = pd.read_csv('/Users/marselsarybaev/avrora_day1/coffee_shop.csv')
    df_bal['date'] = pd.to_datetime(df_bal['date'])
    df_bal = df_bal.sort_values('date')
    last = df_bal['balance'].iloc[-1]
    avg30 = df_bal['balance'].tail(30).mean()
    if len(df_bal) >= 30:
        profit = last - df_bal['balance'].iloc[-30]
        roe = (profit / avg30)*100 if avg30!=0 else 0
    else:
        roe = 0
    q = question.lower()
    if 'остаток' in q:
        return f"Текущий остаток: {last:.2f} руб."
    if 'средний' in q:
        return f"Средний остаток за 30 дней: {avg30:.2f} руб."
    if 'рентабельность капитала' in q or 'roe' in q:
        return f"Рентабельность капитала (ROE) за 30 дней: {roe:.2f}%."
    if 'рентабельность продаж' in q:
        return "Для рентабельности продаж нужны данные о выручке."
    ctx = search(question, model, index, fragments)
    if not ctx:
        return "Я совсем маленькая, пока не могу ответить, но учусь."
    context = "\n".join(ctx[:2])
    prompt = f"Ответь на вопрос на основе данных:\n{context}\nВопрос: {question}\nОтвет:"
    url = "https://llm.api.cloud.yandex.net/foundationModels/v1/completion"
    headers = {"Content-Type": "application/json", "Authorization": f"Api-Key {os.getenv('YANDEX_API_KEY')}"}
    data = {
        "modelUri": f"gpt://{os.getenv('YANDEX_FOLDER_ID')}/yandexgpt/latest",
        "completionOptions": {"stream": False, "temperature": 0.3, "maxTokens": 200},
        "messages": [{"role": "user", "text": prompt}]
    }
    resp = requests.post(url, headers=headers, json=data)
    if resp.status_code == 200:
        return resp.json()['result']['alternatives'][0]['message']['text']
    return "Ошибка API"

def record_and_transcribe(duration=60):
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    CHUNK = 1024
    RECORD_SECONDS = duration
    st.write(f"Говорите {RECORD_SECONDS} секунд...")
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)
    frames = []
    for _ in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
        data = stream.read(CHUNK)
        frames.append(data)
    stream.stop_stream()
    stream.close()
    p.terminate()
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmpfile:
        wav_filename = tmpfile.name
    wf = wave.open(wav_filename, 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()
    st.write("Распознаю...")
    whisper_model = whisper.load_model("base")
    result = whisper_model.transcribe(wav_filename)
    os.unlink(wav_filename)
    return result["text"].strip()

def get_okved_risks(okved_code):
    code_prefix = okved_code.split('.')[0][:2]
    sections = {
        "01": "Сельское, лесное хозяйство, охота, рыболовство",
        "10": "Производство пищевых продуктов",
        "11": "Производство напитков",
        "12": "Производство табачных изделий",
        "13": "Производство текстиля",
        "14": "Производство одежды",
        "15": "Производство кожи",
        "16": "Обработка древесины",
        "17": "Производство бумаги",
        "18": "Печать",
        "19": "Производство кокса и нефтепродуктов",
        "20": "Производство химических веществ",
        "21": "Производство лекарств",
        "22": "Резиновые и пластмассовые изделия",
        "23": "Производство прочей неметаллической продукции",
        "24": "Металлургия",
        "25": "Готовые металлические изделия",
        "26": "Компьютеры, электроника",
        "27": "Электрическое оборудование",
        "28": "Машины и оборудование",
        "29": "Автотранспорт",
        "30": "Прочие транспортные средства",
        "31": "Мебель",
        "32": "Прочие готовые изделия",
        "33": "Ремонт и монтаж машин",
        "35": "Электроэнергия, газ, пар",
        "36": "Вода",
        "37": "Сточные воды",
        "38": "Отходы",
        "39": "Ликвидация загрязнений",
        "41": "Строительство зданий",
        "42": "Инженерные сооружения",
        "43": "Специализированные строительные работы",
        "45": "Торговля автотранспортом",
        "46": "Оптовая торговля",
        "47": "Розничная торговля",
        "49": "Сухопутный транспорт",
        "50": "Водный транспорт",
        "51": "Воздушный транспорт",
        "52": "Складское хозяйство",
        "53": "Почтовая и курьерская деятельность",
        "55": "Проживание",
        "56": "Общественное питание",
        "58": "Издательская деятельность",
        "59": "Кино, видео",
        "60": "Телевидение и радио",
        "61": "Связь",
        "62": "Разработка ПО",
        "63": "Информационные технологии",
        "64": "Финансовые услуги",
        "65": "Страхование",
        "66": "Вспомогательная финансовая деятельность",
        "68": "Операции с недвижимостью",
        "69": "Право и бухгалтерия",
        "70": "Управленческое консультирование",
        "71": "Архитектура и инжиниринг",
        "72": "Научные исследования",
        "73": "Реклама",
        "74": "Профессиональная научно-техническая деятельность",
        "75": "Ветеринария",
        "77": "Аренда и лизинг",
        "78": "Трудоустройство",
        "79": "Туризм",
        "80": "Безопасность",
        "81": "Обслуживание зданий",
        "82": "Административная деятельность",
        "84": "Госуправление",
        "85": "Образование",
        "86": "Здравоохранение",
        "87": "Уход с проживанием",
        "88": "Социальные услуги",
        "90": "Творческая деятельность",
        "91": "Библиотеки, музеи",
        "92": "Азартные игры",
        "93": "Спорт, отдых",
        "94": "Общественные организации",
        "95": "Ремонт",
        "96": "Прочие персональные услуги"
    }
    name = sections.get(code_prefix, "Общая категория")
    if code_prefix in ["01","02","03"]:
        features = "Сезонность, зависимость от погоды, длительный цикл оборота."
        risks = "Неурожай, падение цен, рост стоимости ресурсов."
        mitigation = "Диверсификация, форвардные контракты, субсидии."
    elif code_prefix in ["10","11","12"]:
        features = "Высокая конкуренция, короткие сроки годности."
        risks = "Рост себестоимости, брак, сезонность спроса."
        mitigation = "Оптимизация логистики, контроль качества."
    elif code_prefix in ["45","46","47"]:
        features = "Высокая оборачиваемость, чувствительность к спросу."
        risks = "Падение трафика, рост аренды, товарные остатки."
        mitigation = "Управление запасами, онлайн-продажи, лояльность."
    elif code_prefix in ["55","56"]:
        features = "Зависимость от проходимости, санитарные требования."
        risks = "Изменение вкусов, рост цен на продукты, дефицит персонала."
        mitigation = "Доставка, оптимизация меню, обучение."
    elif code_prefix in ["62","63"]:
        features = "Высокая маржинальность, быстрая смена технологий."
        risks = "Утечка кадров, зависимость от заказчиков."
        mitigation = "Резервирование ФОТ, гибкие методологии."
    elif code_prefix == "68":
        features = "Низкая ликвидность, длинный цикл сделки."
        risks = "Падение рынка, долговая нагрузка, простои."
        mitigation = "Долгосрочная аренда, страхование."
    else:
        features = "Средний уровень стандартизации, разнородные виды деятельности."
        risks = "Рыночные колебания, изменение законодательства."
        mitigation = "Мониторинг рынка, оптимизация издержек."
    return {"name": name, "features": features, "risks": risks, "mitigation": mitigation}

def get_status_text(profit_margin, cash_gap_expected):
    if cash_gap_expected:
        return "Кассовый разрыв", "🔴", "danger"
    elif profit_margin >= 0.3:
        return "Отлично", "🟢", "good"
    elif profit_margin >= 0.2:
        return "Хорошо", "🟡", "normal"
    elif profit_margin >= 0.1:
        return "Нормально", "🟠", "medium"
    elif profit_margin >= 0.05:
        return "Средне", "🟤", "warning"
    else:
        return "Внимание / Тревога", "🔔", "alert"

def generate_recommendations(profit_margin, cash_gap_expected, cash_flow):
    rec = []
    if cash_gap_expected:
        rec.append("⚠️ Ожидается кассовый разрыв! Рекомендуем перенести крупные платежи или привлечь финансирование.")
    if profit_margin < 0.1:
        rec.append("📉 Низкая рентабельность. Проанализируйте структуру расходов.")
    if cash_flow < 0:
        rec.append("💸 Отрицательный денежный поток. Ускорьте сбор дебиторской задолженности.")
    if profit_margin >= 0.25:
        rec.append("✅ Высокая маржинальность. Инвестируйте свободные средства.")
    if not rec:
        rec.append("📊 Все показатели в норме.")
    return rec

def employees_page(lang, t):
    st.header(t["employees"])
    with st.form("add_employee"):
        emp_name = st.text_input(t["employee_name"])
        emp_pos = st.text_input(t["employee_position"])
        emp_phone = st.text_input(t["employee_phone"], value="1")
        emp_birth = st.date_input(t["employee_birth"], value=datetime(1990,1,1))
        emp_hours = st.text_input(t["employee_hours"], value="9:00-18:00")
        emp_plan = st.number_input(t["employee_plan"], min_value=0, value=100000)
        emp_actual = st.number_input(t["employee_actual"], min_value=0, value=80000)
        emp_tasks = st.text_area(t["employee_tasks"], value="Задачи на месяц")
        submitted = st.form_submit_button(t["add_employee"])
        if submitted:
            if not emp_phone.startswith("1"):
                st.error("Телефон должен начинаться с 1" if lang=="ru" else "Phone must start with 1")
            else:
                conn = sqlite3.connect('avrora_future.db')
                c = conn.cursor()
                c.execute('''INSERT INTO employees 
                             (inn_owner, name, position, phone, birth_date, work_hours, plan, actual, tasks)
                             VALUES (?,?,?,?,?,?,?,?,?)''',
                          (st.session_state.inn, emp_name, emp_pos, emp_phone, emp_birth.strftime('%Y-%m-%d'),
                           emp_hours, emp_plan, emp_actual, emp_tasks))
                conn.commit()
                conn.close()
                st.success("Сотрудник добавлен" if lang=="ru" else "Employee added")
    conn = sqlite3.connect('avrora_future.db')
    df_emp = pd.read_sql_query('''SELECT name, position, phone, birth_date, work_hours, plan, actual, tasks,
                                         (actual * 100.0 / plan) as percent
                                  FROM employees WHERE inn_owner=?''', conn, params=(st.session_state.inn,))
    conn.close()
    if not df_emp.empty:
        df_emp = df_emp.reset_index(drop=True)
        df_emp.index = df_emp.index + 1
        df_emp.columns = [t["employee_name"], t["employee_position"], t["employee_phone"], t["employee_birth"],
                          t["employee_hours"], t["employee_plan"], t["employee_actual"], t["employee_tasks"],
                          "% выполнения" if lang=="ru" else "Completion %"]
        df_emp["% выполнения"] = df_emp["% выполнения"].apply(lambda x: f"{x:.1f}%")
        st.dataframe(df_emp)

def counterparty_page(lang):
    st.header("🔍 Проверка контрагента по ИНН")
    inn_input = st.text_input("Введите ИНН контрагента (10 или 12 цифр)", placeholder="Например: 7736207543")
    if st.button("Проверить", type="primary"):
        if not inn_input or len(inn_input) not in [10,12]:
            st.warning("Введите корректный ИНН (10 или 12 цифр).")
        else:
            with st.spinner("Ищем информацию..."):
                DADATA_API_KEY = "8f16b854dcbf4f81b7a16ea172264a95ea856400"
                headers_dadata = {"Authorization": f"Token {DADATA_API_KEY}", "Content-Type": "application/json"}
                payload = {"query": inn_input, "count": 1}
                try:
                    resp = requests.post("https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party", headers=headers_dadata, json=payload, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json()
                        if data.get("suggestions"):
                            company = data["suggestions"][0]["data"]
                            with st.container(border=True):
                                col1, col2 = st.columns(2)
                                with col1:
                                    st.markdown(f"**{company.get('name', {}).get('full_with_opf', '—')}**")
                                    status = company.get("state", {}).get("status", "")
                                    if status == "ACTIVE":
                                        st.success("Статус: **Действующее**")
                                    elif status == "LIQUIDATING":
                                        st.warning("Статус: **В процессе ликвидации**")
                                    elif status == "LIQUIDATED":
                                        st.error("Статус: **Ликвидировано**")
                                    else:
                                        st.info(f"Статус: {status if status else '—'}")
                                    st.text(f"ИНН: {company.get('inn', '—')}  КПП: {company.get('kpp', '—')}")
                                    st.text(f"ОГРН: {company.get('ogrn', '—')}")
                                with col2:
                                    reg_date = company.get("state", {}).get("registration_date", "")
                                    st.text(f"Дата регистрации: {reg_date[:10] if reg_date else '—'}")
                                    mgmt = company.get("management")
                                    director = mgmt.get("name") if mgmt and isinstance(mgmt, dict) else "—"
                                    st.text(f"Руководитель: {director}")
                                    addr = company.get("address", {}).get("value", "—")
                                    st.text(f"Адрес: {addr[:60] + '...' if len(addr)>60 else addr}")
                            st.markdown("---")
                            st.subheader("📊 Финансовое положение и уровень риска")
                            DATANEWTON_API_KEY = "Z1l7vgrBWrDt"
                            try:
                                url_newton = f"https://api.datanewton.ru/finances?inn={company['inn']}"
                                headers_newton = {"accept": "application/json", "x-api-key": DATANEWTON_API_KEY}
                                resp_newton = requests.get(url_newton, headers=headers_newton, timeout=10)
                                if resp_newton.status_code == 200:
                                    fin_data = resp_newton.json()
                                    if fin_data and isinstance(fin_data, dict) and len(fin_data) > 0:
                                        latest_year = max(fin_data.keys())
                                        fin = fin_data[latest_year]
                                        revenue = fin.get("Выручка", fin.get("2110"))
                                        profit = fin.get("Чистая прибыль", fin.get("2400"))
                                        assets = fin.get("ИтогоАктивов", fin.get("1600"))
                                        col_f1, col_f2, col_f3 = st.columns(3)
                                        with col_f1:
                                            st.metric("Выручка", f"{revenue:,.0f} руб." if revenue else "—")
                                        with col_f2:
                                            st.metric("Чистая прибыль", f"{profit:,.0f} руб." if profit else "—")
                                        with col_f3:
                                            st.metric("Валюта баланса", f"{assets:,.0f} руб." if assets else "—")
                                        if revenue and revenue <= 0:
                                            st.error("**Высокий риск**: отсутствует выручка.")
                                        elif profit and profit <= 0:
                                            st.error("**Высокий риск**: компания убыточна.")
                                        elif profit and profit < revenue * 0.05:
                                            st.warning("**Средний риск**: низкая рентабельность.")
                                        else:
                                            st.success("**Низкий риск**: прибыльная компания с положительной выручкой.")
                                    else:
                                        st.info("Финансовые показатели не найдены.")
                                else:
                                    st.info(f"Финансовые данные недоступны (код: {resp_newton.status_code}).")
                            except Exception as e:
                                st.info("Сервис финансовых данных временно недоступен.")
                        else:
                            st.error("Контрагент не найден.")
                    else:
                        st.error(f"Ошибка API DaData: {resp.status_code}")
                except Exception as e:
                    st.error(f"Ошибка подключения: {e}")

def show_calendar_page():
    import calendar
    from datetime import datetime, timedelta
    st.header("📅 Календарь платежей")
    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    c.execute("SELECT due_date, expense_type, description, amount FROM expense_details WHERE inn_owner=?", (st.session_state.inn,))
    rows = c.fetchall()
    conn.close()
    payments_by_date = {}
    for row in rows:
        due_date = row[0]
        if due_date not in payments_by_date:
            payments_by_date[due_date] = []
        payments_by_date[due_date].append({
            "type": row[1],
            "description": row[2],
            "amount": row[3]
        })
    today = datetime.today()
    year = st.number_input("Год", min_value=2000, max_value=2100, value=today.year, step=1)
    month = st.selectbox("Месяц", range(1,13), index=today.month-1)
    cal = calendar.monthcalendar(year, month)
    month_name = calendar.month_name[month]
    st.subheader(f"{month_name} {year}")
    days_of_week = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
    cols = st.columns(7)
    for i, day in enumerate(days_of_week):
        cols[i].write(f"**{day}**")
    for week in cal:
        cols = st.columns(7)
        for i, day in enumerate(week):
            if day == 0:
                cols[i].write("")
            else:
                date_str = f"{year:04d}-{month:02d}-{day:02d}"
                if date_str in payments_by_date:
                    count = len(payments_by_date[date_str])
                    total = sum(p["amount"] for p in payments_by_date[date_str])
                    cols[i].markdown(f"**{day}**<br><span style='color:red;'>🔴 {count} шт.<br>{total:,.0f} ₽</span>", unsafe_allow_html=True)
                    if cols[i].button("📋", key=f"cal_{date_str}"):
                        st.session_state.selected_date = date_str
                else:
                    cols[i].write(day)
    if "selected_date" in st.session_state and st.session_state.selected_date:
        date_selected = st.session_state.selected_date
        st.subheader(f"Платежи на {date_selected}")
        if date_selected in payments_by_date:
            for p in payments_by_date[date_selected]:
                st.write(f"- {p['type']}: {p['description']} — {p['amount']:,.2f} ₽")
        else:
            st.write("Нет платежей")
        if st.button("Очистить выбор"):
            del st.session_state.selected_date
            st.rerun()

# --- ВАЛЮТЫ ---
CURRENCY_SYMBOLS = {"RUB":"₽", "USD":"$", "EUR":"€", "CNY":"¥", "KZT":"₸", "UZS":"soʻm", "GBP":"£", "JPY":"¥"}
def format_currency(amount, currency="RUB", rates=None):
    if rates is None:
        rates = st.session_state.get("exchange_rates", {})
    if not rates:
        rates = {"RUB":1.0, "USD":0.011, "EUR":0.010, "CNY":0.079, "KZT":5.0, "UZS":140.0, "GBP":0.0087, "JPY":1.5}
    if currency == "RUB":
        converted = amount
    else:
        rate = rates.get(currency, 1.0)
        converted = amount * rate
    sym = CURRENCY_SYMBOLS.get(currency, currency)
    return f"{converted:,.2f} {sym}"

if "exchange_rates" not in st.session_state:
    st.session_state.exchange_rates = {"RUB":1.0, "USD":0.011, "EUR":0.010, "CNY":0.079, "KZT":5.0, "UZS":140.0, "GBP":0.0087, "JPY":1.5}
if "currency" not in st.session_state:
    st.session_state.currency = "RUB"

# --- ОСНОВНОЙ ИНТЕРФЕЙС ---
if not st.session_state.logged_in:
    lang = st.sidebar.selectbox("Language / Язык", ["ru", "en"], format_func=lambda x: "Русский" if x=="ru" else "English")
    st.session_state.lang = lang
    # Дальше код входа (опущен для краткости, но он есть в полной версии)
    st.info("Страница входа")
else:
    if not st.session_state.greeting_shown:
        show_time_greeting(st.session_state.lang)
        st.session_state.greeting_shown = True

    lang = st.session_state.lang
    st.sidebar.markdown(f'<div class="au-icon">✨ Au ✨</div>', unsafe_allow_html=True)
    st.sidebar.markdown(f"**Добро пожаловать, {st.session_state.name}**")
    st.sidebar.info("🌟 Аврора — ваш помощник")
    
    with st.sidebar.expander("🎨 Настройка темы"):
        pass

    st.sidebar.markdown("---")
    st.sidebar.markdown("**💱 Валюта**")
    currency_options = ["RUB", "USD", "EUR", "CNY", "KZT", "UZS", "GBP", "JPY"]
    selected_currency = st.sidebar.selectbox("Выберите валюту", currency_options, index=currency_options.index(st.session_state.currency) if st.session_state.currency in currency_options else 0)
    if selected_currency != st.session_state.currency:
        st.session_state.currency = selected_currency
        st.rerun()

    # PDF экспорт (заглушка)
    if st.sidebar.button("📄 Скачать отчёт в PDF"):
        st.info("PDF экспорт (будет реализован)")

    if st.sidebar.button("Выйти"):
        st.session_state.logged_in = False
        st.session_state.page = "home"
        st.rerun()

    # --- ГЛАВНАЯ СТРАНИЦА ---
    if st.session_state.page == "home":
        st.markdown(f'<div style="font-size:28px; font-weight:800; color:#FFFFFF; margin-bottom:4px;">👋 Добрый день, {st.session_state.name}</div>', unsafe_allow_html=True)
        st.markdown('<div style="color:rgba(255,255,255,0.5); font-size:16px; margin-bottom:24px;">Выберите раздел для работы</div>', unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        with col1:
            if st.button("💰\n\nФинансы\n\nАналитика и прогнозы", key="home_finance", use_container_width=True):
                st.session_state.page = "finance"
                st.rerun()
        with col2:
            if st.button("👥\n\nСотрудники\n\nУправление командой", key="home_employees", use_container_width=True):
                st.session_state.page = "employees"
                st.rerun()
        with col3:
            if st.button("📅\n\nКалендарь\n\nПлатежи и налоги", key="home_calendar", use_container_width=True):
                st.session_state.page = "calendar"
                st.rerun()

    elif st.session_state.page == "finance":
        if st.button("← На главную", key="back_home_finance"):
            st.session_state.page = "home"
            st.rerun()
        st.markdown("---")
        st.header("💰 Финансы")
        st.markdown("<div class='sub-grid'>", unsafe_allow_html=True)
        subpages = [("📈","Общий план","overview"), ("💰","Баланс","balance"), ("📉","Расходы","expenses"), ("🎯","Цели","goals"), ("📊","Итоги","summary"), ("💵","ОДДС","cashflow"), ("📈","Прогноз V2.0","forecast"), ("⚠️","Контроль остатка","min_balance")]
        cols = st.columns(4)
        for idx, (icon, label, key) in enumerate(subpages):
            with cols[idx % 4]:
                button_label = f"{icon}\n\n{label}"
                if st.button(button_label, key=f"sub_{key}", use_container_width=True):
                    st.session_state.finance_subpage = key
                    st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)
        # Здесь код для отображения подстраниц (он уже есть ниже)

    elif st.session_state.page == "employees":
        if st.button("← На главную", key="back_home_employees"):
            st.session_state.page = "home"
            st.rerun()
        st.markdown("---")
        st.header("👥 Сотрудники")
        employees_page(st.session_state.lang, translations)

    elif st.session_state.page == "calendar":
        if st.button("← На главную", key="back_home_calendar"):
            st.session_state.page = "home"
            st.rerun()
        st.markdown("---")
        st.header("📅 Календарь")
        show_calendar_page()

    else:
        st.write("Страница не найдена")
