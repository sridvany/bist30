import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Sayfa Ayarları
st.set_page_config(page_title="BIST Analiz Paneli", layout="wide")

# CSS: Sayfanın genel kaydırma özelliğini garantiye alalım
st.markdown("""
    <style>
    .main { overflow-y: auto !important; }
    .stButton>button { width: 100%; border-radius: 5px; background-color: #ff4b4b; color: white; font-weight: bold; }
    input { text-transform: uppercase; }
    </style>
    """, unsafe_allow_html=True)

st.title("📈 BIST Günlük Trade & Likidite Terminali")

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
        with st.spinner('Veriler işleniyor...'):
            ticker = format_bist(symbol_raw)
            comp_ticker = format_bist(compare_raw)
            
            df = yf.download(ticker, period="60d", interval="1d")
            df_comp = yf.download(comp_ticker, period="60d", interval="1d")

            if df.empty or len(df) < 5:
                st.error(f"❌ {symbol_raw} için veri çekilemedi.")
            else:
                # MultiIndex sütun temizliği
                if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)
                if isinstance(df_comp.columns, pd.MultiIndex): df_comp.columns = df_comp.columns.get_level_values(0)

                # --- HESAPLAMALAR ---
                df['Daily Range'] = (df['High'] - df['Low']).round(2)
                df['Pct_Change'] = df['Close'].pct_change() * 100
                # Amihud (Normalize edilmiş: 1M hacim başına düşen mutlak getiri)
                df['Amihud'] = (df['Pct_Change'].abs() / (df['Volume'] / 1000000)).round(4)

                # --- 1. GÖRSELLEŞTİRME ---
                col_left, col_right = st.columns([3, 1])
                
                with col_left:
                    st.subheader(f"📊 {symbol_raw} Grafik")
                    fig = make_subplots(rows=1, cols=2, shared_yaxes=True, 
                                        column_widths=[0.85, 0.15], horizontal_spacing=0.01)
                    
                    fig.add_trace(go.Candlestick(
                        x=df.index, open=df['Open'], high=df['High'], 
                        low=df['Low'], close=df['Close'], name="Fiyat"
                    ), row=1, col=1)

                    # Hacim Profili
                    bins = 15
                    df['PriceBin'] = pd.cut(df['Close'], bins=bins)
                    vprofile = df.groupby('PriceBin', observed=True)['Volume'].sum()
                    bin_centers = [i.mid for i in vprofile.index]

                    fig.add_trace(go.Bar(
                        x=vprofile.values, y=bin_centers, orientation='h',
                        marker_color='rgba(255, 75, 75, 0.3)', name="Hacim"
                    ), row=1, col=2)

                    # SCROLL FIX: 'scrollZoom': False yaparak mouse scroll'u boşa çıkardık
                    fig.update_layout(xaxis_rangeslider_visible=False, height=500, template="plotly_dark", showlegend=False)
                    st.plotly_chart(fig, use_container_width=True, config={'scrollZoom': False})

                with col_right:
                    st.subheader("🔗 İlişki")
                    combined = pd.concat([df['Close'], df_comp['Close']], axis=1).dropna().tail(30)
                    combined.columns = ['Hisse', 'Endeks']
                    
                    if not combined.empty:
                        p_corr = combined['Hisse'].corr(combined['Endeks'], method='pearson')
                        s_corr = combined['Hisse'].corr(combined['Endeks'], method='spearman')
                        st.metric(f"Pearson ({symbol_raw})", f"{p_corr:.2f}")
                        st.metric(f"Spearman ({compare_raw})", f"{s_corr:.2f}")
                        st.write(f"**Amihud (30G Ort):** {df['Amihud'].tail(30).mean():.3f}")

                # --- 2. TABLO (Daily Range ve Amihud, Volume Yanında) ---
                st.divider()
                st.subheader("📅 Son 30 Günlük Veri Seti")
                
                def color_sign(val):
                    if val > 0: return f"🟢 +%{val:.2f}"
                    if val < 0: return f"🔴 -%{abs(val):.2f}"
                    return "⚪ 0.00"

                res_df = df.tail(30).copy()
                res_df['Değişim %'] = res_df['Pct_Change'].apply(color_sign)
                
                # Sütunları tam istediğin sıraya dizdik: Volume yanına Daily Range ve Amihud
                final_cols = ['Open', 'High', 'Low', 'Close', 'Volume', 'Daily Range', 'Amihud', 'Değişim %']
                table_final = res_df[final_cols].sort_index(ascending=False)
                
                # Tablo yüksekliğini sayfanın geri kalanına göre ayarladık
                st.dataframe(table_final, use_container_width=True, height=600)

else:
    st.info("👈 Analize başlamak için sol taraftan sembol girip 'ANALİZİ BAŞLAT'a basın.")
