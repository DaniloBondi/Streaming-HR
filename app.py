import streamlit as st
import requests
import pandas as pd
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz
import altair as alt
import os
import logging
import time
import numpy as np  # Aggiunto per calcoli matematici e RMSSD

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="HR Monitor Pro", layout="wide")

# --- CSS PERSONALIZZATO ---
st.markdown("""
<style>
    div[data-testid="stStatusWidget"] { display: none !important; }
    .block-container { padding-top: 1rem !important; }
    h1 { margin-top: -35px !important; padding-bottom: 10px; font-size: 1.8rem !important; }
    [data-testid="stMetricValue"] { font-size: 1.4rem !important; }
    [data-testid="stMetricLabel"] { font-size: 0.75rem !important; }
    .stButton > button { 
        font-size: 0.7rem !important; 
        padding: 0.1rem 0.3rem !important; 
        min-height: 25px !important;
        line-height: 1.2 !important;
    }
    .timer-box {
        font-family: 'Courier New', monospace;
        font-size: 1.6rem;
        color: #005f6b;
        text-align: center;
        background: rgba(0,0,0,0.05);
        border: 1px solid #005f6b;
        border-radius: 6px;
        padding: 6px;
        margin-bottom: 10px;
        font-weight: bold;
    }
    .timer-small {
        font-size: 0.8rem;
        color: #555;
    }
    /* Stile per far sembrare il radio button più simile a un menu di tab */
    div.row-widget.stRadio > div { flex-direction: row; justify-content: flex-start; gap: 20px; }
</style>
""", unsafe_allow_html=True)

# --- DIZIONARI LINGUE ---
LANGS = {
    "🇮🇹 ITA": {
        "title": "📊❤️ Monitoraggio live frequenza cardiaca",
        "start_rec": "▶️ START REC", "stop_rec": "⏹️ STOP REC",
        "start_test": "🟢 INIZIO TEST", "stop_test": "🔴 FINE TEST",
        "fc_live": "FC (live)", "fc_avg": "Media FC", "fc_max": "FC max", "fc_min": "FC min",
        "clinical": "🩺 Test clinici", "wait": "⏳ Attendi 30s...",
        "respiro": "Respiro Profondo", 
        "valsalva": "Valsalva test - cough test - handgrip test", 
        "tilt": "Tilt test - active standing test",
        "inspira": "🟢 INSPIRA", "espira": "🔵 ESPIRA",
        "fc_diff": "FCmax - FCmin",
        "credits": "**Smartphone app:** App personalizzata creata con Google AI Studio e GitHub Copilot | **Repository:** GitHub | **Backend temporaneo:** npoint.io | **Web app:** framework Streamlit",
        "creator": "**Creator:** Danilo Bondi",
        "privacy_title": "🛡️ Informativa Privacy e Dati",
        "privacy_text": "Nessun salvataggio: i dati restano solo nella RAM temporanea della sessione.<br>Cancellazione: browser chiuso = dati eliminati.<br>Sicurezza ulteriore: via token personalizzato",
        "token_label": "🔑 Token (app custom)", "win_label": "Finestra temporale (sec)",
        "api_label": "🔗 API URL (lasciare vuoto per default)",
        "auth_label": "Metodo Auth",
        "custom_header_label": "Nome header custom",
        "stream_mode": "Modalità Streaming",
        "stats_rr": "📊 Statistiche Sessione (da RR)"
    },
    "🇬🇧 ENG": {
        "title": "📊❤️ Live HR Monitoring",
        "start_rec": "▶️ START REC", "stop_rec": "⏹️ STOP REC",
        "start_test": "🟢 START TEST", "stop_test": "🔴 STOP TEST",
        "fc_live": "HR (live)", "fc_avg": "Avg HR", "fc_max": "Max HR", "fc_min": "Min HR",
        "clinical": "🩺 Clinical Tests", "wait": "⏳ Wait 30s...",
        "respiro": "Deep Breathing", 
        "valsalva": "Valsalva test - cough test - handgrip test", 
        "tilt": "Tilt test - active standing test",
        "inspira": "🟢 INHALE", "espira": "🔵 EXHALE",
        "fc_diff": "HRmax - HRmin",
        "credits": "**Smartphone app:** Custom app created with Google AI Studio and GitHub Copilot | **Repository:** GitHub | **Temporary backend:** npoint.io | **Web app:** framework Streamlit",
        "creator": "**Creator:** Danilo Bondi",
        "privacy_title": "🛡️ Privacy Policy",
        "privacy_text": "No storage: data remains only in RAM.<br>Deletion: browser closing deletes data.<br>Additional security: via customized token",
        "token_label": "🔑 Token (custom app)", "win_label": "Time window (sec)",
        "api_label": "🔗 API URL (leave empty for default)",
        "auth_label": "Auth method",
        "custom_header_label": "Custom header name",
        "stream_mode": "Streaming Mode",
        "stats_rr": "📊 Session Stats (from RR)"
    }
}

# --- COSTANTI ---
DEFAULT_API_URL = "https://api.npoint.io/5d92312f8631a8376f81"

st_autorefresh(interval=500, key="hr_refresher")

# --- STATO DELLA SESSIONE ---
for key, default in {
    'history': pd.DataFrame(columns=['Sec', 'BPM']), 'running': False,
    'active_test': None, 'freeze_view': False,
    'test_data': pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec']),
    'markers': [], 'results': {}, 'last_ts': None,
    'use_streaming': False, 'stream_error': None,
    'last_fetch_time': 0, 'debug_mode': False, 'last_bpm': None,
    'rr_history': [],         # Registro lineare globale degli intervalli RR
    'test_rr_history': []     # Registro degli intervalli RR per il test attivo
}.items():
    if key not in st.session_state: st.session_state[key] = default

# --- FUNZIONI UTILI DI CALCOLO RR ---
def calcola_metriche_rr(rr_list):
    """Calcola parametri statistici e RMSSD partendo da una lista di intervalli RR in ms"""
    if not rr_list or len(rr_list) == 0:
        return {"max": 0, "min": 0, "mean": 0, "rmssd": 0}
    
    # Conversione intervalli RR (ms) in valori di Frequenza Cardiaca istantanea (BPM)
    bpms = [60000.0 / rr for rr in rr_list if rr > 0]
    
    rmssd = 0.0
    if len(rr_list) > 1:
        diffs = np.diff(rr_list)
        rmssd = np.sqrt(np.mean(diffs ** 2))
        
    return {
        "max": max(bpms) if bpms else 0,
        "min": min(bpms) if bpms else 0,
        "mean": np.mean(bpms) if bpms else 0,
        "rmssd": rmssd
    }

# --- FUNZIONI CALLBACK ---
def cb_start_rec():
    if st.session_state.use_streaming:
        if not device_ip or not stream_token:
            st.warning("Device IP o Streaming Token mancanti.")
            return
    else:
        if not api_url_effective:
            st.warning("API URL mancante.")
            return
    st.session_state.running, st.session_state.freeze_view = True, False
    st.session_state.rr_history = []
    st.session_state.last_ts = None
    st.session_state.last_bpm = None

def cb_stop_rec():
    st.session_state.running, st.session_state.active_test = False, None

def cb_reset():
    st.session_state.history = pd.DataFrame(columns=['Sec', 'BPM'])
    st.session_state.markers, st.session_state.results = [], {}
    st.session_state.freeze_view, st.session_state.running, st.session_state.active_test = False, False, None
    st.session_state.rr_history = []
    st.session_state.test_rr_history = []
    st.session_state.last_ts = None
    st.session_state.last_bpm = None

def cb_start_test(name):
    st.session_state.active_test, st.session_state.freeze_view = name, False
    st.session_state.test_data = pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec'])
    st.session_state.test_rr_history = []
    st.session_state.markers.append(len(st.session_state.history))

def cb_stop_test(name):
    # Verifica la durata complessiva basandosi sulla somma degli RR raccolti (30 secondi = 30000ms)
    durata_test_ms = sum(st.session_state.test_rr_history)
    
    if durata_test_ms < 30000 and len(st.session_state.test_data) < 30:
        st.session_state.results[name] = "error"
    else:
        st.session_state.freeze_view = True
        if name in ["res", "val"]:
            # Calcolo dei parametri direttamente sugli intervalli RR registrati nel test
            test_bpms = [60000.0 / rr for rr in st.session_state.test_rr_history if rr > 0]
            t_max = max(test_bpms) if test_bpms else 0
            t_min = min(test_bpms) if test_bpms else 0
            st.session_state.results[name] = {
                'max': t_max, 'min': t_min, 'diff': t_max - t_min,
                'ratio': t_max / t_min if t_min > 0 else 0
            }
        else:
            # Tilt test / Active Standing (Rapporto 30:15 basato sulla temporizzazione dei battiti RR)
            cum_times = np.cumsum(st.session_state.test_rr_history)
            # Trova l'indice del battito più vicino al 15° secondo (15000ms) e al 30° secondo (30000ms)
            idx_15 = (np.abs(cum_times - 15000)).argmin()
            idx_30 = (np.abs(cum_times - 30000)).argmin()
            
            rr_15 = st.session_state.test_rr_history[idx_15] if idx_15 < len(st.session_state.test_rr_history) else st.session_state.test_rr_history[-1]
            rr_30 = st.session_state.test_rr_history[idx_30] if idx_30 < len(st.session_state.test_rr_history) else st.session_state.test_rr_history[-1]
            
            v15 = 60000.0 / rr_15 if rr_15 > 0 else 0
            v30 = 60000.0 / rr_30 if rr_30 > 0 else 0
            st.session_state.results[name] = {'v15': v15, 'v30': v30, 'ratio': v30 / v15 if v15 > 0 else 0}
            
    st.session_state.active_test = None

# --- STREAMING DATA RETRIEVAL WITH IMPROVED ERROR HANDLING ---
def fetch_vitals_data_streaming(device_ip, device_port, stream_token, timeout=1.5):
    try:
        endpoint = f"http://{device_ip}:{device_port}/vitals?token={stream_token}"
        res = requests.get(endpoint, timeout=timeout)
        if res.status_code == 200:
            return res.json(), None
        else:
            return None, f"⚠️ Status code {res.status_code}"
    except requests.exceptions.Timeout:
        return None, "⏱️ Request Timeout: Device not responding"
    except requests.exceptions.ConnectionError:
        return None, "🔌 Connection Failed: Check network/IP"
    except Exception as ex:
        return None, f"⚠️ Error: {str(ex)}"

# API CALL (Ritorna l'intero dizionario JSON per elaborare timestamp e RR grezzi)
def _try_request(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=1)
        if st.session_state.debug_mode:
            logger.info(f"[API] URL: {url} | Status: {r.status_code}")
        if r.status_code == 200:
            try:
                data = r.json()
                if st.session_state.debug_mode:
                    logger.info(f"[API] Response: {data}")
                return data
            except Exception as e:
                if st.session_state.debug_mode:
                    logger.error(f"[API] JSON parse error: {e}")
                return None
        else:
            if st.session_state.debug_mode:
                logger.error(f"[API] Bad status code: {r.status_code}")
            return None
    except Exception as e:
        if st.session_state.debug_mode:
            logger.error(f"[API] Request failed: {e}")
        return None

def get_bpm(api_url, auth_method="Auto", custom_header_name="X-API-KEY", token=None):
    if not api_url:
        return None
    url = api_url.strip()
    if not token and auth_method != "Auto":
        return None
    
    if token:
        if auth_method == "Auto":
            for h in [{"Authorization": f"Bearer {token}"}, {"Authorization": f"Token {token}"}, {"X-API-Key": token}, {custom_header_name: token}]:
                v = _try_request(url, h)
                if v is not None: return v
            return None
        else:
            if auth_method == "Bearer": headers = {"Authorization": f"Bearer {token}"}
            elif auth_method == "Token": headers = {"Authorization": f"Token {token}"}
            elif auth_method == "X-API-Key": headers = {"X-API-Key": token}
            else: headers = {custom_header_name: token}
            return _try_request(url, headers)
    else:
        return _try_request(url, {})

# --- SIDEBAR ---
with st.sidebar:
    lang = st.radio("Lang", ["🇮🇹 ITA", "🇬🇧 ENG"], horizontal=True, label_visibility="collapsed")
    t = LANGS[lang]
    st.markdown("---")
    st.markdown(f"### 🕐 {datetime.now(pytz.timezone('Europe/Rome')).strftime('%H:%M:%S')}")

    st.session_state.debug_mode = st.checkbox("🐛 Debug Mode", value=False)
    st.session_state.use_streaming = st.checkbox(t["stream_mode"], value=False)
    
    if st.session_state.use_streaming:
        st.markdown("### 📱 Streaming Settings")
        device_ip = st.text_input("Mobile IP Address", value="10.215.78.116")
        device_port = st.number_input("Server Port", value=8080, step=1)
        stream_token = st.text_input("Streamer Security Token", type="password", value="VITAL-66A51AC5")
        poll_interval = st.slider("Sampling Interval (sec)", 0.2, 5.0, 1.0, 0.1)
        token = api_url = api_url_effective = custom_header_name = None
    else:
        st.markdown("### 🔧 API Settings")
        api_url_custom = st.text_input(t["api_label"], value="").strip()
        api_url_effective = api_url_custom if api_url_custom else DEFAULT_API_URL
        token = st.text_input(t["token_label"], type="password", value="").strip() or None
        
        if token:
            auth_method = st.selectbox(t["auth_label"], ["Auto", "Bearer", "Token", "X-API-Key", "Custom header"], index=0)
            custom_header_name = st.text_input(t["custom_header_label"], value="X-My-App-Token") if auth_method == "Custom header" else ""
        else:
            auth_method, custom_header_name = "Auto", ""
        api_url, device_ip, device_port, stream_token, poll_interval = api_url_custom, None, None, None, 1.0
    
    c1, c2 = st.columns(2)
    if st.session_state.use_streaming:
        c1.button(t["start_rec"], type="primary", disabled=not device_ip or not stream_token, on_click=cb_start_rec)
    else:
        c1.button(t["start_rec"], type="primary", disabled=not api_url_effective, on_click=cb_start_rec)
    c2.button(t["stop_rec"], on_click=cb_stop_rec)

    win = st.slider(t["win_label"], 10, 300, 60)
    st.button("🗑 Reset", use_container_width=True, on_click=cb_reset)

    # --- METRICHE SIDEBAR (RICHIESTA UTENTE) ---
    st.markdown("---")
    st.markdown(f"### {t['stats_rr']}")
    metrics_globali = calcola_metriche_rr(st.session_state.rr_history)
    if st.session_state.rr_history:
        st.metric(t["fc_max"], f"{metrics_globali['max']:.0f} BPM")
        st.metric(t["fc_min"], f"{metrics_globali['min']:.0f} BPM")
        st.metric("RMSSD", f"{metrics_globali['rmssd']:.1f} ms")
    else:
        st.caption("Nessun dato RR registrato.")

    st.markdown("---")
    st.caption(t["credits"])
    lc1, lc2 = st.columns(2)
    try:
        if os.path.exists("logo UDA.png"): lc1.image("logo UDA.png", width=80)
        if os.path.exists("Logo UnivAq.png"): lc2.image("Logo UnivAq.png", width=80)
    except: pass
    st.caption(t["creator"])
    with st.expander(t["privacy_title"]): st.markdown(f"<small>{t['privacy_text']}</small>", unsafe_allow_html=True)

# --- DASHBOARD PRINCIPALE ---
st.title(t["title"])

# --- CONTINUOUS DATA POLLING & GAPS MANAGEMENT ---
if st.session_state.running:
    current_time = time.time()
    if current_time - st.session_state.last_fetch_time >= poll_interval:
        payload = None
        if st.session_state.use_streaming:
            payload, error = fetch_vitals_data_streaming(device_ip, device_port, stream_token)
            if error:
                st.session_state.stream_error = error
                payload = None
            else:
                st.session_state.stream_error = None
        else:
            payload = get_bpm(api_url_effective, auth_method, custom_header_name, token)
            
        sec_now = len(st.session_state.history)
        
        if payload:
            ts = payload.get("timestamp")
            bpm = payload.get("heart_rate") or payload.get("bpm")
            rr_intervals = payload.get("rr_intervals", [])
            
            # SE IL TIMESTAMP NON CAMBIA = STREAMING BLOCCATO -> INSERISCI UN BUCO (NaN)
            if st.session_state.last_ts is not None and st.session_state.last_ts == ts:
                new_row = pd.DataFrame([{'Sec': sec_now, 'BPM': float('nan')}])
                st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
                st.session_state.last_bpm = None
            else:
                # NUOVO PACCHETTO VALIDO
                st.session_state.last_ts = ts
                if bpm:
                    st.session_state.last_bpm = bpm
                    new_row = pd.DataFrame([{'Sec': sec_now, 'BPM': bpm}])
                    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
                    
                    if st.session_state.active_test:
                        st.session_state.test_data = pd.concat([st.session_state.test_data, pd.DataFrame([{'T_Sec': len(st.session_state.test_data), 'BPM': bpm, 'G_Sec': sec_now}])], ignore_index=True)
                
                if rr_intervals:
                    st.session_state.rr_history.extend(rr_intervals)
                    if st.session_state.active_test:
                        st.session_state.test_rr_history.extend(rr_intervals)
        else:
            # RICHIESTA FALLITA / NO LIVE DATA -> INSERISCI UN BUCO (NaN)
            new_row = pd.DataFrame([{'Sec': sec_now, 'BPM': float('nan')}])
            st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
            st.session_state.last_bpm = None
            
        st.session_state.last_fetch_time = current_time
        st.rerun()

if st.session_state.stream_error:
    st.warning(st.session_state.stream_error)

# --- VISUALIZZAZIONE METRICHE SUL PANNELLO (Calcolate su RR) ---
m1, m2, m3, m4, m5 = st.columns(5)
hist = st.session_state.history

if not hist.empty:
    display_bpm = st.session_state.last_bpm if st.session_state.last_bpm is not None else float('nan')
    
    # Se abbiamo intervalli RR registrati, usiamo quelli per le statistiche globali
    if st.session_state.rr_history:
        metrics_globali = calcola_metriche_rr(st.session_state.rr_history)
        avg_val = f"{metrics_globali['mean']:.1f}"
        max_val = f"{metrics_globali['max']:.0f}"
        min_val = f"{metrics_globali['min']:.0f}"
        rmssd_val = f"{metrics_globali['rmssd']:.1f} ms"
    else:
        # Fallback se non ci sono ancora RR salvati
        valid_bpms = hist['BPM'].dropna()
        avg_val = f"{valid_bpms.mean():.1f}" if not valid_bpms.empty else "--"
        max_val = f"{valid_bpms.max():.0f}" if not valid_bpms.empty else "--"
        min_val = f"{valid_bpms.min():.0f}" if not valid_bpms.empty else "--"
        rmssd_val = "--"
        
    m1.metric(t["fc_live"], f"{display_bpm:.0f} BPM" if pd.notna(display_bpm) else "--")
    m2.metric(t["fc_avg"], avg_val)
    m3.metric(t["fc_max"], max_val)
    m4.metric(t["fc_min"], min_val)
    m5.metric("RMSSD", rmssd_val)
else:
    m1.metric(t["fc_live"], "--")
    m2.info("Avvia START REC")

if st.session_state.active_test:
    elapsed = len(st.session_state.test_data)
    if st.session_state.active_test == "res":
        cycle_time = elapsed % 10
        phase_text, sec_left = (t["inspira"], 5 - cycle_time) if cycle_time < 5 else (t["espira"], 10 - cycle_time)
        st.markdown(f"<div class='timer-box'>{phase_text} ({sec_left}s)<br><span class='timer-small'>⏱️ TOT: {elapsed}s</span></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='timer-box'>⏱️ TEST: {elapsed}s</div>", unsafe_allow_html=True)

# --- GRAFICO CON SUPPORTO PER I BUCHI (Altair ignora i NaN spezzando la linea) ---
if not hist.empty:
    df_plot = hist[(hist['Sec'] >= st.session_state.test_data['G_Sec'].min()-2) & (hist['Sec'] <= st.session_state.test_data['G_Sec'].max()+2)] if st.session_state.freeze_view else hist.tail(win)
    
    # Range dinamico dell'asse Y per evitare crash se ci sono NaN
    valid_plot_bpms = df_plot['BPM'].dropna()
    y_min = valid_plot_bpms.min() - 5 if not valid_plot_bpms.empty else 40
    y_max = valid_plot_bpms.max() + 5 if not valid_plot_bpms.empty else 100

    line = alt.Chart(df_plot).mark_line(color='#ff4b4b', interpolate='monotone', size=3).encode(
        x=alt.X('Sec:Q', title="Secondi", scale=alt.Scale(nice=False)),
        y=alt.Y('BPM:Q', title="BPM", scale=alt.Scale(domain=[y_min, y_max]))
    )
    layers = [line]
    if st.session_state.markers:
        layers.append(alt.Chart(pd.DataFrame({'Sec': st.session_state.markers})).mark_rule(color='#00e5ff', strokeDash=[5,5]).encode(x='Sec:Q'))
    st.altair_chart(alt.layer(*layers).interactive(), use_container_width=True)

# --- MENU TEST CLINICI ---
st.markdown("---")
st.subheader(t["clinical"])

opzioni_test = [f"🌬️ {t['respiro']}", f"😤 {t['valsalva']}", f"🧍 {t['tilt']}"]
scelta_test = st.radio("Seleziona Test", opzioni_test, horizontal=True, label_visibility="collapsed")

def render_test_ui(name):
    cs, ce = st.columns(2)
    cs.button(t["start_test"], key=f"s_{name}", disabled=not st.session_state.running, on_click=cb_start_test, args=(name,))
    ce.button(t["stop_test"], key=f"e_{name}", disabled=st.session_state.active_test != name, on_click=cb_stop_test, args=(name,))

    res = st.session_state.results.get(name)
    if res == "error": 
        st.warning(t["wait"])
    elif isinstance(res, dict):
        st.success("Test OK (Calcolato su intervalli RR grezzi)")
        if 'max' in res:
            rc = st.columns(4)
            rc[0].metric(t["fc_max"], f"{res['max']:.0f}")
            rc[1].metric(t["fc_min"], f"{res['min']:.0f}")
            rc[2].metric(t["fc_diff"], f"{res['diff']:.0f}")
            rc[3].metric("Ratio (Max/Min)", f"{res['ratio']:.2f}")
        else:
            rc = st.columns(3)
            rc[0].metric("FC equivalente a ~15s", f"{res['v15']:.0f} BPM")
            rc[1].metric("FC equivalente a ~30s", f"{res['v30']:.0f} BPM")
            rc[2].metric("Ratio 30:15", f"{res['ratio']:.2f}")

if scelta_test == opzioni_test[0]: render_test_ui("res")
elif scelta_test == opzioni_test[1]: render_test_ui("val")
else: render_test_ui("tilt")
