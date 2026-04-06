import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="BIST Terminal", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; background-color: #ff4b4b; color: white; font-weight: bold; }
    input { text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 BIST Profesyonel Günlük Trade & Likidite Terminali")

# --- SIDEBAR ---
with st.sidebar:
    st.header("🔍 Parametreler")
    symbol_raw = st.text_input("Sembol", placeholder="Örn: THYAO").strip().upper()
    compare_raw = st.text_input("Korelasyon Sembolü", value="XU100").strip().upper()
    st.divider()
    run_analysis = st.button("ANALİZİ BAŞLAT")

def format_bist(s):
    if not s: return None
    return f"{s}.IS" if not s.endswith(".IS") else s

if run_analysis:
    if not symbol_raw:
        st.warning("⚠️ Lütfen bir sembol giriniz.")
    else:
        with st.spinner('Analiz ediliyor...'):
            ticker = format_bist(symbol_raw)
            comp_ticker = format_bist(compare_raw)
            
            # Daha uzun veri çekiyoruz ki sağa sola kaydırırken boşluk kalmasın
            df = yf.download(ticker, period="1y", interval="1d")
            df_comp = yf.download(comp_ticker, period="1y", interval="1d")

            if df.empty or len(df) < 5:
                st.error(f"❌ {symbol_raw} verisi bulunamadı.")
            else:
                # Sütun temizliği
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if isinstance(df_comp.columns, pd.MultiIndex): df_comp.columns = df_comp.columns.get_level_values(0)

                # --- HESAPLAMALAR ---
                df['Daily Range'] = (df['High'] - df['Low']).round(2)
                df['Pct_Change'] = df['Close'].pct_change() * 100
                df['Amihud'] = (df['Pct_Change'].abs() / (df['Volume'] / 1000000)).round(4)

                # --- 1. GRAFİK (TAM İNTERAKTİF) ---
                col_left, col_right = st.columns([3, 1])
                
                with col_left:
                    st.subheader(f"📊 {symbol_raw} Teknik Görünüm")
                    # Son 60 günü başlangıçta göster ama tüm yılı yükle (sağa-sola kaydırma için)
                    view_df = df.tail(100) 
                    
                    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, 
                                        column_widths=[0.85, 0.15], horizontal_spacing=0.01)
                    
                    # Candlestick
                    fig.add_trace(go.Candlestick(
                        x=df.index, open=df['Open'], high=df['High'], 
                        low=df['Low'], close=df['Close'], name=symbol_raw
                    ), row=1, col=1)

                    # Hacim Profili (VRP)
                    bins = 20
                    df_vrp = df.tail(30) # VRP'yi son 30 güne göre hesapla
                    df_vrp['PriceBin'] = pd.cut(df_vrp['Close'], bins=bins)
                    vprofile = df_vrp.groupby('PriceBin', observed=True)['Volume'].sum()
                    bin_centers = [i.mid for i in vprofile.index]

                    fig.add_trace(go.Bar(
                        x=vprofile.values, y=bin_centers, orientation='h',
                        marker_color='rgba(255, 75, 75, 0.3)', name="Hacim Profili"
                    ), row=1, col=2)

                    # İNTERAKTİF AYARLAR
                    fig.update_layout(
                        xaxis_rangeslider_visible=True, # Sağa sola kaydırmak için slider
                        dragmode='pan', # Tıklayıp sürükleyince sağa-sola kayar
                        height=600,
                        template="plotly_dark",
                        showlegend=False,
                        xaxis=dict(range=[df.index[-60], df.index[-1]]) # Başlangıçta son 60 günü göster
                    )
                    
                    # scrollZoom: True -> Mouse tekerleğiyle yakınlaşma/uzaklaşma
                    st.plotly_chart(fig, use_container_width=True, config={
                        'scrollZoom': True,
                        'displayModeBar': True,
                        'modeBarButtonsToAdd': ['drawline', 'drawopenpath', 'eraseshape']
                    })

                with col_right:
                    st.subheader("🔗 Korelasyon")
                    combined = pd.concat([df['Close'], df_comp['Close']], axis=1).dropna().tail(30)
                    combined.columns = ['Hisse', 'Endeks']
                    
                    if not combined.empty:
                        p_corr = combined['Hisse'].corr(combined['Kiyas'], method='pearson') if 'Kiyas' in combined else combined['Hisse'].corr(combined['Endeks'])
                        st.metric(f"{symbol_raw} vs {compare_raw}", f"{p_corr:.2f}")
                        st.write(f"**Günlük Range Ort:** {df['Daily Range'].tail(30).mean():.2f}")
                        st.write(f"**Amihud Ort:** {df['Amihud'].tail(30).mean():.4f}")

                # --- 2. TABLO ---
                st.divider()
                st.subheader("📅 Detay Veri Listesi")
                
                def color_sign(val):
                    if val > 0: return f"🟢 +%{val:.2f}"
                    if val < 0: return f"🔴 -%{abs(val):.2f}"
                    return "⚪ 0.00"

                res_df = df.tail(30).copy()
                res_df['Değişim %'] = res_df['Pct_Change'].apply(color_sign)
                
                # Volume yanında Daily Range ve Amihud
                table_final = res_df[['Open', 'High', 'Low', 'Close', 'Volume', 'Daily Range', 'Amihud', 'Değişim %']].sort_index(ascending=False)
                st.dataframe(table_final, use_container_width=True, height=500)
