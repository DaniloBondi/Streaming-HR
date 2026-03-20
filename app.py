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

# --- CSS PERSONALIZZATO (Per font, margini e cronometro) ---
st.markdown("""
<style>
    /* Sposta il titolo più in alto riducendo il padding superiore */
    .block-container {
        padding-top: 1.5rem !important;
    }
    h1 {
        margin-top: -40px !important;
        padding-bottom: 20px;
    }
    /* Riduci font metriche principali (FC Live, Media, Max, Min) */
    [data-testid="stMetricValue"] {
        font-size: 1.6rem !important;
    }
    /* Riduci font label metriche */
    [data-testid="stMetricLabel"] {
        font-size: 0.85rem !important;
    }
    /* Riduci font pulsanti nella sidebar (START REC / STOP REC) */
    .stButton > button {
        font-size: 0.8rem !important;
        padding: 0.2rem 0.5rem;
    }
    /* Stile personalizzato per il box del cronometro durante i test */
    .timer-box {
        font-family: 'Courier New', Courier, monospace;
        font-size: 2.2rem;
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

# --- DIZIONARI LINGUE (Aggiornati con tutti i testi) ---
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
        "privacy_title": "🛡️ Informativa Privacy e Dati",
        "privacy_text": "Nessun salvataggio: i dati restano solo nella RAM temporanea della sessione.<br>Cancellazione: alla chiusura del browser, i dati vengono eliminati.<br>Sicurezza: il token Pulsoid inserito non viene mai archiviato.",
        "info_token": "👈 Inserisci il tuo Token Pulsoid nella barra laterale per avviare il monitoraggio.",
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
        "start_recording": "⚠️ Avvia START REC prima di iniziare un test",
        "credits": "**Smartphone app:** Pulsoid | **Repository:** GitHub | **Web app:** Streamlit | **AI:** Gemini",
        "creator": "**Creator:** Danilo Bondi"
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
        "privacy_title": "🛡️ Privacy and Data Policy",
        "privacy_text": "No storage: data remains only in temporary RAM during the session.<br>Deletion: closing the browser deletes the data.<br>Security: the entered Pulsoid token is never stored.",
        "info_token": "👈 Insert your Pulsoid Token in the sidebar to start monitoring.",
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
        "start_recording": "⚠️ Start START REC first",
        "credits": "**Smartphone app:** Pulsoid | **Repository:** GitHub | **Web app:** Streamlit | **AI:** Gemini",
        "creator": "**Creator:** Danilo Bondi"
    }
}

# Auto-refresh ogni 500ms
st_autorefresh(interval=500, key="hr_update")

# --- INIZIALIZZAZIONE SESSION STATE ---
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
    st.session_state.test_markers = [] # Memorizza i timestamp globali per le linee verticali
if 'test_results' not in st.session_state:
    st.session_state.test_results = {}
if 'last_timestamp' not in st.session_state:
    st.session_state.last_timestamp = ""

# --- FUNZIONE RECUPERO DATI API ---
def get_bpm(token):
    if not token: return None
    url = "https://dev.pulsoid.net/api/v1/data/heart_rate/latest"
    headers = {"Authorization": f"Bearer {token}"}
    try:
        r = requests.get(url, headers=headers, timeout=1)
        if r.status_code == 200: return r.json().get('data', {}).get('heart_rate')
    except: return None
    return None

# --- SIDEBAR (Completa di tutti gli elementi) ---
with st.sidebar:
    # Selezione Lingua in alto
    lang_choice = st.radio("Lang", ["🇮🇹 ITA", "🇬🇧 ENG"], horizontal=True, label_visibility="collapsed")
    texts = LANGUAGES[lang_choice]
    
    st.markdown("---")
    
    # Orologio live
    italy_tz = pytz.timezone('Europe/Rome')
    st.markdown(f"### 🕐 {datetime.now(italy_tz).strftime('%H:%M:%S')}")

    # Input Token
    user_token = st.text_input(texts["token_label"], type="password", help=texts["token_help"])
    
    # Pulsanti di registrazione principali
    c1, c2 = st.columns(2)
    if c1.button(texts["btn_start"], use_container_width=True, type="primary", disabled=not user_token):
        st.session_state.running = True
        st.session_state.freeze_view = False # Sblocca la vista se era congelata da un test precedente
    if c2.button(texts["btn_stop"], use_container_width=True):
        st.session_state.running = False
        st.session_state.active_test = None # Ferma anche eventuali test attivi

    # Slider finestra temporale grafico
    window_size = st.slider(texts["window_slider"], 10, 300, 60)
    
    # Download e Reset
    if not st.session_state.history.empty:
        csv = st.session_state.history.to_csv(index=False).encode('utf-8')
        st.download_button(texts["btn_csv"], data=csv, file_name="hr_data.csv", use_container_width=True)
        
        if st.button(texts["btn_reset"], use_container_width=True):
            # Reset completo di tutti gli stati
            for key in ['history', 'test_markers', 'test_data', 'test_results']: 
                st.session_state[key] = pd.DataFrame() if 'data' in key or 'history' in key else []
            st.session_state.active_test = None
            st.session_state.freeze_view = False
            st.session_state.running = False
            st.session_state.last_timestamp = ""
            st.rerun()

    st.markdown("---")
    # Credits e Info tecniche
    st.caption(texts["credits"])
    
    st.write("")
    # Loghi Università (try-except per evitare errori se mancano i file)
    logoc1, logoc2 = st.columns(2)
    try:
        with logoc1:
            if os.path.exists("logo UDA.png"): st.image("logo UDA.png", width=100)
        with logoc2:
            if os.path.exists("Logo UnivAq.png"): st.image("Logo UnivAq.png", width=100)
    except: pass # Ignora silenziosamente se i loghi non vengono caricati
    
    st.write("")
    # Creatore
    st.caption(texts["creator"])

    st.write("") 
    # Espansore Informativa Privacy completa
    with st.expander(texts["privacy_title"]):
        st.markdown(f"<small>{texts['privacy_text']}</small>", unsafe_allow_html=True)

# --- DASHBOARD PRINCIPALE ---
st.title(texts["main_title"])

if not user_token:
    st.info(texts["info_token"])
    bpm = None
else:
    bpm = get_bpm(user_token)

current_ts = datetime.now().strftime("%H:%M:%S")

# --- AREA METRICHE SUPERIORI (4 Colonne) ---
col_live, col_avg, col_max, col_min = st.columns(4)

if bpm:
    # Logica di registrazione dati (solo se START REC è attivo)
    if st.session_state.running:
        col_live.metric(texts["hr_live"], f"{bpm} BPM")
        # Registra un dato ogni secondo (se il timestamp cambia)
        if st.session_state.last_timestamp != current_ts:
            sec_total = len(st.session_state.history)
            st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([{'Secondi': sec_total, 'BPM': bpm}])], ignore_index=True)
            st.session_state.last_timestamp = current_ts
            
            # Se un test clinico è attivo, registra dati anche nel DF del test specifico
            if st.session_state.active_test:
                sec_test = len(st.session_state.test_data)
                # Global_Sec serve per congelare il grafico sui dati corretti alla fine
                st.session_state.test_data = pd.concat([st.session_state.test_data, pd.DataFrame([{'Test_Sec': sec_test, 'BPM': bpm, 'Global_Sec': sec_total}])], ignore_index=True)

    # Visualizzazione metriche FC (Live, Media, Max, Min globali della sessione)
    if not st.session_state.history.empty:
        h = st.session_state.history
        col_avg.metric(texts["avg_bpm"], f"{h['BPM'].mean():.1f}")
        col_max.metric(texts["fc_max_global"], f"{h['BPM'].max():.0f}")
        col_min.metric(texts["fc_min_global"], f"{h['BPM'].min():.0f}")
        
        # Se la registrazione è stoppata, mostra riepilogo
        if not st.session_state.running:
            col_live.metric(texts["hr_paused"], f"{bpm} BPM")
            st.success(f"{texts['session_done']} {len(h)} {texts['sec']}.")
    else:
        # Stato iniziale o in pausa senza dati
        if not st.session_state.running:
            col_live.metric(texts["hr_paused"], f"{bpm} BPM")
            col_avg.warning(texts["paused_msg"])
elif user_token:
    # Token inserito ma nessun segnale da Pulsoid
    st.error(texts["error_signal"])

# --- SEZIONE CENTRALE: CRONOMETRO TEST E GRAFICO ---

# 1. Cronometro visibile solo durante l'esecuzione dei test
if st.session_state.active_test:
    elapsed = len(st.session_state.test_data)
    # Box azzurro stilizzato via CSS
    st.markdown(f"<div class='timer-box'>{texts['test_running']}: {elapsed}s</div>", unsafe_allow_html=True)

# 2. Grafico Altair (Sistemato con linea continua, interpolazione e sfumatura)
if not st.session_state.history.empty:
    
    # Logica per determinare quali dati mostrare (Live tail o Freeze del test concluso)
    if st.session_state.freeze_view and not st.session_state.test_data.empty:
        # Mostra i dati del test appena concluso con un margine di 5 secondi prima e dopo
        t_data = st.session_state.test_data
        plot_data = st.session_state.history[
            (st.session_state.history['Secondi'] >= t_data['Global_Sec'].min() - 5) & 
            (st.session_state.history['Secondi'] <= t_data['Global_Sec'].max() + 5)
        ]
    else:
        # Vista Live: mostra gli ultimi secondi definiti dallo slider nella sidebar
        plot_data = st.session_state.history.tail(window_size)
    
    # Calcolo dinamico asse Y basato sui dati visibili
    if not plot_data.empty:
        y_min, y_max = plot_data['BPM'].min() - 10, plot_data['BPM'].max() + 10
    else:
        y_min, y_max = 40, 100 # Default se non ci sono dati visibili

    # Grafico Base Altair
    base = alt.Chart(plot_data).encode(
        x=alt.X('Secondi:Q', axis=alt.Axis(grid=True), title=texts["chart_x"]),
        y=alt.Y('BPM:Q', scale=alt.Scale(domain=[max(20, y_min), y_max]), title=texts["chart_y"])
    )

    # Layer 1: L'area sfumata sottostante (Gradient offset da rosso a trasparente)
    area = base.mark_area(
        interpolate='monotone', # Rende l'area curva e morbida
        color=alt.Gradient(
            gradient='linear',
            stops=[
                alt.GradientStop(color='rgba(255, 75, 75, 0.4)', offset=0), # Rosso semi-trasparente in alto
                alt.GradientStop(color='rgba(255, 75, 75, 0)', offset=1)    # Trasparente in basso
            ],
            x1=1, y1=1, x2=1, y2=0 # Direzione verticale
        )
    )

    # Layer 2: La linea principale della FC (Rossa, spessa e curva)
    line = base.mark_line(
        color='#ff4b4b', 
        interpolate='monotone', # <--- Rende la linea continua e morbida
        size=3
    )
    
    # Layer 3: Linee verticali tratteggiate azzurre per segnare l'inizio dei test
    layers = [area, line]
    if st.session_state.test_markers:
        m_df = pd.DataFrame({'Secondi': st.session_state.test_markers})
        markers_rule = alt.Chart(m_df).mark_rule(
            color='#00e5ff', # Azzurro brillante
            strokeWidth=2,
            strokeDash=[6,4] # Tratteggio
        ).encode(x='Secondi:Q')
        layers.append(markers_rule)
    
    # Renderizza il grafico combinato (area + linea + marker) con interattività abilitata
    st.altair_chart(alt.layer(*layers).interactive(), use_container_width=True)

# --- SEZIONE INFERIORE: TEST CLINICI ---
st.markdown("---")
st.subheader(texts["test_clinical_title"])

# Organizzazione in Tab per i tre test
tab_db, tab_val, tab_tilt = st.tabs([f"🌬️ {texts['test_deep_breath']}", f"😤 {texts['test_valsalva']}", f"🧍 {texts['test_tilt']}"])

# Funzione helper per gestire la logica comune dei bottoni e calcoli dei test
def run_test_logic(test_id):
    c1, c2 = st.columns(2)
    
    # Pulsante INIZIO TEST
    if c1.button(texts["btn_test_start"], key=f"s_{test_id}", use_container_width=True, disabled=not st.session_state.running):
        st.session_state.active_test = test_id
        st.session_state.freeze_view = False # Assicura che il grafico sia live mentre il test corre
        st.session_state.test_data = pd.DataFrame(columns=['Test_Sec', 'BPM', 'Global_Sec']) # Reset dati test precedente
        st.session_state.test_markers.append(len(st.session_state.history)) # Aggiunge marker verticale sul grafico
        st.rerun()

    # Pulsante FINE TEST
    if c2.button(texts["btn_test_end"], key=f"e_{test_id}", use_container_width=True, disabled=st.session_state.active_test != test_id):
        
        # Soglia minima di validità: tutti i test devono durare almeno 30 secondi
        if len(st.session_state.test_data) < 30:
            st.session_state.test_results[test_id] = {"error": texts["test_wait_30"]}
        else:
            df = st.session_state.test_data
            st.session_state.freeze_view = True # <--- CONGELA IL GRAFICO sui dati di questo test
            
            # Calcoli specifici basati sul tipo di test
            if test_id == "deep_breath":
                st.session_state.test_results[test_id] = {
                    'fc_max': df['BPM'].max(), 'fc_min': df['BPM'].min(), 
                    'fc_diff': df['BPM'].max()-df['BPM'].min(), 'fc_ratio': df['BPM'].max()/df['BPM'].min()
                }
            elif test_id == "valsalva":
                st.session_state.test_results[test_id] = {
                    'fc_max': df['BPM'].max(), 'fc_min': df['BPM'].min(), 'fc_ratio': df['BPM'].max()/df['BPM'].min()
                }
            elif test_id == "tilt":
                # Rapporto 30:15 clinico
                v15 = df.iloc[15]['BPM'] if len(df)>15 else df['BPM'].iloc[-1]
                v30 = df.iloc[30]['BPM'] if len(df)>30 else df['BPM'].iloc[-1]
                st.session_state.test_results[test_id] = {
                    'tilt_15': v15, 'tilt_30': v30, 'tilt_ratio': v30/v15
                }
        # Ferma il cronometro e lo stato attivo del test
        st.session_state.active_test = None
        st.rerun()

    # Visualizzazione dei risultati se presenti
    if st.session_state.test_results.get(test_id):
        res = st.session_state.test_results[test_id]
        if "error" in res: st.warning(res["error"]) # Mostra alert se test troppo breve
        else:
            st.success(texts["test_completed"])
            return res # Restituisce i risultati per la visualizzazione delle metriche
    return None

# Renderizzazione UI specifica per ogni Tab
with tab_db:
    # Icona aggiornata in 🌬️ Respiro Profondo
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
