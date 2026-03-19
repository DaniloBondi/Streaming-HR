import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz
import altair as alt
import os

# --- CONFIGURAZIONE ---
PULSOID_TOKEN = "6f519fde-0ec2-4bc1-a108-8812f6f0c102"

st.set_page_config(page_title="Monitoraggio live FC", layout="wide")

# Refresh automatico ogni 500ms
st_autorefresh(interval=500, key="hr_update")

# --- INIZIALIZZAZIONE MEMORIA ---
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM', 'RR_ms'])
if 'running' not in st.session_state:
    st.session_state.running = False
if 'last_timestamp' not in st.session_state:
    st.session_state.last_timestamp = ""

def get_bpm():
    url = "https://dev.pulsoid.net/api/v1/data/heart_rate/latest"
    headers = {"Authorization": f"Bearer {PULSOID_TOKEN}"}
    try:
        r = requests.get(url, headers=headers, timeout=1)
        if r.status_code == 200:
            return r.json().get('data', {}).get('heart_rate')
    except:
        return None
    return None

# --- SIDEBAR COMPATTA ---
with st.sidebar:
    italy_tz = pytz.timezone('Europe/Rome')
    now_italy = datetime.now(italy_tz)
    st.markdown(f"### 🕐 {now_italy.strftime('%H:%M:%S')} | {now_italy.strftime('%d/%m/%Y')}")

    c1, c2 = st.columns(2)
    if c1.button("▶️ START", use_container_width=True, type="primary"):
        st.session_state.running = True
    if c2.button("⏹️ STOP", use_container_width=True):
        st.session_state.running = False

    window_size = st.slider("Finestra temporale (sec)", 10, 300, 60)

    if not st.session_state.history.empty:
        csv = st.session_state.history.to_csv(index=False).encode('utf-8')
        st.download_button("📥 CSV", data=csv, file_name="hrv_data.csv", use_container_width=True)
        if st.button("🗑 Reset", use_container_width=True):
            st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM', 'RR_ms'])
            st.session_state.last_timestamp = ""
            st.session_state.running = False
            st.rerun()

    st.markdown("---")
    st.caption("**Sensor:** Moofit armband | **Smartphone app:** Pulsoid | **Repository:** GitHub | **Web app:** Streamlit | **AI:** Gemini")
    
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
    
    st.caption("**Creator:** Danilo Bondi")

# DASHBOARD
st.title("📊❤️ Monitoraggio live frequenza cardiaca e calcolo HRV")

bpm = get_bpm()
current_ts = datetime.now().strftime("%H:%M:%S")

col_val, col_hrv = st.columns(2)

if bpm:
    rr_ms = 60000 / bpm
    
    if st.session_state.running:
        # LIVE SESSION
        col_val.metric("Heart Rate (Live)", f"{bpm} BPM")
        
        if st.session_state.last_timestamp != current_ts:
            sec_elapsed = len(st.session_state.history)
            new_row = pd.DataFrame([{'Secondi': sec_elapsed, 'BPM': bpm, 'RR_ms': rr_ms}])
            st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
            st.session_state.last_timestamp = current_ts

        n_punti = len(st.session_state.history)
        if n_punti >= 30:
            recent_rr = st.session_state.history['RR_ms'].tail(30).values
            rmssd_live = np.sqrt(np.mean(np.square(np.diff(recent_rr))))
            col_hrv.metric("HRV (RMSSD 30s live)", f"{rmssd_live:.2f} ms")
        else:
            col_hrv.info(f"⏳ Calibrazione HRV: {30 - n_punti}s...")
            
    else:
        # STOP & REPORT
        if not st.session_state.history.empty:
            # Calcolo medie globali
            avg_bpm_total = st.session_state.history['BPM'].mean()
            
            # Calcolo RMSSD globale su tutta la registrazione
            all_rr = st.session_state.history['RR_ms'].values
            if len(all_rr) >= 2:
                rmssd_total = np.sqrt(np.mean(np.square(np.diff(all_rr))))
                
                col_val.metric("Media BPM Sessione", f"{avg_bpm_total:.1f}")
                col_hrv.metric("RMSSD Totale Sessione", f"{rmssd_total:.2f} ms")
                st.success(f"✅ Sessione conclusa. Dati totali: {len(st.session_state.history)} secondi.")
            else:
                col_val.warning("Sessione troppo breve per il calcolo.")
        else:
            col_val.metric("Heart Rate", f"{bpm} BPM")
            col_hrv.warning("In pausa - Inizia una registrazione")
else:
    st.error("⚠️ Segnale assente")

# GRAFICO INTERATTIVO
if not st.session_state.history.empty:
    data_subset = st.session_state.history.tail(window_size)
    
    avg_bpm = data_subset['BPM'].mean()
    y_min = max(20, avg_bpm - 20)
    y_max = y_min + 50

    line = alt.Chart(data_subset).mark_line(color='#ff4b4b', interpolate='monotone').encode(
        x=alt.X('Secondi:Q',
                axis=alt.Axis(grid=True, tickCount=window_size//5, gridDash=[4,4]),
                title="Tempo (secondi)"),
        y=alt.Y('BPM:Q', scale=alt.Scale(domain=[y_min, y_max]), title="Battiti per minuto")
    ).interactive()

    trend = line.transform_regression('Secondi', 'BPM').mark_line(
        color='white', 
        size=2, 
        opacity=0.8
    )

    st.altair_chart(line + trend, use_container_width=True)
