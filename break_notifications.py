import streamlit as st
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import os
from dotenv import load_dotenv

def send_email(to_email, subject, body):
    load_dotenv()
    SMTP_HOST = os.getenv('SMTP_HOST')
    SMTP_PORT = int(os.getenv('SMTP_PORT', 465))
    SMTP_USER = os.getenv('SMTP_USER')
    SMTP_PASS = os.getenv('SMTP_PASS')
    SMTP_FROM = os.getenv('SMTP_FROM')
    if not SMTP_HOST or not SMTP_USER or not SMTP_PASS:
        print("SMTP не настроен")
        return
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = SMTP_FROM
    msg['To'] = to_email
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_FROM, to_email, msg.as_string())
        print(f"Email отправлен на {to_email}")
    except Exception as e:
        print(f"Ошибка: {e}")

def get_break_date(forecast_dates, forecast_vals):
    min_balance = min(forecast_vals)
    if min_balance >= 0:
        return None, min_balance
    for i, val in enumerate(forecast_vals):
        if val < 0:
            return forecast_dates[i], min_balance
    return None, min_balance

def check_and_send_break_notification(forecast_dates, forecast_vals, user_email):
    if not user_email:
        st.warning("Email пользователя не указан")
        return
    break_date, min_bal = get_break_date(forecast_dates, forecast_vals)
    if break_date is None:
        return
    today = datetime.today().date()
    days_until_break = (break_date - today).days
    if 0 <= days_until_break <= 7:
        if not st.session_state.get("break_notification_sent", False):
            subject = "⚠️ Предупреждение о кассовом разрыве"
            body = f"""Здравствуйте!

Прогноз показывает, что {break_date.strftime('%d.%m.%Y')} остаток на счете станет отрицательным (минимальный остаток: {min_bal:,.2f} ₽).

Рекомендуем принять меры: перенести крупные платежи, ускорить инкассацию или привлечь финансирование.

С уважением,
Aurora Fin"""
            send_email(user_email, subject, body)
            st.session_state.break_notification_sent = True
            st.success(f"Уведомление отправлено на {user_email}")
