import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz
import altair as alt
import os

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
    italy_tz = pytz.timezone('Europe/Rome')
    now_italy = datetime.now(italy_tz)
    st.markdown(f"### 🕐 {now_italy.strftime('%H:%M:%S')} | {now_italy.strftime('%d/%m/%Y')}")

    # NUOVO: Campo di testo per il Token dell'utente
    user_token = st.text_input("🔑 Token Pulsoid", type="password", help="Inserisci qui il tuo Token generato da Pulsoid.")

    c1, c2 = st.columns(2)
    
    if c1.button("▶️ START", use_container_width=True, type="primary", disabled=not user_token):
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
    
    st.caption("**Creator:** Danilo Bondi")

    st.write("") 
    with st.expander("🛡️ Informativa Privacy e Dati"):
        st.markdown("""
        <small>
        Nessun salvataggio: i dati restano solo nella RAM temporanea della sessione.
        Cancellazione: alla chiusura del browser, i dati vengono eliminati.
        Sicurezza: il token Pulsoid inserito non viene mai archiviato.
        </small>
        """, unsafe_allow_html=True)

# DASHBOARD
st.title("📊❤️ Monitoraggio live frequenza cardiaca e calcolo HRV")

# Controllo iniziale: chiedo all'utente di inserire il token
if not user_token:
    st.info("👈 Inserisci il tuo Token Pulsoid nella barra laterale per avviare il monitoraggio.")
    bpm = None
else:
    bpm = get_bpm(user_token)

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
            avg_bpm_total = st.session_state.history['BPM'].mean()
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
elif user_token:
    # Se c'è il token ma non arrivano i BPM, significa che il segnale è assente o il token è errato
    st.error("⚠️ Segnale assente o Token non valido. Controlla il collegamento con l'app Pulsoid.")

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
