import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="BIST Analiz", layout="wide", initial_sidebar_state="expanded")

# CSS ile buton ve arayüzü biraz daha profesyonel gösterelim
st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; height: 3em; background-color: #ff4b4b; color: white; }
    .stDataFrame { border: 1px solid #31333F; border-radius: 5px; }
    </style>
    """, unsafe_allow_html=True)

st.title("🚀 BIST Profesyonel Günlük Trade Paneli")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Analiz Ayarları")
    
    # Kullanıcı girişleri
    symbol_raw = st.text_input("Hisse Sembolü", placeholder="Örn: THYAO, ASELS...").strip().upper()
    compare_raw = st.text_input("Korelasyon (Endeks/Hisse)", value="XU100").strip().upper()
    
    st.divider()
    
    # Analiz Butonu
    run_analysis = st.button("ANALİZİ BAŞLAT")

# Sembol Formatlama Fonksiyonu
def format_bist(s):
    if not s: return None
    return f"{s}.IS" if not s.endswith(".IS") else s

# --- ANA EKRAN MANTIĞI ---
if run_analysis:
    if not symbol_raw:
        st.warning("⚠️ Lütfen önce bir hisse sembolü giriniz.")
    else:
        with st.spinner('Veriler çekiliyor ve analiz ediliyor...'):
            ticker = format_bist(symbol_raw)
            comp_ticker = format_bist(compare_raw)
            
            # Veri Çekme
            df = yf.download(ticker, period="60d", interval="1d")
            df_comp = yf.download(comp_ticker, period="60d", interval="1d")

            if df.empty or len(df) < 5:
                st.error(f"❌ {symbol_raw} için veri bulunamadı! Sembolün doğruluğundan emin olun (Örn: THYAO).")
            else:
                # --- 1. GRAFİK VE VOLUME PROFILE ---
                col_left, col_right = st.columns([3, 1])
                
                with col_left:
                    st.subheader(f"📊 {symbol_raw} Teknik Görünüm")
                    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, 
                                        column_widths=[0.85, 0.15], horizontal_spacing=0.01)

                    # Mum Grafiği
                    fig.add_trace(go.Candlestick(
                        x=df.index, open=df['Open'], high=df['High'], 
                        low=df['Low'], close=df['Close'], name="Fiyat"
                    ), row=1, col=1)

                    # Hacim Profili Hesaplama
                    price_min, price_max = float(df['Low'].min()), float(df['High'].max())
                    bins = 20
                    df['PriceBin'] = pd.cut(df['Close'], bins=bins)
                    vprofile = df.groupby('PriceBin', observed=True)['Volume'].sum()
                    bin_centers = [i.mid for i in vprofile.index]

                    fig.add_trace(go.Bar(
                        x=vprofile.values, y=bin_centers, orientation='h',
                        marker_color='rgba(100, 150, 250, 0.4)', name="Hacim Profili"
                    ), row=1, col=2)

                    fig.update_layout(xaxis_rangeslider_visible=False, height=600, 
                                      template="plotly_dark", showlegend=False,
                                      margin=dict(l=20, r=20, t=20, b=20))
                    st.plotly_chart(fig, use_container_width=True)

                with col_right:
                    st.subheader("🔗 Korelasyon")
                    # Korelasyon Hesaplama
                    combined = pd.concat([df['Close'], df_comp['Close']], axis=1).dropna().tail(30)
                    combined.columns = ['Hisse', 'Endeks']
                    
                    if not combined.empty:
                        p_corr = combined['Hisse'].corr(combined['Endeks'], method='pearson')
                        s_corr = combined['Hisse'].corr(combined['Endeks'], method='spearman')
                        
                        st.metric("Pearson (Lineer)", f"{p_corr:.2f}")
                        st.metric("Spearman (Trend)", f"{s_corr:.2f}")
                        st.info(f"Bu veriler {compare_raw} baz alınarak son 30 gün için hesaplanmıştır.")
                    else:
                        st.warning("Korelasyon verisi yetersiz.")

                # --- 2. LİSTE ---
                st.divider()
                st.subheader("📅 Son 30 Günlük Fiyat Listesi")
                
                res_df = df.tail(30).copy()
                res_df['Günlük Değişim %'] = (res_df['Close'].pct_change() * 100).round(2)
                
                def color_sign(val):
                    if val > 0: return f"🟢 +%{val}"
                    if val < 0: return f"🔴 -%{abs(val)}"
                    return "⚪ 0.00"

                res_df['Durum'] = res_df['Günlük Değişim %'].apply(color_sign)
                
                # Sadece gerekli kolonları göster ve tarih formatını düzelt
                final_table = res_df[['Open', 'High', 'Low', 'Close', 'Volume', 'Durum']].sort_index(ascending=False)
                st.dataframe(final_table, use_container_width=True)

else:
    # Başlangıç Ekranı
    st.info("👈 Analize başlamak için sol taraftaki menüden bir sembol girin ve 'ANALİZİ BAŞLAT' butonuna tıklayın.")
    st.image("https://images.unsplash.com/photo-1611974717482-98aa03509162?q=80&w=1000", caption="BIST Data Analysis Environment")
