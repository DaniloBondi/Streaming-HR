import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz
import altair as alt
import os

st.set_page_config(page_title="Monitoraggio FC / HR Monitor", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
<style>
    /* Sposta il titolo più in alto */
    .block-container {
        padding-top: 1.5rem !important;
    }
    h1 {
        margin-top: -40px !important;
        padding-bottom: 20px;
    }
    /* Riduci font metriche */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
    }
    /* Riduci font pulsanti START/STOP REC */
    .stButton > button {
        font-size: 0.8rem !important;
        padding: 0.2rem 0.5rem;
    }
    /* Stile Cronometro */
    .timer-box {
        font-family: 'Courier New', Courier, monospace;
        font-size: 2.5rem;
        color: #00e5ff;
        text-align: center;
        font-weight: bold;
        background: rgba(0,0,0,0.2);
        border-radius: 10px;
        padding: 5px;
        margin-bottom: 10px;
        border: 1px solid #00e5ff;
    }
</style>
""", unsafe_allow_html=True)

LANGUAGES = {
    "🇮🇹 ITA": {
        "main_title": "📊❤️ Monitoraggio live frequenza cardiaca",
        "token_label": "🔑 Token Pulsoid",
        "token_help": "Inserisci qui il tuo Token generato da Pulsoid.",
        "btn_start": "▶️ START REC",
        "btn_stop": "⏹️ STOP REC",
        "btn_test_start": "🟢 INIZIO TEST",
        "btn_test_end": "🔴 FINE TEST",
        "test_clinical_title": "🩺 Test clinici",
        "test_deep_breath": "Respiro Profondo",
        "test_valsalva": "Valsalva",
        "test_tilt": "Tilt Test",
        "window_slider": "Finestra temporale (sec)",
        "btn_csv": "📥 CSV",
        "btn_reset": "🗑 Reset Dati",
        "hr_live": "FC (live)",
        "avg_bpm": "Media FC",
        "fc_max_global": "FC max",
        "fc_min_global": "FC min",
        "session_done": "✅ Sessione conclusa.",
        "paused_msg": "In pausa - Inizia una registrazione",
        "error_signal": "⚠️ Segnale assente o Token non valido.",
        "chart_x": "Tempo (secondi)",
        "chart_y": "Battiti per minuto",
        "test_running": "⏱️ TEST IN CORSO",
        "test_completed": "✅ Test completato",
        "fc_max": "FC Max",
        "fc_min": "FC Min",
        "fc_diff": "FCmax - FCmin",
        "fc_ratio": "FCmax / FCmin",
        "tilt_ratio": "Rapporto 30:15",
        "tilt_15": "FC a 15s",
        "tilt_30": "FC a 30s",
        "test_wait_30": "⏳ Attendi almeno 30 secondi per un risultato valido",
        "start_recording": "⚠️ Avvia START REC prima di iniziare un test"
    },
    "🇬🇧 ENG": {
        "main_title": "📊❤️ Live heart rate monitoring",
        "token_label": "🔑 Pulsoid Token",
        "token_help": "Enter your Pulsoid generated Token here.",
        "btn_start": "▶️ START REC",
        "btn_stop": "⏹️ STOP REC",
        "btn_test_start": "🟢 START TEST",
        "btn_test_end": "🔴 END TEST",
        "test_clinical_title": "🩺 Clinical Tests",
        "test_deep_breath": "Deep Breathing",
        "test_valsalva": "Valsalva",
        "test_tilt": "Tilt Test",
        "window_slider": "Time window (sec)",
        "btn_csv": "📥 CSV",
        "btn_reset": "🗑 Reset Data",
        "hr_live": "HR (Live)",
        "avg_bpm": "Avg HR",
        "fc_max_global": "Max HR",
        "fc_min_global": "Min HR",
        "session_done": "✅ Session ended.",
        "paused_msg": "Paused - Start a recording",
        "error_signal": "⚠️ No signal or invalid Token.",
        "chart_x": "Time (seconds)",
        "chart_y": "Beats per minute",
        "test_running": "⏱️ TEST RUNNING",
        "test_completed": "✅ Test completed",
        "fc_max": "HR Max",
        "fc_min": "HR Min",
        "fc_diff": "HRmax - HRmin",
        "fc_ratio": "HRmax / HRmin",
        "tilt_ratio": "30:15 Ratio",
        "tilt_15": "HR at 15s",
        "tilt_30": "HR at 30s",
        "test_wait_30": "⏳ Wait at least 30 seconds for a valid result",
        "start_recording": "⚠️ Start START REC first"
    }
}

st_autorefresh(interval=500, key="hr_update")

# --- INITIALIZE SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM'])
if 'running' not in st.session_state:
    st.session_state.running = False
if 'active_test' not in st.session_state:
    st.session_state.active_test = None
if 'freeze_view' not in st.session_state:
    st.session_state.freeze_view = False
if 'test_data' not in st.session_state:
    st.session_state.test_data = pd.DataFrame(columns=['Test_Sec', 'BPM', 'Global_Sec'])
if 'test_markers' not in st.session_state:
    st.session_state.test_markers = []
if 'test_results' not in st.session_state:
    st.session_state.test_results = {}
if 'last_timestamp' not in st.session_state:
    st.session_state.last_timestamp = ""

def get_bpm(token):
    if not token: return None
    url = "https://dev.pulsoid.net/api/v1/data/heart_rate/latest"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=1)
        if r.status_code == 200: return r.json().get('data', {}).get('heart_rate')
    except: return None
    return None

# --- SIDEBAR ---
with st.sidebar:
    lang_choice = st.radio("Lang", ["🇮🇹 ITA", "🇬🇧 ENG"], horizontal=True, label_visibility="collapsed")
    texts = LANGUAGES[lang_choice]
    st.markdown("---")
    italy_tz = pytz.timezone('Europe/Rome')
    st.markdown(f"### 🕐 {datetime.now(italy_tz).strftime('%H:%M:%S')}")

    user_token = st.text_input(texts["token_label"], type="password")
    
    c1, c2 = st.columns(2)
    if c1.button(texts["btn_start"], use_container_width=True, type="primary", disabled=not user_token):
        st.session_state.running = True
        st.session_state.freeze_view = False
    if c2.button(texts["btn_stop"], use_container_width=True):
        st.session_state.running = False
        st.session_state.active_test = None

    window_size = st.slider(texts["window_slider"], 10, 300, 60)
    
    if not st.session_state.history.empty:
        csv = st.session_state.history.to_csv(index=False).encode('utf-8')
        st.download_button(texts["btn_csv"], data=csv, file_name="hr_data.csv", use_container_width=True)
        if st.button(texts["btn_reset"], use_container_width=True):
            for key in ['history', 'test_markers', 'test_data', 'test_results']: st.session_state[key] = pd.DataFrame() if 'data' in key or 'history' in key else []
            st.session_state.active_test = None
            st.session_state.freeze_view = False
            st.session_state.running = False
            st.rerun()

# --- MAIN DASHBOARD ---
st.title(texts["main_title"])

if not user_token:
    st.info(texts["info_token"])
    bpm = None
else:
    bpm = get_bpm(user_token)

current_ts = datetime.now().strftime("%H:%M:%S")

# Metriche 4 Colonne
col_live, col_avg, col_max, col_min = st.columns(4)

if bpm:
    if st.session_state.running:
        col_live.metric(texts["hr_live"], f"{bpm} BPM")
        if st.session_state.last_timestamp != current_ts:
            sec_total = len(st.session_state.history)
            st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([{'Secondi': sec_total, 'BPM': bpm}])], ignore_index=True)
            st.session_state.last_timestamp = current_ts
            if st.session_state.active_test:
                sec_test = len(st.session_state.test_data)
                st.session_state.test_data = pd.concat([st.session_state.test_data, pd.DataFrame([{'Test_Sec': sec_test, 'BPM': bpm, 'Global_Sec': sec_total}])], ignore_index=True)

    if not st.session_state.history.empty:
        h = st.session_state.history
        col_avg.metric(texts["avg_bpm"], f"{h['BPM'].mean():.1f}")
        col_max.metric(texts["fc_max_global"], f"{h['BPM'].max():.0f}")
        col_min.metric(texts["fc_min_global"], f"{h['BPM'].min():.0f}")

# --- CRONOMETRO E GRAFICO ---
if st.session_state.active_test:
    elapsed = len(st.session_state.test_data)
    st.markdown(f"<div class='timer-box'>{texts['test_running']}: {elapsed}s</div>", unsafe_allow_html=True)

if not st.session_state.history.empty:
    # Se un test è appena finito, "congela" il grafico sui dati di quel test
    if st.session_state.freeze_view and not st.session_state.test_data.empty:
        plot_data = st.session_state.history[
            (st.session_state.history['Secondi'] >= st.session_state.test_data['Global_Sec'].min() - 5) & 
            (st.session_state.history['Secondi'] <= st.session_state.test_data['Global_Sec'].max() + 5)
        ]
    else:
        plot_data = st.session_state.history.tail(window_size)
    
    y_min, y_max = plot_data['BPM'].min() - 10, plot_data['BPM'].max() + 10
    
    line = alt.Chart(plot_data).mark_line(color='#ff4b4b', interpolate='monotone').encode(
        x=alt.X('Secondi:Q', axis=alt.Axis(grid=True), title=texts["chart_x"]),
        y=alt.Y('BPM:Q', scale=alt.Scale(domain=[max(20, y_min), y_max]), title=texts["chart_y"])
    )
    
    layers = [line]
    if st.session_state.test_markers:
        m_df = pd.DataFrame({'Secondi': st.session_state.test_markers})
        layers.append(alt.Chart(m_df).mark_rule(color='#00e5ff', strokeDash=[4,4]).encode(x='Secondi:Q'))
    
    st.altair_chart(alt.layer(*layers).interactive(), use_container_width=True)

# --- TEST CLINICI ---
st.markdown("---")
st.subheader(texts["test_clinical_title"])

tab_db, tab_val, tab_tilt = st.tabs([f"🌬️ {texts['test_deep_breath']}", f"😤 {texts['test_valsalva']}", f"🧍 {texts['test_tilt']}"])

def run_test_logic(test_id):
    c1, c2 = st.columns(2)
    if c1.button(texts["btn_test_start"], key=f"s_{test_id}", use_container_width=True, disabled=not st.session_state.running):
        st.session_state.active_test = test_id
        st.session_state.freeze_view = False
        st.session_state.test_data = pd.DataFrame(columns=['Test_Sec', 'BPM', 'Global_Sec'])
        st.session_state.test_markers.append(len(st.session_state.history))
        st.rerun()

    if c2.button(texts["btn_test_end"], key=f"e_{test_id}", use_container_width=True, disabled=st.session_state.active_test != test_id):
        if len(st.session_state.test_data) < 30:
            st.session_state.test_results[test_id] = {"error": texts["test_wait_30"]}
        else:
            df = st.session_state.test_data
            st.session_state.freeze_view = True # CONGELA IL GRAFICO
            if test_id == "deep_breath":
                st.session_state.test_results[test_id] = {'fc_max': df['BPM'].max(), 'fc_min': df['BPM'].min(), 'fc_diff': df['BPM'].max()-df['BPM'].min(), 'fc_ratio': df['BPM'].max()/df['BPM'].min()}
            elif test_id == "valsalva":
                st.session_state.test_results[test_id] = {'fc_max': df['BPM'].max(), 'fc_min': df['BPM'].min(), 'fc_ratio': df['BPM'].max()/df['BPM'].min()}
            elif test_id == "tilt":
                v15 = df.iloc[15]['BPM'] if len(df)>15 else df['BPM'].iloc[-1]
                v30 = df.iloc[30]['BPM'] if len(df)>30 else df['BPM'].iloc[-1]
                st.session_state.test_results[test_id] = {'tilt_15': v15, 'tilt_30': v30, 'tilt_ratio': v30/v15}
        st.session_state.active_test = None
        st.rerun()

    if st.session_state.test_results.get(test_id):
        res = st.session_state.test_results[test_id]
        if "error" in res: st.warning(res["error"])
        else:
            st.success(texts["test_completed"])
            return res
    return None

with tab_db:
    res = run_test_logic("deep_breath")
    if res:
        r1, r2, r3, r4 = st.columns(4)
        r1.metric(texts["fc_max"], f"{res['fc_max']:.0f}")
        r2.metric(texts["fc_min"], f"{res['fc_min']:.0f}")
        r3.metric(texts["fc_diff"], f"{res['fc_diff']:.0f}")
        r4.metric(texts["fc_ratio"], f"{res['fc_ratio']:.2f}")

with tab_val:
    res = run_test_logic("valsalva")
    if res:
        r1, r2, r3 = st.columns(3)
        r1.metric(texts["fc_max"], f"{res['fc_max']:.0f}")
        r2.metric(texts["fc_min"], f"{res['fc_min']:.0f}")
        r3.metric(texts["fc_ratio"], f"{res['fc_ratio']:.2f}")

with tab_tilt:
    res = run_test_logic("tilt")
    if res:
        r1, r2, r3 = st.columns(3)
        r1.metric(texts["tilt_15"], f"{res['tilt_15']:.0f}")
        r2.metric(texts["tilt_30"], f"{res['tilt_30']:.0f}")
        r3.metric(texts["tilt_ratio"], f"{res['tilt_ratio']:.2f}")
