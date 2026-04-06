import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import pearsonr, spearmanr
from datetime import datetime, timedelta

# Sayfa Ayarları
st.set_page_config(page_title="BIST Günlük Trade Analiz", layout="wide")
st.title("📈 BIST Günlük Trade Tarayıcı")

# --- SIDEBAR (Giriş Alanı) ---
st.sidebar.header("Parametreler")
ticker_input = st.sidebar.text_input("Ana Hisse (Örn: THYAO):", value="THYAO").upper()
compare_input = st.sidebar.text_input("Karşılaştırma (Örn: XU100):", value="XU100").upper()

# BIST için sonuna .IS ekleme kontrolü
def format_ticker(t):
    return f"{t}.IS" if not t.endswith(".IS") else t

ticker = format_ticker(ticker_input)
compare_ticker = format_ticker(compare_input)

days_to_look = st.sidebar.slider("Gözlem Süresi (Gün)", 30, 365, 60)

# --- VERİ ÇEKME ---
@st.cache_data
def get_data(symbol, period="1y"):
    df = yf.download(symbol, period=period, interval="1d")
    return df

data = get_data(ticker)
comp_data = get_data(compare_ticker)

if data.empty:
    st.error("Hisse verisi bulunamadı. Lütfen sembolü kontrol edin.")
else:
    # Son 30 Günü Ayır
    df_30 = data.tail(30).copy()
    
    # --- 1. GÖRSELLEŞTİRME: CANDLESTICK & VOLUME PROFILE (VRP) ---
    st.subheader(f"{ticker_input} Teknik Görünüm ve Volume Profile")
    
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, 
                        column_widths=[0.8, 0.2], horizontal_spacing=0.02)

    # Candlestick
    fig.add_trace(go.Candlestick(
        x=data.index[-days_to_look:],
        open=data['Open'][-days_to_look:],
        high=data['High'][-days_to_look:],
        low=data['Low'][-days_to_look:],
        close=data['Close'][-days_to_look:],
        name="Fiyat"
    ), row=1, col=1)

    # Volume Profile Hesaplama (Basit)
    price_buckets = pd.cut(data['Close'][-days_to_look:], bins=20)
    vprofile = data['Volume'][-days_to_look:].groupby(price_buckets).sum()
    bin_centers = [interval.mid for interval in vprofile.index]

    fig.add_trace(go.Bar(
        x=vprofile.values,
        y=bin_centers,
        orientation='h',
        marker_color='rgba(100, 150, 250, 0.5)',
        name="Hacim Profili"
    ), row=1, col=2)

    fig.update_layout(xaxis_rangeslider_visible=False, height=600, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- 2. FİYAT LİSTESİ (SON 30 GÜN) ---
    st.subheader("📅 Son 30 Günlük Fiyat Hareketleri")
    
    df_30['Günlük Fark (%)'] = df_30['Close'].pct_change() * 100
    df_30['Durum'] = df_30['Günlük Fark (%)'].apply(lambda x: "🟢 +" if x > 0 else "🔴 -" if x < 0 else "⚪ 0")
    
    # Tabloyu düzenleme
    display_df = df_30[['Open', 'High', 'Low', 'Close', 'Volume', 'Günlük Fark (%)', 'Durum']].copy()
    display_df.index = display_df.index.strftime('%Y-%m-%d')
    st.dataframe(display_df.sort_index(ascending=False), use_container_width=True)

    # --- 3. KORELASYON ANALİZİ ---
    st.subheader(f"🔗 Korelasyon Analizi ({ticker_input} vs {compare_input})")
    
    # Verileri birleştirme
    combined = pd.concat([data['Close'], comp_data['Close']], axis=1).dropna()
    combined.columns = ['Main', 'Comp']
    
    if len(combined) > 30:
        p_corr, _ = pearsonr(combined['Main'].tail(30), combined['Comp'].tail(30))
        s_corr, _ = spearmanr(combined['Main'].tail(30), combined['Comp'].tail(30))
        
        col1, col2 = st.columns(2)
        col1.metric("Pearson (Lineer İlişki)", f"{p_corr:.2f}")
        col2.metric("Spearman (Sıralı İlişki)", f"{s_corr:.2f}")
        
        st.info("""
        **Pearson:** Fiyat hareketlerinin doğrusal benzerliğini ölçer. 
        **Spearman:** Trendlerin (yönün) ne kadar uyumlu olduğunu ölçer (aykırı değerlere daha dayanıklıdır).
        """)
