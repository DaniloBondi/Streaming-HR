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
import numpy as np

# configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- CONFIGURAZIONE PAGINA ---
st.set_page_config(page_title="HR Monitor Pro", layout="wide", page_icon="📊")

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
        "stats_rr": "📊 Statistiche Sessione (da RR)",
        "diagnostics_title": "🔍 Pannello di Diagnostica Live",
        "no_packet": "Nessun pacchetto ricevuto",
        "packet_latency": "Latenza ultimo pacchetto",
        "collected_rr": "Intervalli RR totali",
        "graph_smooth_toggle": "⚡ Grafico ultra-fluido",
        "error_no_data": "Nessun dato RR grezzo registrato",
        "error_short_data": "I dati sono inferiori a 30s. Risultato non attendibile."
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
        "stats_rr": "📊 Session Stats (from RR)",
        "diagnostics_title": "🔍 Live Diagnostics Panel",
        "no_packet": "No packets received yet",
        "packet_latency": "Last packet latency",
        "collected_rr": "Collected RR Intervals",
        "graph_smooth_toggle": "⚡ Ultra-fluid Chart",
        "error_no_data": "No raw RR intervals recorded",
        "error_short_data": "The recorded data is under 30s. Result may be unreliable."
    }
}

# --- COSTANTI ---
DEFAULT_API_URL = "https://api.npoint.io/5d92312f8631a8376f81"

# --- DETECT STREAMING MODE FOR ADAPTIVE AUTOREFRESH ---
is_streaming = st.session_state.get('use_streaming', False)
refresh_rate = 500 if is_streaming else 2000
st_autorefresh(interval=refresh_rate, key="hr_refresher")

# --- STATO DELLA SESSIONE ---
for key, default in {
    'history': pd.DataFrame(columns=['Sec', 'BPM']), 'running': False,
    'active_test': None, 'freeze_view': False,
    'test_data': pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec']),
    'markers': [], 'results': {}, 'last_ts': None,
    'use_streaming': False, 'stream_error': None,
    'last_fetch_time': 0, 'last_bpm': None,
    'rr_history': [],          
    'test_rr_history': [],     
    'rec_start_time': None,    
    'test_start_time': None,   
    'last_valid_packet_time': 0, 
    'rr_time_accumulated': 0.0, 
    'test_rr_time_accumulated': 0.0,
    'last_raw_payload': None,   
    'packet_counter': 0
}.items():
    if key not in st.session_state: st.session_state[key] = default

# --- FUNZIONI UTILI DI CALCOLO RR ---
def calcola_metriche_rr(rr_list):
    if not rr_list or len(rr_list) == 0:
        return {"max": 0, "min": 0, "mean": 0, "rmssd": 0}
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
    st.session_state.rec_start_time = time.time()
    st.session_state.last_valid_packet_time = time.time()
    st.session_state.rr_time_accumulated = 0.0
    st.session_state.packet_counter = 0
    st.session_state.last_raw_payload = None

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
    st.session_state.rec_start_time = None
    st.session_state.test_start_time = None
    st.session_state.last_valid_packet_time = 0
    st.session_state.rr_time_accumulated = 0.0
    st.session_state.test_rr_time_accumulated = 0.0
    st.session_state.packet_counter = 0
    st.session_state.last_raw_payload = None

def cb_start_test(name):
    st.session_state.active_test, st.session_state.freeze_view = name, False
    st.session_state.test_data = pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec'])
    st.session_state.test_rr_history = []
    st.session_state.test_rr_time_accumulated = 0.0
    
    marker_sec = st.session_state.rr_time_accumulated
    st.session_state.markers.append(marker_sec)
    st.session_state.test_start_time = time.time()

def cb_stop_test(name):
    durata_reale_sec = time.time() - st.session_state.test_start_time if st.session_state.test_start_time else 0
    durata_test_ms = sum(st.session_state.test_rr_history)
    
    if not st.session_state.test_rr_history:
        st.session_state.results[name] = "error_no_data"
    elif durata_reale_sec < 30 and durata_test_ms < 30000:
        st.session_state.results[name] = "error_short"
    else:
        st.session_state.freeze_view = True
        if name in ["res", "val"]:
            test_bpms = [60000.0 / rr for rr in st.session_state.test_rr_history if rr > 0]
            if not test_bpms:
                st.session_state.results[name] = "error_no_data"
            else:
                t_max = max(test_bpms)
                t_min = min(test_bpms)
                st.session_state.results[name] = {
                    'max': t_max, 'min': t_min, 'diff': t_max - t_min,
                    'ratio': t_max / t_min if t_min > 0 else 1.0
                }
        else:
            cum_times = np.cumsum(st.session_state.test_rr_history)
            if len(cum_times) == 0:
                st.session_state.results[name] = "error_no_data"
            else:
                idx_15 = (np.abs(cum_times - 15000)).argmin()
                idx_30 = (np.abs(cum_times - 30000)).argmin()
                
                rr_15 = st.session_state.test_rr_history[idx_15] if idx_15 < len(st.session_state.test_rr_history) else st.session_state.test_rr_history[-1] if len(st.session_state.test_rr_history) > 0 else 0
                rr_30 = st.session_state.test_rr_history[idx_30] if idx_30 < len(st.session_state.test_rr_history) else st.session_state.test_rr_history[-1] if len(st.session_state.test_rr_history) > 0 else 0
                
                v15 = 60000.0 / rr_15 if rr_15 > 0 else 0
                v30 = 60000.0 / rr_30 if rr_30 > 0 else 0
                st.session_state.results[name] = {
                    'v15': v15, 'v30': v30, 
                    'ratio': v30 / v15 if v15 > 0 else 1.0
                }
            
    st.session_state.active_test = None

# --- STREAMING DATA RETRIEVAL ---
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

def _try_request(url, headers):
    try:
        r = requests.get(url, headers=headers, timeout=1.5)
        if r.status_code == 200:
            try:
                return r.json()
            except Exception:
                return None
        return None
    except Exception:
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

    st.session_state.use_streaming = st.checkbox(t["stream_mode"], value=st.session_state.use_streaming)
    grafico_veloce = st.toggle(t["graph_smooth_toggle"], value=True)
    
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

# --- DATA POLLING LOOP ---
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
            
        if payload:
            st.session_state.last_raw_payload = payload
            ts = payload.get("timestamp")
            bpm = payload.get("heart_rate") or payload.get("bpm")
            rr_intervals = payload.get("rr_intervals", [])
            
            is_new_packet = (st.session_state.last_ts is None) or (st.session_state.last_ts != ts)
            should_update_vitals = is_new_packet or (st.session_state.use_streaming and len(rr_intervals) > 0)
            
            if not should_update_vitals:
                if time.time() - st.session_state.last_valid_packet_time > 15:
                    if not st.session_state.history.empty and pd.notna(st.session_state.history.iloc[-1]['BPM']):
                        gap_sec = st.session_state.rr_time_accumulated + (time.time() - st.session_state.last_valid_packet_time)
                        new_row = pd.DataFrame([{'Sec': gap_sec, 'BPM': float('nan')}])
                        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
                    st.session_state.last_bpm = None
            else:
                st.session_state.last_ts = ts
                st.session_state.last_valid_packet_time = time.time()
                st.session_state.packet_counter += 1
                
                if rr_intervals:
                    new_rows = []
                    new_test_rows = []
                    for rr in rr_intervals:
                        if rr > 0:
                            st.session_state.rr_time_accumulated += rr / 1000.0
                            beat_bpm = 60000.0 / rr  
                            
                            new_rows.append({'Sec': st.session_state.rr_time_accumulated, 'BPM': beat_bpm})
                            st.session_state.rr_history.append(rr)
                            
                            if st.session_state.active_test:
                                st.session_state.test_rr_time_accumulated += rr / 1000.0
                                new_test_rows.append({
                                    'T_Sec': st.session_state.test_rr_time_accumulated, 
                                    'BPM': beat_bpm, 
                                    'G_Sec': st.session_state.rr_time_accumulated
                                })
                                st.session_state.test_rr_history.append(rr)
                                
                    if new_rows:
                        st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame(new_rows)], ignore_index=True)
                        st.session_state.last_bpm = new_rows[-1]['BPM']  
                        
                    if new_test_rows and st.session_state.active_test:
                        st.session_state.test_data = pd.concat([st.session_state.test_data, pd.DataFrame(new_test_rows)], ignore_index=True)
                else:
                    if bpm:
                        st.session_state.last_bpm = bpm
                        sec_now = int(time.time() - st.session_state.rec_start_time) if st.session_state.rec_start_time else 0
                        new_row = pd.DataFrame([{'Sec': sec_now, 'BPM': bpm}])
                        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
                        
                        if st.session_state.active_test:
                            t_elapsed = int(time.time() - st.session_state.test_start_time)
                            st.session_state.test_data = pd.concat([st.session_state.test_data, pd.DataFrame([{'T_Sec': t_elapsed, 'BPM': bpm, 'G_Sec': sec_now}])], ignore_index=True)
        else:
            if time.time() - st.session_state.last_valid_packet_time > 15:
                if not st.session_state.history.empty and pd.notna(st.session_state.history.iloc[-1]['BPM']):
                    gap_sec = st.session_state.rr_time_accumulated + (time.time() - st.session_state.last_valid_packet_time)
                    new_row = pd.DataFrame([{'Sec': gap_sec, 'BPM': float('nan')}])
                    st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
                st.session_state.last_bpm = None
                
        st.session_state.last_fetch_time = current_time
        st.rerun()

if st.session_state.stream_error:
    st.warning(st.session_state.stream_error)

# --- VISUALIZZAZIONE TIMER TEST CLINICI ---
if st.session_state.active_test and st.session_state.test_start_time:
    elapsed = int(time.time() - st.session_state.test_start_time)
    if st.session_state.active_test == "res":
        cycle_time = elapsed % 10
        phase_text, sec_left = (t["inspira"], 5 - cycle_time) if cycle_time < 5 else (t["espira"], 10 - cycle_time)
        st.markdown(f"<div class='timer-box'>{phase_text} ({sec_left}s)<br><span class='timer-small'>⏱️ TOT: {elapsed}s</span></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<div class='timer-box'>⏱️ TEST: {elapsed}s</div>", unsafe_allow_html=True)

# --- METRICHE VISIVE ---
m1, m2, m3, m4, m5 = st.columns(5)
hist = st.session_state.history

if not hist.empty:
    display_bpm = st.session_state.last_bpm if st.session_state.last_bpm is not None else float('nan')
    
    if st.session_state.rr_history:
        metrics_globali = calcola_metriche_rr(st.session_state.rr_history)
        avg_val = f"{metrics_globali['mean']:.1f}"
        max_val = f"{metrics_globali['max']:.0f}"
        min_val = f"{metrics_globali['min']:.0f}"
        rmssd_val = f"{metrics_globali['rmssd']:.1f} ms"
    else:
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

# --- GRAFICO ---
if not hist.empty:
    if st.session_state.freeze_view and not st.session_state.test_data.empty:
        df_plot = hist[(hist['Sec'] >= st.session_state.test_data['G_Sec'].min()-2) & (hist['Sec'] <= st.session_state.test_data['G_Sec'].max()+2)]
    else:
        max_sec = hist['Sec'].max()
        df_plot = hist[hist['Sec'] >= (max_sec - win)]
    
    valid_plot_bpms = df_plot['BPM'].dropna()
    y_min = float(valid_plot_bpms.min() - 5) if not valid_plot_bpms.empty else 40.0
    y_max = float(valid_plot_bpms.max() + 5) if not valid_plot_bpms.empty else 100.0

    if grafico_veloce:
        st.subheader("⚡ Vital Sign Flow Graph")
        chart_df = df_plot.rename(columns={"Sec": "Secondi", "BPM": "BPM"}).set_index("Secondi")
        st.line_chart(chart_df["BPM"], y_label="BPM", height=300)
    else:
        line = alt.Chart(df_plot).mark_line(color='#ff4b4b', interpolate='monotone', size=3).encode(
            x=alt.X('Sec:Q', title="Secondi", scale=alt.Scale(nice=False)),
            y=alt.Y('BPM:Q', title="BPM", scale=alt.Scale(domain=[y_min, y_max]))
        )
        layers = [line]
        if st.session_state.markers:
            layers.append(alt.Chart(pd.DataFrame({'Sec': st.session_state.markers})).mark_rule(color='#00e5ff', strokeDash=[5,5]).encode(x='Sec:Q'))
        st.altair_chart(alt.layer(*layers).interactive(), use_container_width=True)

# --- LIVE DIAGNOSTICS & RAW PAYLOAD PANEL ---
st.markdown("---")
with st.expander(t["diagnostics_title"]):
    col_d1, col_d2, col_d3 = st.columns(3)
    time_since_packet = (time.time() - st.session_state.last_valid_packet_time) if st.session_state.last_valid_packet_time > 0 else float('inf')
    col_d1.metric(t["packet_latency"], f"{time_since_packet:.1f} s" if time_since_packet < 9999 else t["no_packet"])
    col_d2.metric("Pacchetti Elaborati", f"{st.session_state.packet_counter}")
    col_d3.metric(t["collected_rr"], f"{len(st.session_state.rr_history)}")
    
    st.markdown("##### Raw JSON Payload:")
    if st.session_state.last_raw_payload:
        st.json(st.session_state.last_raw_payload)
    else:
        st.caption(t["no_packet"])

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
    elif res == "error_no_data":
        st.error(f"❌ {t['error_no_data']} ({t['wait']})")
    elif res == "error_short":
        st.warning(f"⚠️ {t['error_short_data']}")
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

if In_Breathing_Tab := (scelta_test == opzioni_test[0]): render_test_ui("res")
elif In_Valsalva_Tab := (scelta_test == opzioni_test[1]): render_test_ui("val")
else: render_test_ui("tilt")
