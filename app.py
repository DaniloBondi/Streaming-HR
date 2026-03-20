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

# --- INIEZIONE CSS PER DIMENSIONI FONT ---
st.markdown("""
<style>
/* Riduci font metriche principali (valori) */
[data-testid="stMetricValue"] {
    font-size: 1.8rem !important;
}
/* Riduci font label metriche */
[data-testid="stMetricLabel"] {
    font-size: 0.9rem !important;
}
/* Riduci font pulsanti sidebar (START REC / STOP REC) */
.stButton > button {
    font-size: 0.85rem !important;
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
        "privacy_title": "🛡️ Informativa Privacy e Dati",
        "privacy_text": "Nessun salvataggio: i dati restano solo nella RAM temporanea della sessione.<br>Cancellazione: alla chiusura del browser, i dati vengono eliminati.<br>Sicurezza: il token Pulsoid inserito non viene mai archiviato.",
        "info_token": "👈 Inserisci il tuo Token Pulsoid nella barra laterale per avviare il monitoraggio.",
        "hr_live": "FC (live)",
        "avg_bpm": "Media FC",
        "fc_max_global": "FC max",
        "fc_min_global": "FC min",
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
        "tilt_ratio": "Rapporto 30:15",
        "tilt_15": "FC a 15s",
        "tilt_30": "FC a 30s",
        "start_recording": "⚠️ Avvia prima la registrazione generale con START REC",
        "test_no_data": "Nessun dato del test disponibile",
        "test_wait_30": "⏳ Attendi almeno 30 secondi per avere un risultato valido"
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
        "tilt_ratio": "30:15 Ratio",
        "tilt_15": "HR at 15s",
        "tilt_30": "HR at 30s",
        "start_recording": "⚠️ Start general recording with START REC first",
        "test_no_data": "No test data available",
        "test_wait_30": "⏳ Wait at least 30 seconds for a valid result"
    }
}

st_autorefresh(interval=500, key="hr_update")

# --- INIZIALIZZAZIONE SESSION STATE ---
if 'history' not in st.session_state:
    st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM'])
if 'running' not in st.session_state:
    st.session_state.running = False
if 'last_timestamp' not in st.session_state:
    st.session_state.last_timestamp = ""

# Stati per i test clinici e marker sul grafico
if 'test_markers' not in st.session_state:
    st.session_state.test_markers = [] # Memorizza i secondi in cui inizia un test
if 'active_test' not in st.session_state:
    st.session_state.active_test = None
if 'test_data' not in st.session_state:
    st.session_state.test_data = pd.DataFrame(columns=['Test_Sec', 'BPM'])
if 'test_results' not in st.session_state:
    st.session_state.test_results = {}

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

# --- SIDEBAR ---
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
        st.session_state.active_test = None

    window_size = st.slider(texts["window_slider"], 10, 300, 60)

    if not st.session_state.history.empty:
        csv = st.session_state.history.to_csv(index=False).encode('utf-8')
        st.download_button(texts["btn_csv"], data=csv, file_name="hr_data.csv", use_container_width=True)
        if st.button(texts["btn_reset"], use_container_width=True):
            st.session_state.history = pd.DataFrame(columns=['Secondi', 'BPM'])
            st.session_state.last_timestamp = ""
            st.session_state.running = False
            st.session_state.active_test = None
            st.session_state.test_markers = []
            st.session_state.test_data = pd.DataFrame(columns=['Test_Sec', 'BPM'])
            st.session_state.test_results = {}
            st.rerun()

    st.markdown("---")
    st.caption("**Smartphone app:** Pulsoid | **Repository:** GitHub | **Web app:** Streamlit | **AI:** Gemini")
    
    st.write("")
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

# Metriche principali: 4 Colonne per includere FC Max e FC Min
col_live, col_avg, col_max, col_min = st.columns(4)

if bpm:
    if st.session_state.running:
        col_live.metric(texts["hr_live"], f"{bpm} BPM")
        
        if st.session_state.last_timestamp != current_ts:
            sec_elapsed = len(st.session_state.history)
            new_row = pd.DataFrame([{'Secondi': sec_elapsed, 'BPM': bpm}])
            st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
            st.session_state.last_timestamp = current_ts
            
            # Registrazione dati test
            if st.session_state.active_test is not None:
                test_sec = len(st.session_state.test_data)
                test_row = pd.DataFrame([{'Test_Sec': test_sec, 'BPM': bpm}])
                st.session_state.test_data = pd.concat([st.session_state.test_data, test_row], ignore_index=True)

        if not st.session_state.history.empty:
            avg_bpm_session = st.session_state.history['BPM'].mean()
            max_bpm_session = st.session_state.history['BPM'].max()
            min_bpm_session = st.session_state.history['BPM'].min()
            
            col_avg.metric(texts["avg_bpm"], f"{avg_bpm_session:.1f}")
            col_max.metric(texts["fc_max_global"], f"{max_bpm_session:.0f}")
            col_min.metric(texts["fc_min_global"], f"{min_bpm_session:.0f}")
            
    else:
        if not st.session_state.history.empty:
            avg_bpm_total = st.session_state.history['BPM'].mean()
            max_bpm_total = st.session_state.history['BPM'].max()
            min_bpm_total = st.session_state.history['BPM'].min()
            
            col_live.metric(texts["hr_paused"], f"{bpm} BPM")
            col_avg.metric(texts["avg_bpm"], f"{avg_bpm_total:.1f}")
            col_max.metric(texts["fc_max_global"], f"{max_bpm_total:.0f}")
            col_min.metric(texts["fc_min_global"], f"{min_bpm_total:.0f}")
            st.success(f"{texts['session_done']} {len(st.session_state.history)} {texts['sec']}.")
        else:
            col_live.metric(texts["hr_paused"], f"{bpm} BPM")
            col_avg.warning(texts["paused_msg"])
elif user_token:
    st.error(texts["error_signal"])


# --- GRAFICO INTERATTIVO (Spostato in alto) ---
st.markdown("---")
if not st.session_state.history.empty:
    data_subset = st.session_state.history.tail(window_size)
    
    avg_bpm = data_subset['BPM'].mean()
    y_min = max(20, avg_bpm - 20)
    y_max = y_min + 50

    line = alt.Chart(data_subset).mark_line(color='#ff4b4b', interpolate='monotone').encode(
        x=alt.X('Secondi:Q', axis=alt.Axis(grid=True, tickCount=window_size//5, gridDash=[4,4]), title=texts["chart_x"]),
        y=alt.Y('BPM:Q', scale=alt.Scale(domain=[y_min, y_max]), title=texts["chart_y"])
    ).interactive()

    trend = line.transform_regression('Secondi', 'BPM').mark_line(color='white', size=2, opacity=0.8)

    # Aggiungo i marker verticali se presenti nella finestra temporale attuale
    chart_layers = [line, trend]
    if st.session_state.test_markers:
        markers_df = pd.DataFrame({'Secondi': st.session_state.test_markers})
        # Filtra i marker per mostrare solo quelli visibili nella finestra
        markers_in_window = markers_df[markers_df['Secondi'] >= data_subset['Secondi'].min()]
        
        if not markers_in_window.empty:
            rules = alt.Chart(markers_in_window).mark_rule(color='#00e5ff', strokeWidth=2, strokeDash=[4,4]).encode(
                x='Secondi:Q'
            )
            chart_layers.append(rules)

    st.altair_chart(alt.layer(*chart_layers), use_container_width=True)


# --- SEZIONE TEST CLINICI (Spostata in basso) ---
st.subheader(texts["test_clinical_title"])

tab_db, tab_val, tab_tilt = st.tabs([f"🌬️ {texts['test_deep_breath']}", f"😤 {texts['test_valsalva']}", f"🧍 {texts['test_tilt']}"])

def render_test_ui(test_id, tab_texts):
    c1, c2 = st.columns(2)
    
    # Bottone INIZIO (Salva anche il marker nel grafico)
    if c1.button(texts["btn_test_start"], key=f"start_{test_id}", use_container_width=True, disabled=not st.session_state.running):
        st.session_state.active_test = test_id
        st.session_state.test_data = pd.DataFrame(columns=['Test_Sec', 'BPM'])
        st.session_state.test_results[test_id] = None 
        # Aggiungi marker verticale sul grafico principale
        st.session_state.test_markers.append(len(st.session_state.history))
        st.rerun()

    # Bottone FINE
    if c2.button(texts["btn_test_end"], key=f"end_{test_id}", use_container_width=True, disabled=(st.session_state.active_test != test_id)):
        st.session_state.active_test = None
        df_test = st.session_state.test_data
        
        # Gestione alert dei 30 secondi per tutti i test
        if not df_test.empty:
            if len(df_test) < 30:
                st.session_state.test_results[test_id] = {"error": texts["test_wait_30"]}
            else:
                if test_id == "deep_breath":
                    fc_max = df_test['BPM'].max()
                    fc_min = df_test['BPM'].min()
                    st.session_state.test_results[test_id] = {
                        'fc_max': fc_max, 'fc_min': fc_min,
                        'fc_diff': fc_max - fc_min, 'fc_ratio': fc_max / fc_min if fc_min > 0 else 0
                    }
                elif test_id == "valsalva":
                    fc_max = df_test['BPM'].max()
                    fc_min = df_test['BPM'].min()
                    st.session_state.test_results[test_id] = {
                        'fc_max': fc_max, 'fc_min': fc_min,
                        'fc_ratio': fc_max / fc_min if fc_min > 0 else 0
                    }
                elif test_id == "tilt":
                    bpm_15 = df_test[df_test['Test_Sec'] == 15]['BPM'].values
                    bpm_30 = df_test[df_test['Test_Sec'] == 30]['BPM'].values
                    v_15 = bpm_15[0] if len(bpm_15) > 0 else df_test.iloc[15]['BPM']
                    v_30 = bpm_30[0] if len(bpm_30) > 0 else df_test.iloc[30]['BPM']
                    st.session_state.test_results[test_id] = {
                        'tilt_15': v_15, 'tilt_30': v_30,
                        'tilt_ratio': (v_30 / v_15) if (v_15 and v_30 and v_15 > 0) else None
                    }
        st.rerun()

    if not st.session_state.running:
        st.warning(texts["start_recording"])
    elif st.session_state.active_test == test_id:
        st.info(f"{texts['test_running']} {len(st.session_state.test_data)} {texts['sec']}")
    elif st.session_state.test_results.get(test_id):
        if "error" in st.session_state.test_results[test_id]:
            st.warning(st.session_state.test_results[test_id]["error"])
        else:
            st.success(texts['test_completed'])
            return True
    return False

# TAB 1: Deep Breathing
with tab_db:
    if render_test_ui("deep_breath", texts):
        res = st.session_state.test_results["deep_breath"]
        r1, r2, r3, r4 = st.columns(4)
        r1.metric(texts["fc_max"], f"{res['fc_max']:.0f}")
        r2.metric(texts["fc_min"], f"{res['fc_min']:.0f}")
        r3.metric(texts["fc_diff"], f"{res['fc_diff']:.0f}")
        r4.metric(texts["fc_ratio"], f"{res['fc_ratio']:.2f}")

# TAB 2: Valsalva
with tab_val:
    if render_test_ui("valsalva", texts):
        res = st.session_state.test_results["valsalva"]
        r1, r2, r3 = st.columns(3)
        r1.metric(texts["fc_max"], f"{res['fc_max']:.0f}")
        r2.metric(texts["fc_min"], f"{res['fc_min']:.0f}")
        r3.metric(texts["fc_ratio"], f"{res['fc_ratio']:.2f}")

# TAB 3: Tilt Test
with tab_tilt:
    if render_test_ui("tilt", texts):
        res = st.session_state.test_results["tilt"]
        r1, r2, r3 = st.columns(3)
        r1.metric(texts["tilt_15"], f"{res['tilt_15']:.0f}")
        r2.metric(texts["tilt_30"], f"{res['tilt_30']:.0f}")
        r3.metric(texts["tilt_ratio"], f"{res['tilt_ratio']:.2f}")
