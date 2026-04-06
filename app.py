import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="BIST Günlük Analiz", layout="wide")
st.title("📈 BIST Günlük Trade Paneli")

# --- Giriş Alanı ---
st.sidebar.header("Ayarlar")
symbol = st.sidebar.text_input("Hisse (Örn: THYAO)", "THYAO").upper()
compare_symbol = st.sidebar.text_input("Korelasyon İçin (Örn: XU100)", "XU100").upper()

# BIST formatına çevir (.IS ekle)
ticker = f"{symbol}.IS" if not symbol.endswith(".IS") else symbol
comp_ticker = f"{compare_symbol}.IS" if not compare_symbol.endswith(".IS") else compare_symbol

# --- Veri Çekme ---
@st.cache_data
def load_data(t):
    return yf.download(t, period="60d", interval="1d")

df = load_data(ticker)
df_comp = load_data(comp_ticker)

if df.empty:
    st.error("Veri çekilemedi. Lütfen sembolü kontrol et.")
else:
    # --- 1. VOLUME PROFILE (VRP) & GRAFİK ---
    st.subheader(f"{symbol} Fiyat ve Hacim Profili")
    
    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, 
                        column_widths=[0.8, 0.2], horizontal_spacing=0.03)

    # Mum Grafiği
    fig.add_trace(go.Candlestick(
        x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
        name="Fiyat"
    ), row=1, col=1)

    # Manuel Volume Profile Hesaplama (Kütüphanesiz)
    bins = 15
    price_min, price_max = float(df['Low'].min()), float(df['High'].max())
    # Hacmi fiyat aralıklarına bölüyoruz
    df['PriceBin'] = pd.cut(df['Close'], bins=bins)
    vprofile = df.groupby('PriceBin', observed=True)['Volume'].sum()
    bin_centers = [i.mid for i in vprofile.index]

    fig.add_trace(go.Bar(
        x=vprofile.values, y=bin_centers, orientation='h',
        marker_color='rgba(0, 0, 255, 0.3)', name="Hacim Profili"
    ), row=1, col=2)

    fig.update_layout(xaxis_rangeslider_visible=False, height=500, showlegend=False)
    st.plotly_chart(fig, use_container_width=True)

    # --- 2. SON 30 GÜNLÜK LİSTE (+/- İŞARETLİ) ---
    st.subheader("📅 Son 30 Günlük Hareketler")
    
    last_30 = df.tail(30).copy()
    last_30['Fark'] = last_30['Close'].diff()
    last_30['Değişim %'] = (last_30['Close'].pct_change() * 100).round(2)
    
    # İşaretleme mantığı
    def get_sign(val):
        if val > 0: return "🟢 +"
        if val < 0: return "🔴 -"
        return "⚪ 0"

    last_30['Durum'] = last_30['Değişim %'].apply(get_sign)
    
    # Tabloyu güzelleştirme
    report_df = last_30[['Open', 'Close', 'Değişim %', 'Durum']].sort_index(ascending=False)
    st.dataframe(report_df, use_container_width=True)

    # --- 3. KORELASYON (PEARSON & SPEARMAN) ---
    st.subheader(f"🔗 {symbol} vs {compare_symbol} İlişkisi (Son 30 Gün)")
    
    # Verileri hizala
    combined = pd.concat([df['Close'], df_comp['Close']], axis=1).dropna().tail(30)
    combined.columns = ['Hisse', 'Endeks']
    
    p_corr = combined['Hisse'].corr(combined['Endeks'], method='pearson')
    s_corr = combined['Hisse'].corr(combined['Endeks'], method='spearman')

    c1, c2 = st.columns(2)
    c1.metric("Pearson (Doğrusal)", f"{p_corr:.2f}")
    c2.metric("Spearman (Trend Uyumu)", f"{s_corr:.2f}")
