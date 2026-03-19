import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz
import altair as alt
import os

# set_page_config deve essere il primo comando Streamlit
st.set_page_config(page_title="Monitoraggio FC / HR Monitor", layout="wide")

# --- DIZIONARIO TRADUZIONI ---
LANGUAGES = {
    "Italiano": {
        "main_title": "📊❤️ Monitoraggio live frequenza cardiaca e calcolo HRV",
        "token_label": "🔑 Token Pulsoid",
        "token_help": "Inserisci qui il tuo Token generato da Pulsoid.",
        "btn_start": "▶️ START",
        "btn_stop": "⏹️ STOP",
        "window_slider": "Finestra temporale (sec)",
        "btn_csv": "📥 CSV",
        "btn_reset": "🗑 Reset",
        "privacy_title": "🛡️ Informativa Privacy e Dati",
        "privacy_text": "Nessun salvataggio: i dati restano solo nella RAM temporanea della sessione.<br>Cancellazione: alla chiusura del browser, i dati vengono eliminati.<br>Sicurezza: il token Pulsoid inserito non viene mai archiviato.",
        "info_token": "👈 Inserisci il tuo Token Pulsoid nella barra laterale per avviare il monitoraggio.",
        "hr_live": "Heart Rate (Live)",
        "hrv_live": "HRV (RMSSD 30s live)",
        "calibrating": "⏳ Calibrazione HRV:",
        "avg_bpm": "Media BPM Sessione",
        "rmssd_tot": "RMSSD Totale Sessione",
        "session_done": "✅ Sessione conclusa. Dati totali:",
        "session_short": "Sessione troppo breve per il calcolo.",
        "hr_paused": "Heart Rate",
        "paused_msg": "In pausa - Inizia una registrazione",
        "error_signal": "⚠️ Segnale assente o Token non valido. Controlla il collegamento con l'app Pulsoid.",
        "chart_x": "Tempo (secondi)",
        "chart_y": "Battiti per minuto",
        "creator": "**Creator:** Danilo Bondi",
        "sec": "secondi"
    },
    "English": {
        "main_title": "📊❤️ Live Heart Rate Monitoring and HRV Calculation",
        "token_label": "🔑 Pulsoid Token",
        "token_help": "Enter your Pulsoid generated Token here.",
        "btn_start": "▶️ START",
        "btn_stop": "⏹️ STOP",
        "window_slider": "Time window (sec)",
        "btn_csv": "📥 CSV",
        "btn_reset": "🗑 Reset",
        "privacy_title": "🛡️ Privacy and Data Policy",
        "privacy_text": "No storage: data remains only in temporary RAM during the session.<br>Deletion: closing the browser deletes the data.<br>Security: the entered Pulsoid token is never stored.",
        "info_token": "👈 Insert your Pulsoid Token in the sidebar to start monitoring.",
        "hr_live": "Heart Rate (Live)",
        "hrv_live": "HRV (RMSSD 30s live)",
        "calibrating": "⏳ HRV Calibration:",
        "avg_bpm": "Session Avg BPM",
        "rmssd_tot": "Session Total RMSSD",
        "session_done": "✅ Session ended. Total data:",
        "session_short": "Session too short for calculation.",
        "hr_paused": "Heart Rate",
        "paused_msg": "Paused - Start a recording",
        "error_signal": "⚠️ No signal or invalid Token. Check your Pulsoid app connection.",
        "chart_x": "Time (seconds)",
        "chart_y": "Beats per minute",
        "creator": "**Creator:** Danilo Bondi",
        "sec": "seconds"
    }
}

# Refresh automatico ogni 500ms
st_autorefresh(interval=500, key="hr_update")

# --- INIZIALIZZAZIONE MEMORIA ---
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM', 'RR_ms'])
if 'running' not in st.session_state:
    st.session_state.running = False
if 'last_timestamp' not in st.session_state:
    st.session_state.last_timestamp = ""

# --- FUNZIONE API ---
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

# --- SIDEBAR COMPATTA ---
with st.sidebar:
    # 1. Scelta della lingua
    lang_choice = st.selectbox("🌐 Lingua / Language", ["Italiano", "English"])
    texts = LANGUAGES[lang_choice] # Assegna il dizionario corretto in base alla scelta

    st.markdown("---")

    italy_tz = pytz.timezone('Europe/Rome')
    now_italy = datetime.now(italy_tz)
    st.markdown(f"### 🕐 {now_italy.strftime('%H:%M:%S')} | {now_italy.strftime('%d/%m/%Y')}")

    # Campo di testo per il Token dell'utente
    user_token = st.text_input(texts["token_label"], type="password", help=texts["token_help"])

    c1, c2 = st.columns(2)
    
    if c1.button(texts["btn_start"], use_container_width=True, type="primary", disabled=not user_token):
        st.session_state.running = True
    if c2.button(texts["btn_stop"], use_container_width=True):
        st.session_state.running = False

    window_size = st.slider(texts["window_slider"], 10, 300, 60)

    if not st.session_state.history.empty:
        csv = st.session_state.history.to_csv(index=False).encode('utf-8')
        st.download_button(texts["btn_csv"], data=csv, file_name="hrv_data.csv", use_container_width=True)
        if st.button(texts["btn_reset"], use_container_width=True):
            st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM', 'RR_ms'])
            st.session_state.last_timestamp = ""
            st.session_state.running = False
            st.rerun()

    st.markdown("---")
    st.caption("**Smartphone app:** Pulsoid | **Repository:** GitHub | **Web app:** Streamlit | **AI:** Gemini")
    
    st.write("")
    logoc1, logoc2 = st.columns(2)
    
    try:
        with logoc1:
            if os.path.exists("logo UDA.png"):
                st.image("logo UDA.png", width=100)
            else:
                st.error("UDA non trovato")
        with logoc2:
            if os.path.exists("Logo UnivAq.png"):
                st.image("Logo UnivAq.png", width=100)
            else:
                st.error("UnivAq non trovato")
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

col_val, col_hrv = st.columns(2)

if bpm:
    rr_ms = 60000 / bpm
    
    if st.session_state.running:
        # LIVE SESSION
        col_val.metric(texts["hr_live"], f"{bpm} BPM")
        
        if st.session_state.last_timestamp != current_ts:
            sec_elapsed = len(st.session_state.history)
            new_row = pd.DataFrame([{'Secondi': sec_elapsed, 'BPM': bpm, 'RR_ms': rr_ms}])
            st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
            st.session_state.last_timestamp = current_ts

        n_punti = len(st.session_state.history)
        if n_punti >= 30:
            recent_rr = st.session_state.history['RR_ms'].tail(30).values
            rmssd_live = np.sqrt(np.mean(np.square(np.diff(recent_rr))))
            col_hrv.metric(texts["hrv_live"], f"{rmssd_live:.2f} ms")
        else:
            col_hrv.info(f"{texts['calibrating']} {30 - n_punti}s...")
            
    else:
        # STOP & REPORT
        if not st.session_state.history.empty:
            avg_bpm_total = st.session_state.history['BPM'].mean()
            all_rr = st.session_state.history['RR_ms'].values
            if len(all_rr) >= 2:
                rmssd_total = np.sqrt(np.mean(np.square(np.diff(all_rr))))
                
                col_val.metric(texts["avg_bpm"], f"{avg_bpm_total:.1f}")
                col_hrv.metric(texts["rmssd_tot"], f"{rmssd_total:.2f} ms")
                st.success(f"{texts['session_done']} {len(st.session_state.history)} {texts['sec']}.")
            else:
                col_val.warning(texts["session_short"])
        else:
            col_val.metric(texts["hr_paused"], f"{bpm} BPM")
            col_hrv.warning(texts["paused_msg"])
elif user_token:
    # Se c'è il token ma non arrivano i BPM
    st.error(texts["error_signal"])

# GRAFICO INTERATTIVO
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
    
