import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz
import altair as alt
import os

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="HR Monitor Pro", layout="wide")

# --- CSS AVANZATO: STOP FLICKER & UI ---
st.markdown("""
<style>
    /* Nasconde l'indicatore di caricamento in alto a destra e l'effetto sfumato */
    div[data-testid="stStatusWidget"] { display: none !important; }
    .stApp { transition: none !important; }
    
    /* Titolo e margini */
    .block-container { padding-top: 1rem !important; }
    h1 { margin-top: -30px !important; padding-bottom: 10px; font-size: 2rem !important; }

    /* Metriche compatte */
    [data-testid="stMetricValue"] { font-size: 1.5rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.8rem !important; }

    /* Pulsanti */
    .stButton > button { font-size: 0.8rem !important; width: 100%; }

    /* Cronometro */
    .timer-box {
        font-family: monospace;
        font-size: 2rem;
        color: #00e5ff;
        text-align: center;
        background: rgba(0,229,255,0.1);
        border: 1px solid #00e5ff;
        border-radius: 8px;
        padding: 10px;
        margin-bottom: 15px;
    }
</style>
""", unsafe_allow_html=True)

# --- LOGICA LINGUE ---
LANGS = {
    "🇮🇹 ITA": {
        "title": "📊❤️ Monitoraggio live frequenza cardiaca",
        "start_rec": "▶️ START REC", "stop_rec": "⏹️ STOP REC",
        "start_test": "🟢 INIZIO TEST", "stop_test": "🔴 FINE TEST",
        "fc_live": "FC (live)", "fc_avg": "Media FC", "fc_max": "FC max", "fc_min": "FC min",
        "clinical": "🩺 Test clinici", "wait": "⏳ Attendi 30s...", "ready": "Pronto",
        "respiro": "Respiro Profondo", "valsalva": "Valsalva", "tilt": "Tilt Test"
    },
    "🇬🇧 ENG": {
        "title": "📊❤️ Live HR Monitoring",
        "start_rec": "▶️ START REC", "stop_rec": "⏹️ STOP REC",
        "start_test": "🟢 START TEST", "stop_test": "🔴 STOP TEST",
        "fc_live": "HR (live)", "fc_avg": "Avg HR", "fc_max": "Max HR", "fc_min": "Min HR",
        "clinical": "🩺 Clinical Tests", "wait": "⏳ Wait 30s...", "ready": "Ready",
        "respiro": "Deep Breathing", "valsalva": "Valsalva", "tilt": "Tilt Test"
    }
}

# Auto-refresh (500ms)
st_autorefresh(interval=500, key="hr_refresher")

# --- INIZIALIZZAZIONE STATI ---
for key, default in {
    'history': pd.DataFrame(columns=['Sec', 'BPM']),
    'running': False,
    'active_test': None,
    'freeze_view': False,
    'test_data': pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec']),
    'markers': [],
    'results': {},
    'last_ts': ""
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

def get_bpm(token):
    if not token: return None
    try:
        r = requests.get("https://dev.pulsoid.net/api/v1/data/heart_rate/latest", 
                         headers={"Authorization": f"Bearer {token}"}, timeout=1)
        return r.json().get('data', {}).get('heart_rate') if r.status_code == 200 else None
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    lang = st.radio("Lang", ["🇮🇹 ITA", "🇬🇧 ENG"], horizontal=True, label_visibility="collapsed")
    t = LANGS[lang]
    st.markdown("---")
    token = st.text_input("Pulsoid Token", type="password")
    
    col1, col2 = st.columns(2)
    if col1.button(t["start_rec"], type="primary", disabled=not token):
        st.session_state.running = True
        st.session_state.freeze_view = False
    if col2.button(t["stop_rec"]):
        st.session_state.running = False
        st.session_state.active_test = None

    win = st.slider("Finestra (sec)", 10, 300, 60)
    
    if st.button("🗑 Reset", use_container_width=True):
        st.session_state.history = pd.DataFrame(columns=['Sec', 'BPM'])
        st.session_state.markers = []
        st.session_state.results = {}
        st.session_state.freeze_view = False
        st.rerun()

    st.markdown("---")
    st.caption("Danilo Bondi - UDA / UnivAq")

# --- LOGICA DATI ---
st.title(t["title"])
bpm = get_bpm(token)
curr_ts = datetime.now().strftime("%H:%M:%S")

if bpm and st.session_state.running:
    if st.session_state.last_ts != curr_ts:
        sec_now = len(st.session_state.history)
        new_row = pd.DataFrame([{'Sec': sec_now, 'BPM': bpm}])
        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
        st.session_state.last_ts = curr_ts
        
        if st.session_state.active_test:
            t_row = pd.DataFrame([{'T_Sec': len(st.session_state.test_data), 'BPM': bpm, 'G_Sec': sec_now}])
            st.session_state.test_data = pd.concat([st.session_state.test_data, t_row], ignore_index=True)

# --- UI: METRICHE ---
m1, m2, m3, m4 = st.columns(4)
hist = st.session_state.history
if not hist.empty:
    m1.metric(t["fc_live"], f"{bpm if bpm else hist['BPM'].iloc[-1]} BPM")
    m2.metric(t["fc_avg"], f"{hist['BPM'].mean():.1f}")
    m3.metric(t["fc_max"], f"{hist['BPM'].max():.0f}")
    m4.metric(t["fc_min"], f"{hist['BPM'].min():.0f}")
else:
    m1.metric(t["fc_live"], "--")
    m2.info("In attesa di START REC")

# --- CRONOMETRO & GRAFICO ---
if st.session_state.active_test:
    st.markdown(f"<div class='timer-box'>⏱️ TEST: {len(st.session_state.test_data)}s</div>", unsafe_allow_html=True)

if not hist.empty:
    # Selezione dati per il grafico (Live o Freeze)
    if st.session_state.freeze_view and not st.session_state.test_data.empty:
        df_plot = hist[(hist['Sec'] >= st.session_state.test_data['G_Sec'].min()-2) & 
                       (hist['Sec'] <= st.session_state.test_data['G_Sec'].max()+2)]
    else:
        df_plot = hist.tail(win)

    # Definizione Grafico Altair
    ch_base = alt.Chart(df_plot).encode(
        x=alt.X('Sec:Q', title="Secondi", scale=alt.Scale(nice=False)),
        y=alt.Y('BPM:Q', title="BPM", scale=alt.Scale(domain=[hist['BPM'].min()-5, hist['BPM'].max()+5]))
    )
    
    line = ch_base.mark_line(color='#ff4b4b', interpolate='monotone', size=3)
    area = ch_base.mark_area(color=alt.Gradient(
        gradient='linear', stops=[alt.GradientStop(color='red', offset=0), alt.GradientStop(color='transparent', offset=1)],
        x1=1, x2=1, y1=1, y2=0
    ), interpolate='monotone', opacity=0.3)
    
    layers = [area, line]
    
    # Marker verticali
    if st.session_state.markers:
        m_df = pd.DataFrame({'Sec': st.session_state.markers})
        layers.append(alt.Chart(m_df).mark_rule(color='#00e5ff', strokeDash=[5,5]).encode(x='Sec:Q'))

    st.altair_chart(alt.layer(*layers).interactive(), use_container_width=True)

# --- TEST CLINICI ---
st.markdown("---")
st.subheader(t["clinical"])
tabs = st.tabs([f"🌬️ {t['respiro']}", f"😤 {t['valsalva']}", f"🧍 {t['tilt']}"])

def handle_test(test_name):
    col_s, col_e = st.columns(2)
    # INIZIO TEST
    if col_s.button(t["start_test"], key=f"btn_s_{test_name}", disabled=not st.session_state.running):
        st.session_state.active_test = test_name
        st.session_state.test_data = pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec'])
        st.session_state.markers.append(len(st.session_state.history))
        st.session_state.freeze_view = False
        st.rerun()
    
    # FINE TEST
    if col_e.button(t["stop_test"], key=f"btn_e_{test_name}", disabled=st.session_state.active_test != test_name):
        if len(st.session_state.test_data) < 30:
            st.session_state.results[test_name] = "error"
        else:
            d = st.session_state.test_data
            st.session_state.freeze_view = True
            if test_name == "res":
                st.session_state.results[test_name] = {'max': d['BPM'].max(), 'min': d['BPM'].min(), 'ratio': d['BPM'].max()/d['BPM'].min()}
            elif test_name == "val":
                st.session_state.results[test_name] = {'max': d['BPM'].max(), 'min': d['BPM'].min(), 'ratio': d['BPM'].max()/d['BPM'].min()}
            elif test_name == "tilt":
                v15 = d.iloc[15]['BPM'] if len(d)>15 else d['BPM'].iloc[-1]
                v30 = d.iloc[30]['BPM'] if len(d)>30 else d['BPM'].iloc[-1]
                st.session_state.results[test_name] = {'v15': v15, 'v30': v30, 'ratio': v30/v15}
        
        st.session_state.active_test = None
        st.rerun()

    # Visualizzazione Risultati
    res = st.session_state.results.get(test_name)
    if res == "error":
        st.warning(t["wait"])
    elif isinstance(res, dict):
        st.success("Test Completato")
        cols = st.columns(3)
        if 'max' in res:
            cols[0].metric("Max", f"{res['max']:.0f}")
            cols[1].metric("Min", f"{res['min']:.0f}")
            cols[2].metric("Ratio", f"{res['ratio']:.2f}")
        else:
            cols[0].metric("15s", f"{res['v15']:.0f}")
            cols[1].metric("30s", f"{res['v30']:.0f}")
            cols[2].metric("30:15", f"{res['ratio']:.2f}")

with tabs[0]: handle_test("res")
with tabs[1]: handle_test("val")
with tabs[2]: handle_test("tilt")
