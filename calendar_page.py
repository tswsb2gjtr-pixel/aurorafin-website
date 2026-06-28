import streamlit as st
import sqlite3
import calendar
from datetime import datetime, timedelta

def show_calendar_page():
    st.header("📅 Календарь платежей")
    st.caption("Здесь отображаются все запланированные платежи (включая налоги).")

    conn = sqlite3.connect('avrora_future.db')
    c = conn.cursor()
    c.execute("SELECT due_date, expense_type, description, amount FROM expense_details WHERE inn_owner=?", (st.session_state.inn,))
    rows = c.fetchall()
    conn.close()

    # Реальные платежи
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
    col1, col2 = st.columns(2)
    with col1:
        year = st.number_input("Год", min_value=2000, max_value=2100, value=today.year, step=1)
    with col2:
        month = st.selectbox("Месяц", range(1,13), index=today.month-1)

    # Генерация виртуальных налоговых напоминаний для текущего месяца
    # Выберем 20-е и 28-е числа каждого месяца (можно настроить)
    tax_dates = [20, 28]
    for day in tax_dates:
        if day <= calendar.monthrange(year, month)[1]:
            date_str = f"{year:04d}-{month:02d}-{day:02d}"
            if date_str not in payments_by_date:
                # Создаём виртуальный налоговый платёж
                payments_by_date[date_str] = [{
                    "type": "Налоги",
                    "description": "Автоматическое напоминание о налоге",
                    "amount": 0  # сумма не указана, только напоминание
                }]
            else:
                # Если уже есть платежи на эту дату, добавим пометку, что это налоговый день
                # Проверим, есть ли среди них налоги
                has_tax = any(p["type"] == "Налоги" for p in payments_by_date[date_str])
                if not has_tax:
                    payments_by_date[date_str].append({
                        "type": "Налоги",
                        "description": "Автоматическое напоминание о налоге",
                        "amount": 0
                    })

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
                    # Отфильтруем только виртуальные налоги, чтобы показывать их специально
                    virtual_tax = any(p["type"] == "Налоги" and p["amount"] == 0 for p in payments_by_date[date_str])
                    real_payments = [p for p in payments_by_date[date_str] if not (p["type"] == "Налоги" and p["amount"] == 0)]
                    count = len(payments_by_date[date_str])
                    total = sum(p["amount"] for p in payments_by_date[date_str])
                    # Если есть виртуальный налог, показываем его как напоминание
                    if virtual_tax:
                        color = "#FFA500"
                        label = "🧾 Налоги (напоминание)"
                        # Считаем только реальные суммы для total, но total уже включает 0, так что нормально
                    else:
                        # Проверим, есть ли реальные налоги
                        if any(p["type"] == "Налоги" for p in payments_by_date[date_str]):
                            color = "#FFA500"
                            label = "🧾 Налоги"
                        else:
                            color = "red"
                            label = "🔴"
                    cols[i].markdown(f"**{day}**<br><span style='color:{color};'>{label} {count} шт.<br>{total:,.0f} ₽</span>", unsafe_allow_html=True)
                    if cols[i].button("📋", key=f"cal_{date_str}"):
                        st.session_state.selected_date = date_str
                else:
                    cols[i].write(day)

    if "selected_date" in st.session_state and st.session_state.selected_date:
        date_selected = st.session_state.selected_date
        st.subheader(f"Платежи на {date_selected}")
        if date_selected in payments_by_date:
            for p in payments_by_date[date_selected]:
                if p["type"] == "Налоги" and p["amount"] == 0:
                    st.markdown(f"**🧾 {p['description']} (сумма не указана, добавьте вручную в разделе «Расходы»)**")
                elif p["type"] == "Налоги":
                    st.markdown(f"**🧾 {p['type']}: {p['description']} — {p['amount']:,.2f} ₽ (налоговый платёж)**")
                else:
                    st.write(f"- {p['type']}: {p['description']} — {p['amount']:,.2f} ₽")
        else:
            st.write("Нет платежей")
        if st.button("Очистить выбор"):
            del st.session_state.selected_date
            st.rerun()
