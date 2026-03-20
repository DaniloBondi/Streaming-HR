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

LANGUAGES = {
    "🇮🇹 ITA": {
        "main_title": "📊❤️ Monitoraggio live frequenza cardiaca",
        "token_label": "🔑 Token Pulsoid",
        "token_help": "Inserisci qui il tuo Token generato da Pulsoid.",
        "btn_start": "▶️ START",
        "btn_stop": "⏹️ STOP",
        "btn_test_start": "🫁 INIZIO TEST",
        "btn_test_end": "🫁 FINE TEST",
        "test_title": "Test Respiro Profondo",
        "window_slider": "Finestra temporale (sec)",
        "btn_csv": "📥 CSV",
        "btn_reset": "🗑 Reset",
        "privacy_title": "🛡️ Informativa Privacy e Dati",
        "privacy_text": "Nessun salvataggio: i dati restano solo nella RAM temporanea della sessione.<br>Cancellazione: alla chiusura del browser, i dati vengono eliminati.<br>Sicurezza: il token Pulsoid inserito non viene mai archiviato.",
        "info_token": "👈 Inserisci il tuo Token Pulsoid nella barra laterale per avviare il monitoraggio.",
        "hr_live": "Heart Rate (Live)",
        "avg_bpm": "Media BPM Sessione",
        "session_done": "✅ Sessione conclusa. Dati totali:",
        "session_short": "Sessione troppo breve per il calcolo.",
        "hr_paused": "Heart Rate",
        "paused_msg": "In pausa - Inizia una registrazione",
        "error_signal": "⚠️ Segnale assente o Token non valido. Controlla il collegamento con l'app Pulsoid.",
        "chart_x": "Tempo (secondi)",
        "chart_y": "Battiti per minuto",
        "creator": "**Creator:** Danilo Bondi",
        "sec": "secondi",
        "test_running": "⏱️ Test in corso...",
        "test_completed": "✅ Test completato",
        "fc_max": "FC Max",
        "fc_min": "FC Min",
        "fc_diff": "FCmax - FCmin",
        "fc_ratio": "FCmax / FCmin",
        "start_recording": "⚠️ Avvia prima la registrazione con START",
        "test_no_data": "Nessun dato del test disponibile"
    },
    "🇬🇧 ENG": {
        "main_title": "📊❤️ Live heart rate monitoring",
        "token_label": "🔑 Pulsoid Token",
        "token_help": "Enter your Pulsoid generated Token here.",
        "btn_start": "▶️ START",
        "btn_stop": "⏹️ STOP",
        "btn_test_start": "🫁 START TEST",
        "btn_test_end": "🫁 END TEST",
        "test_title": "Deep Breathing Test",
        "window_slider": "Time window (sec)",
        "btn_csv": "📥 CSV",
        "btn_reset": "🗑 Reset",
        "privacy_title": "🛡️ Privacy and Data Policy",
        "privacy_text": "No storage: data remains only in temporary RAM during the session.<br>Deletion: closing the browser deletes the data.<br>Security: the entered Pulsoid token is never stored.",
        "info_token": "👈 Insert your Pulsoid Token in the sidebar to start monitoring.",
        "hr_live": "Heart Rate (Live)",
        "avg_bpm": "Session Avg BPM",
        "session_done": "✅ Session ended. Total data:",
        "session_short": "Session too short for calculation.",
        "hr_paused": "Heart Rate",
        "paused_msg": "Paused - Start a recording",
        "error_signal": "⚠️ No signal or invalid Token. Check your Pulsoid app connection.",
        "chart_x": "Time (seconds)",
        "chart_y": "Beats per minute",
        "creator": "**Creator:** Danilo Bondi",
        "sec": "seconds",
        "test_running": "⏱️ Test running...",
        "test_completed": "✅ Test completed",
        "fc_max": "HR Max",
        "fc_min": "HR Min",
        "fc_diff": "HRmax - HRmin",
        "fc_ratio": "HRmax / HRmin",
        "start_recording": "⚠️ Start recording with START first",
        "test_no_data": "No test data available"
    }
}

st_autorefresh(interval=500, key="hr_update")

if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM'])
if 'running' not in st.session_state:
    st.session_state.running = False
if 'last_timestamp' not in st.session_state:
    st.session_state.last_timestamp = ""
if 'test_running' not in st.session_state:
    st.session_state.test_running = False
if 'test_data' not in st.session_state:
    st.session_state.test_data = pd.DataFrame(columns=['Secondi', 'BPM'])
if 'test_results' not in st.session_state:
    st.session_state.test_results = None

def get_bpm(token):
    if not token:
        return None
    url = "https://dev.pulsoid.net/api/v1/data/heart_rate/latest"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=1)
        if r.status_code == 200:
            return r.json().get('data', {}).get('heart_rate')
    except:
        return None
    return None

with st.sidebar:
    lang_choice = st.radio("Lingua", ["🇮🇹 ITA", "🇬🇧 ENG"], horizontal=True, label_visibility="collapsed")
    texts = LANGUAGES[lang_choice] 

    st.markdown("---")

    italy_tz = pytz.timezone('Europe/Rome')
    now_italy = datetime.now(italy_tz)
    st.markdown(f"### 🕐 {now_italy.strftime('%H:%M:%S')} | {now_italy.strftime('%d/%m/%Y')}")

    user_token = st.text_input(texts["token_label"], type="password", help=texts["token_help"])

    c1, c2 = st.columns(2)
    
    if c1.button(texts["btn_start"], use_container_width=True, type="primary", disabled=not user_token):
        st.session_state.running = True
    if c2.button(texts["btn_stop"], use_container_width=True):
        st.session_state.running = False
        if st.session_state.test_running:
            st.session_state.test_running = False

    window_size = st.slider(texts["window_slider"], 10, 300, 60)

    if not st.session_state.history.empty:
        csv = st.session_state.history.to_csv(index=False).encode('utf-8')
        st.download_button(texts["btn_csv"], data=csv, file_name="hr_data.csv", use_container_width=True)
        if st.button(texts["btn_reset"], use_container_width=True):
            st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM'])
            st.session_state.last_timestamp = ""
            st.session_state.running = False
            st.session_state.test_running = False
            st.session_state.test_data = pd.DataFrame(columns=['Secondi', 'BPM'])
            st.session_state.test_results = None
            st.rerun()

    st.markdown("---")
    st.caption("**Smartphone app:** Pulsoid | **Repository:** GitHub | **Web app:** Streamlit | **AI:** Gemini")
    
    st.write("")
    logoc1, logoc2 = st.columns(2)
    
    try:
        with logoc1:
            if os.path.exists("logo UDA.png"):
                st.image("logo UDA.png", width=100)
        with logoc2:
            if os.path.exists("Logo UnivAq.png"):
                st.image("Logo UnivAq.png", width=100)
    except Exception as e:
        st.sidebar.error(f"Errore caricamento loghi: {e}")
    
    st.caption(texts["creator"])

    st.write("") 
    with st.expander(texts["privacy_title"]):
        st.markdown(f"""
        <small>
        {texts["privacy_text"]}
        </small>
        """, unsafe_allow_html=True)

# DASHBOARD
st.title(texts["main_title"])

# Controllo iniziale: chiedo all'utente di inserire il token
if not user_token:
    st.info(texts["info_token"])
    bpm = None
else:
    bpm = get_bpm(user_token)

current_ts = datetime.now().strftime("%H:%M:%S")

col_val, col_avg = st.columns(2)

if bpm:
    if st.session_state.running:
        # LIVE SESSION
        col_val.metric(texts["hr_live"], f"{bpm} BPM")
        
        if st.session_state.last_timestamp != current_ts:
            sec_elapsed = len(st.session_state.history)
            new_row = pd.DataFrame([{'Secondi': sec_elapsed, 'BPM': bpm}])
            st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
            st.session_state.last_timestamp = current_ts
            
            # Se il test è in corso, aggiungi anche ai dati del test
            if st.session_state.test_running:
                test_sec = len(st.session_state.test_data)
                test_row = pd.DataFrame([{'Secondi': test_sec, 'BPM': bpm}])
                st.session_state.test_data = pd.concat([st.session_state.test_data, test_row], ignore_index=True)

        # Mostra media della sessione
        if not st.session_state.history.empty:
            avg_bpm_session = st.session_state.history['BPM'].mean()
            col_avg.metric(texts["avg_bpm"], f"{avg_bpm_session:.1f} BPM")
            
    else:
        # STOP & REPORT
        if not st.session_state.history.empty:
            avg_bpm_total = st.session_state.history['BPM'].mean()
            col_val.metric(texts["avg_bpm"], f"{avg_bpm_total:.1f} BPM")
            col_avg.success(f"{texts['session_done']} {len(st.session_state.history)} {texts['sec']}.")
        else:
            col_val.metric(texts["hr_paused"], f"{bpm} BPM")
            col_avg.warning(texts["paused_msg"])
elif user_token:
    # Se c'è il token ma non arrivano i BPM
    st.error(texts["error_signal"])

# SEZIONE TEST RESPIRO PROFONDO
st.markdown("---")
st.subheader(f"🫁 {texts['test_title']}")

test_col1, test_col2 = st.columns(2)

# Bottone INIZIO TEST
if test_col1.button(
    texts["btn_test_start"], 
    key="start_test_button",
    use_container_width=True, 
    type="primary", 
    disabled=not st.session_state.running
):
    if st.session_state.running:
        st.session_state.test_running = True
        st.session_state.test_data = pd.DataFrame(columns=['Secondi', 'BPM'])
        st.session_state.test_results = None
        st.rerun()

# Bottone FINE TEST  
if test_col2.button(
    texts["btn_test_end"],
    key="end_test_button", 
    use_container_width=True,
    disabled=not st.session_state.test_running
):
    if st.session_state.test_running:
        st.session_state.test_running = False
        
        # Calcola i risultati del test
        if not st.session_state.test_data.empty and len(st.session_state.test_data) > 0:
            fc_max = st.session_state.test_data['BPM'].max()
            fc_min = st.session_state.test_data['BPM'].min()
            fc_diff = fc_max - fc_min
            fc_ratio = fc_max / fc_min if fc_min > 0 else 0
            
            st.session_state.test_results = {
                'fc_max': fc_max,
                'fc_min': fc_min,
                'fc_diff': fc_diff,
                'fc_ratio': fc_ratio
            }
        st.rerun()
        
# Mostra stato del test
if st.session_state.test_running:
    st.info(f"{texts['test_running']} {len(st.session_state.test_data)} {texts['sec']}")
elif st.session_state.test_results:
    st.success(texts['test_completed'])
    
    # Mostra i risultati in 4 colonne
    res_col1, res_col2, res_col3, res_col4 = st.columns(4)
    
    res_col1.metric(texts["fc_max"], f"{st.session_state.test_results['fc_max']:.0f} BPM")
    res_col2.metric(texts["fc_min"], f"{st.session_state.test_results['fc_min']:.0f} BPM")
    res_col3.metric(texts["fc_diff"], f"{st.session_state.test_results['fc_diff']:.0f} BPM")
    res_col4.metric(texts["fc_ratio"], f"{st.session_state.test_results['fc_ratio']:.2f}")

# GRAFICO INTERATTIVO
st.markdown("---")
if not st.session_state.history.empty:
    data_subset = st.session_state.history.tail(window_size)
    
    avg_bpm = data_subset['BPM'].mean()
    y_min = max(20, avg_bpm - 20)
    y_max = y_min + 50

    line = alt.Chart(data_subset).mark_line(color='#ff4b4b', interpolate='monotone').encode(
        x=alt.X('Secondi:Q',
                axis=alt.Axis(grid=True, tickCount=window_size//5, gridDash=[4,4]),
                title=texts["chart_x"]),
        y=alt.Y('BPM:Q', scale=alt.Scale(domain=[y_min, y_max]), title=texts["chart_y"])
    ).interactive()

    trend = line.transform_regression('Secondi', 'BPM').mark_line(
        color='white', 
        size=2, 
        opacity=0.8
    )

    st.altair_chart(line + trend, use_container_width=True)
