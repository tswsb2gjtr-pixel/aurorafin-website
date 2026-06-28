from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import io
from datetime import datetime
import streamlit as st
import os

# Символы валют (скопированы для независимости)
CURRENCY_SYMBOLS = {
    "RUB": "₽",
    "USD": "$",
    "EUR": "€",
    "CNY": "¥",
    "KZT": "₸",
    "UZS": "soʻm",
    "GBP": "£",
    "JPY": "¥"
}

def convert_currency(amount, from_currency, to_currency, rates):
    if to_currency == from_currency:
        return amount
    if from_currency not in rates or to_currency not in rates:
        return amount
    if from_currency == "RUB":
        rub_amount = amount
    else:
        rub_amount = amount / rates[from_currency]
    if to_currency == "RUB":
        return rub_amount
    else:
        return rub_amount * rates[to_currency]

def format_currency(amount, currency="RUB", rates=None):
    if rates is None:
        rates = st.session_state.get("exchange_rates", {})
    if not rates:
        sym = CURRENCY_SYMBOLS.get(currency, currency)
        return f"{amount:,.2f} {sym}"
    converted = convert_currency(amount, "RUB", currency, rates)
    sym = CURRENCY_SYMBOLS.get(currency, currency)
    return f"{converted:,.2f} {sym}"

# Шрифт
FONT_NAME = 'Helvetica'
font_paths = [
    '/System/Library/Fonts/Supplemental/Arial.ttf',
    '/System/Library/Fonts/Arial.ttf',
    '/Library/Fonts/Arial.ttf'
]
for path in font_paths:
    if os.path.exists(path):
        try:
            pdfmetrics.registerFont(TTFont('Arial', path))
            FONT_NAME = 'Arial'
            break
        except:
            pass

def generate_pdf_report():
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2*cm, leftMargin=2*cm, topMargin=2*cm, bottomMargin=2*cm)
    styles = getSampleStyleSheet()
    
    styleH = ParagraphStyle(name='Heading1', parent=styles['Heading1'], fontName=FONT_NAME, fontSize=16, alignment=1)
    styleH2 = ParagraphStyle(name='Heading2', parent=styles['Heading2'], fontName=FONT_NAME, fontSize=14)
    styleN = ParagraphStyle(name='Normal', parent=styles['Normal'], fontName=FONT_NAME, fontSize=11)
    styleB = ParagraphStyle(name='Body', parent=styles['Normal'], fontName=FONT_NAME, fontSize=11)
    
    currency = st.session_state.get('currency', 'RUB')
    rates = st.session_state.get('exchange_rates', {})
    
    elements = []
    elements.append(Paragraph("Aurora Fin — Финансовый отчёт", styleH))
    elements.append(Spacer(1, 0.5*cm))
    elements.append(Paragraph(f"Дата формирования: {datetime.now().strftime('%d.%m.%Y %H:%M')}", styleN))
    elements.append(Spacer(1, 0.7*cm))
    
    balance = st.session_state.get("balance", 1_500_000)
    revenue = st.session_state.get("revenue", 4_500_000)
    expenses = st.session_state.get("expenses", 3_000_000)
    profit = revenue - expenses
    
    data = [
        ["Показатель", "Сумма"],
        ["Текущий баланс", format_currency(balance, currency, rates)],
        ["Выручка", format_currency(revenue, currency, rates)],
        ["Расходы", format_currency(expenses, currency, rates)],
        ["Прибыль", format_currency(profit, currency, rates)]
    ]
    table = Table(data, colWidths=[6*cm, 6*cm])
    table.setStyle(TableStyle([
        ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4a6cf7')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.white),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTSIZE', (0,0), (-1,0), 12),
        ('BOTTOMPADDING', (0,0), (-1,0), 12),
        ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f0f4ff')),
        ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d0d8e8')),
        ('FONTSIZE', (0,1), (-1,-1), 11),
    ]))
    elements.append(table)
    elements.append(Spacer(1, 0.7*cm))
    
    elements.append(Paragraph("Прогноз кассовых разрывов на 7 дней", styleH2))
    elements.append(Spacer(1, 0.3*cm))
    
    import __main__ as main
    if hasattr(main, 'forecast_cash_gap'):
        forecast_dates, forecast_vals = main.forecast_cash_gap(7)
        forecast_data = [["Дата", "Прогнозный остаток"]]
        for d, v in zip(forecast_dates, forecast_vals):
            forecast_data.append([d.strftime('%d.%m.%Y'), format_currency(v, currency, rates)])
        forecast_table = Table(forecast_data, colWidths=[4*cm, 8*cm])
        forecast_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), FONT_NAME),
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#4a6cf7')),
            ('TEXTCOLOR', (0,0), (-1,0), colors.white),
            ('ALIGN', (0,0), (-1,-1), 'CENTER'),
            ('FONTSIZE', (0,0), (-1,0), 11),
            ('BOTTOMPADDING', (0,0), (-1,0), 10),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f8faff')),
            ('GRID', (0,0), (-1,-1), 1, colors.HexColor('#d0d8e8')),
            ('FONTSIZE', (0,1), (-1,-1), 10),
        ]))
        elements.append(forecast_table)
    else:
        elements.append(Paragraph("Прогноз недоступен", styleN))
    
    elements.append(Spacer(1, 0.7*cm))
    elements.append(Paragraph("© Aurora Fin — интеллектуальная панель управления финансами", styleN))
    
    doc.build(elements)
    pdf_data = buffer.getvalue()
    buffer.close()
    
    st.download_button(
        label="📥 Скачать PDF" if st.session_state.lang == "ru" else "📥 Download PDF",
        data=pdf_data,
        file_name=f"aurora_fin_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf",
        mime="application/pdf"
    )
