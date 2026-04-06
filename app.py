import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# Sayfa Ayarları
st.set_page_config(page_title="BIST Pro Terminal", layout="wide")

st.markdown("""
    <style>
    .stButton>button { width: 100%; border-radius: 5px; background-color: #ff4b4b; color: white; font-weight: bold; }
    input { text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

st.title("📊 BIST Profesyonel Trade & Likidite Terminali")

# --- SIDEBAR (PARAMETRE KONSOLU) ---
with st.sidebar:
    st.header("🔍 Analiz Parametreleri")
    symbol_raw = st.text_input("Sembol", placeholder="Örn: THYAO").strip().upper()
    compare_raw = st.text_input("Korelasyon Sembolü", value="XU100").strip().upper()
    
    st.divider()
    st.subheader("📅 Veri Aralığı Seçimi")
    # Varsayılan olarak son 60 günü getiriyoruz ama kullanıcı değiştirebilir
    default_start = datetime.now() - timedelta(days=60)
    start_date = st.date_input("Başlangıç Tarihi", default_start)
    end_date = st.date_input("Bitiş Tarihi", datetime.now())
    
    if start_date > end_date:
        st.error("Hata: Başlangıç tarihi bitişten sonra olamaz.")
        
    st.divider()
    run_analysis = st.button("ANALİZİ BAŞLAT")

def format_bist(s):
    if not s: return None
    return f"{s}.IS" if not s.endswith(".IS") else s

if run_analysis:
    if not symbol_raw:
        st.warning("⚠️ Lütfen önce bir sembol giriniz.")
    else:
        with st.spinner(f'{symbol_raw} verileri seçilen tarih aralığı için işleniyor...'):
            ticker = format_bist(symbol_raw)
            comp_ticker = format_bist(compare_raw)
            
            # KRİTİK: Veriyi seçilen tarih aralığında çekiyoruz
            df = yf.download(ticker, start=start_date, end=end_date, interval="1d")
            df_comp = yf.download(comp_ticker, start=start_date, end=end_date, interval="1d")

            if df.empty or len(df) < 2:
                st.error(f"❌ {symbol_raw} için bu tarih aralığında veri bulunamadı.")
            else:
                # MultiIndex sütun temizliği
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if isinstance(df_comp.columns, pd.MultiIndex): df_comp.columns = df_comp.columns.get_level_values(0)

                # --- HESAPLAMALAR (Tüm Seçilen Aralık İçin) ---
                df['Daily Range'] = (df['High'] - df['Low']).round(2)
                df['Pct_Change'] = df['Close'].pct_change() * 100
                # Amihud (Normalize: 1M hacim başına mutlak getiri)
                df['Amihud'] = (df['Pct_Change'].abs() / (df['Volume'] / 1000000)).round(4)
                
                # Analiz aralığı bilgisi
                actual_start = df.index[0].strftime('%Y-%m-%d')
                actual_end = df.index[-1].strftime('%Y-%m-%d')

                # --- 1. ANA FİYAT GRAFİĞİ ---
                col_left, col_right = st.columns([3, 1])
                with col_left:
                    st.subheader(f"🕯️ {symbol_raw} Fiyat & Hacim ({actual_start} / {actual_end})")
                    fig_main = make_subplots(rows=1, cols=2, shared_yaxes=True, column_widths=[0.85, 0.15], horizontal_spacing=0.01)
                    fig_main.add_trace(go.Candlestick(x=df.index, open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'], name="Fiyat"), row=1, col=1)
                    
                    # VRP (Seçilen tüm aralığa göre)
                    df['PriceBin'] = pd.cut(df['Close'], bins=15)
                    vprofile = df.groupby('PriceBin', observed=True)['Volume'].sum()
                    fig_main.add_trace(go.Bar(x=vprofile.values, y=[i.mid for i in vprofile.index], orientation='h', marker_color='rgba(255, 75, 75, 0.3)', name="Hacim"), row=1, col=2)
                    
                    fig_main.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark", showlegend=False, dragmode='pan')
                    st.plotly_chart(fig_main, use_container_width=True, config={'scrollZoom': True})

                with col_right:
                    st.subheader("🔗 Aralıklı Analiz")
                    combined = pd.concat([df['Close'], df_comp['Close']], axis=1).dropna()
                    combined.columns = ['Hisse', 'Endeks']
                    if not combined.empty:
                        st.metric(f"Pearson ({symbol_raw})", f"{combined['Hisse'].corr(combined['Endeks']):.2f}")
                        st.write(f"**Seçilen Dönem Ort. Amihud:** {df['Amihud'].mean():.4f}")
                        st.write(f"**Seçilen Dönem Ort. Range:** {df['Daily Range'].mean():.2f}")
                        st.caption("Veriler seçtiğiniz başlangıç ve bitiş tarihleri arasını kapsar.")

                # --- 2. DETAY VERİ LİSTESİ ---
                st.divider()
                st.subheader(f"📅 Veri Listesi ({len(df)} İşlem Günü)")
                res_df = df.copy()
                res_df['Değişim %'] = res_df['Pct_Change'].apply(lambda x: f"🟢 +%{x:.2f}" if x > 0 else f"🔴 -%{abs(x):.2f}" if x < 0 else "⚪ 0.00")
                st.dataframe(res_df[['Open', 'High', 'Low', 'Close', 'Volume', 'Daily Range', 'Amihud', 'Değişim %']].sort_index(ascending=False), use_container_width=True, height=400)

                # --- 3. DUAL AXIS GRAFİKLER ---
                st.divider()
                
                # Grafik 1: Amihud vs Daily Range
                st.subheader("📉 Amihud vs Daily Range")
                fig1 = go.Figure()
                fig1.add_trace(go.Scatter(x=df.index, y=df['Amihud'], name="Amihud", line=dict(color='#00FFCC', width=2.5), yaxis="y1"))
                fig1.add_trace(go.Scatter(x=df.index, y=df['Daily Range'], name="Daily Range", line=dict(color='#FFD700', width=2.5, dash='dot'), yaxis="y2"))
                fig1.update_layout(template="plotly_dark", height=400, yaxis=dict(title="Amihud", tickfont=dict(color="#00FFCC")), yaxis2=dict(title="Daily Range", tickfont=dict(color="#FFD700"), anchor="x", overlaying="y", side="right"), hovermode="x unified", dragmode='pan')
                st.plotly_chart(fig1, use_container_width=True, config={'scrollZoom': True})

                # Grafik 2: Close vs Daily Range
                st.subheader("📈 Close vs Daily Range")
                fig2 = go.Figure()
                fig2.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Close", line=dict(color='#FFFFFF', width=2), yaxis="y1"))
                fig2.add_trace(go.Scatter(x=df.index, y=df['Daily Range'], name="Daily Range", line=dict(color='#FFD700', width=2.5), yaxis="y2"))
                fig2.update_layout(template="plotly_dark", height=400, yaxis=dict(title="Fiyat", tickfont=dict(color="#FFFFFF")), yaxis2=dict(title="Daily Range", tickfont=dict(color="#FFD700"), anchor="x", overlaying="y", side="right"), hovermode="x unified", dragmode='pan')
                st.plotly_chart(fig2, use_container_width=True, config={'scrollZoom': True})

                # Grafik 3: Close vs Amihud
                st.subheader("🧪 Close vs Amihud")
                fig3 = go.Figure()
                fig3.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Close", line=dict(color='#FFFFFF', width=2), yaxis="y1"))
                fig3.add_trace(go.Scatter(x=df.index, y=df['Amihud'], name="Amihud", line=dict(color='#00FFCC', width=2.5), yaxis="y2"))
                fig3.update_layout(template="plotly_dark", height=400, yaxis=dict(title="Fiyat", tickfont=dict(color="#FFFFFF")), yaxis2=dict(title="Amihud", tickfont=dict(color="#00FFCC"), anchor="x", overlaying="y", side="right"), hovermode="x unified", dragmode='pan')
                st.plotly_chart(fig3, use_container_width=True, config={'scrollZoom': True})

else:
    st.info("👈 Tarih aralığını seçin ve sembolü girerek 'ANALİZİ BAŞLAT'a basın.")
