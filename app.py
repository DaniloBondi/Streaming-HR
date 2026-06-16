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
        "stream_mode": "Modalità Streaming"
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
        "stream_mode": "Streaming Mode"
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
    'markers': [], 'results': {}, 'last_ts': "",
    'use_streaming': False, 'stream_error': None,
    'last_fetch_time': 0, 'debug_mode': False
}.items():
    if key not in st.session_state: st.session_state[key] = default

# --- FUNZIONI CALLBACK (Rendono i tasti istantanei) ---
def cb_start_rec():
    # impedisci start se api mancante (nel caso di streaming, device_ip/token)
    if st.session_state.use_streaming:
        if not device_ip or not stream_token:
            st.warning("Device IP o Streaming Token mancanti.")
            return
    else:
        # Nel caso non-streaming, non richiedere token (sarà None)
        if not api_url_effective:
            st.warning("API URL mancante.")
            return
    st.session_state.running, st.session_state.freeze_view = True, False

def cb_stop_rec():
    st.session_state.running, st.session_state.active_test = False, None

def cb_reset():
    st.session_state.history = pd.DataFrame(columns=['Sec', 'BPM'])
    st.session_state.markers, st.session_state.results = [], {}
    st.session_state.freeze_view, st.session_state.running, st.session_state.active_test = False, False, None

def cb_start_test(name):
    st.session_state.active_test, st.session_state.freeze_view = name, False
    st.session_state.test_data = pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec'])
    st.session_state.markers.append(len(st.session_state.history))

def cb_stop_test(name):
    if len(st.session_state.test_data) < 30:
        st.session_state.results[name] = "error"
    else:
        d = st.session_state.test_data
        st.session_state.freeze_view = True
        if name in ["res", "val"]:
            st.session_state.results[name] = {
                'max': d['BPM'].max(), 'min': d['BPM'].min(), 'diff': d['BPM'].max() - d['BPM'].min(),
                'ratio': d['BPM'].max() / d['BPM'].min() if d['BPM'].min() > 0 else 0
            }
        else:
            v15 = d.iloc[15]['BPM'] if len(d)>15 else d['BPM'].iloc[-1]
            v30 = d.iloc[30]['BPM'] if len(d)>30 else d['BPM'].iloc[-1]
            st.session_state.results[name] = {'v15': v15, 'v30': v30, 'ratio': v30/v15}
    st.session_state.active_test = None

# Helper: recupera token da st.secrets o da env var
def get_token():
    token = None
    try:
        token = st.secrets.get("API_TOKEN") if hasattr(st, "secrets") else None
    except Exception:
        token = None
    if not token:
        token = os.getenv("API_TOKEN")
    return token

# --- STREAMING DATA RETRIEVAL WITH IMPROVED ERROR HANDLING ---
def fetch_vitals_data_streaming(device_ip, device_port, stream_token, timeout=1.5):
    """Fetch vital signs from the mobile device endpoint using streaming procedure"""
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

def update_rolling_dataframe_streaming(payload):
    """Update the rolling BPM dataframe with new data from streaming"""
    bpm = payload.get("bpm", 0)
    now_str = datetime.now().strftime("%H:%M:%S")
    
    if bpm > 0:
        sec_now = len(st.session_state.history)
        new_row = pd.DataFrame([{'Sec': sec_now, 'BPM': bpm}])
        st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True).tail(100)
    
    # Sync rolling list from remote cache on startup
    if len(st.session_state.history) <= 1 and len(payload.get("bpm_history", [])) > 0:
        remote_pts = []
        for idx, pt in enumerate(payload["bpm_history"]):
            remote_pts.append({"Sec": idx, "BPM": pt.get("BPM", pt.get("bpm", 0))})
        st.session_state.history = pd.DataFrame(remote_pts)

# API CALL (Original method for compatibility)
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
                # Prova prima con 'heart_rate', poi fallback a 'bpm' per compatibilità
                bpm_value = data.get('heart_rate') or data.get('bpm')
                if st.session_state.debug_mode:
                    logger.info(f"[API] Extracted BPM: {bpm_value}")
                return bpm_value
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
    """
    Fetch BPM from API URL without requiring token.
    Token is optional and only used if auth_method is not 'Auto' or if needed.
    """
    if not api_url:
        if st.session_state.debug_mode:
            logger.warning("[get_bpm] No API URL provided")
        return None
    
    url = api_url.strip()
    
    # Se non c'è token e auth_method non è 'Auto', ritorna None
    if not token and auth_method != "Auto":
        if st.session_state.debug_mode:
            logger.warning("[get_bpm] No token and auth_method is not Auto")
        return None
    
    # Se token è presente, usalo
    if token:
        if auth_method == "Auto":
            # prova Bearer -> Token -> X-API-Key
            headers = {"Authorization": f"Bearer {token}"}
            v = _try_request(url, headers)
            if v is not None: return v
            headers = {"Authorization": f"Token {token}"}
            v = _try_request(url, headers)
            if v is not None: return v
            headers = {"X-API-Key": token}
            v = _try_request(url, headers)
            if v is not None: return v
            # ultima prova custom header default
            headers = {custom_header_name: token}
            return _try_request(url, headers)
        else:
            if auth_method == "Bearer":
                headers = {"Authorization": f"Bearer {token}"}
            elif auth_method == "Token":
                headers = {"Authorization": f"Token {token}"}
            elif auth_method == "X-API-Key":
                headers = {"X-API-Key": token}
            else:
                headers = {custom_header_name: token}
            return _try_request(url, headers)
    else:
        # No token: request senza header di autenticazione
        headers = {}
        if st.session_state.debug_mode:
            logger.info(f"[get_bpm] Fetching from {url} with no auth headers")
        return _try_request(url, headers)

# --- SIDEBAR ---
with st.sidebar:
    lang = st.radio("Lang", ["🇮🇹 ITA", "🇬🇧 ENG"], horizontal=True, label_visibility="collapsed")
    t = LANGS[lang]
    st.markdown("---")
    st.markdown(f"### 🕐 {datetime.now(pytz.timezone('Europe/Rome')).strftime('%H:%M:%S')}")

    # --- DEBUG MODE ---
    st.session_state.debug_mode = st.checkbox("🐛 Debug Mode", value=False)

    # --- STREAMING MODE TOGGLE ---
    st.session_state.use_streaming = st.checkbox(t["stream_mode"], value=False)
    
    if st.session_state.use_streaming:
        st.markdown("### 📱 Streaming Settings")
        device_ip = st.text_input("Mobile IP Address", value="10.215.78.116")
        device_port = st.number_input("Server Port", value=8080, step=1)
        stream_token = st.text_input("Streamer Security Token", type="password", value="VITAL-66A51AC5")
        poll_interval = st.slider("Sampling Interval (sec)", 0.2, 5.0, 1.0, 0.1)
        token = None
        api_url = None
        api_url_effective = None
        custom_header_name = ""
    else:
        st.markdown("### 🔧 API Settings")
        # L'utente può inserire un URL personalizzato, altrimenti usa il default
        api_url_custom = st.text_input(t["api_label"], value="").strip()
        api_url_effective = api_url_custom if api_url_custom else DEFAULT_API_URL
        
        # Mostra URL attivo
        st.caption(f"📍 URL attivo: `{api_url_effective}`")
        
        # Token opzionale
        token = st.text_input(t["token_label"], type="password", value="")
        token = token.strip() if token else None
        
        # Auth method solo se token fornito
        if token:
            auth_method = st.selectbox(t["auth_label"], ["Auto", "Bearer", "Token", "X-API-Key", "Custom header"], index=0)
            custom_header_name = ""
            if auth_method == "Custom header":
                custom_header_name = st.text_input(t["custom_header_label"], value="X-My-App-Token")
        else:
            auth_method = "Auto"
            custom_header_name = ""
        
        api_url = api_url_custom  # Usa custom solo se fornito esplicitamente
        device_ip = None
        device_port = None
        stream_token = None
        poll_interval = 1.0
    
    c1, c2 = st.columns(2)
    if st.session_state.use_streaming:
        c1.button(t["start_rec"], type="primary", disabled=not device_ip or not stream_token, on_click=cb_start_rec)
    else:
        c1.button(t["start_rec"], type="primary", disabled=not api_url_effective, on_click=cb_start_rec)
    c2.button(t["stop_rec"], on_click=cb_stop_rec)

    win = st.slider(t["win_label"], 10, 300, 60)
    st.button("🗑 Reset", use_container_width=True, on_click=cb_reset)

    st.markdown("---")
    st.caption(t["credits"])
    lc1, lc2 = st.columns(2)
    try:
        if os.path.exists("logo UDA.png"): lc1.image("logo UDA.png", width=80)
        if os.path.exists("Logo UnivAq.png"): lc2.image("Logo UnivAq.png", width=80)
    except: pass
    st.caption(t["creator"])
    with st.expander(t["privacy_title"]): st.markdown(f"<small>{t['privacy_text']}</small>", unsafe_allow_html=True)

# --- DASHBOARD ---
st.title(t["title"])

# --- CONTINUOUS DATA POLLING ---
# Polling loop che raccoglie dati continuativamente quando running=True
if st.session_state.running:
    current_time = time.time()
    time_since_last_fetch = current_time - st.session_state.last_fetch_time
    
    # Fetch solo se è passato abbastanza tempo (basato su poll_interval)
    if time_since_last_fetch >= poll_interval:
        if st.session_state.use_streaming:
            payload, error = fetch_vitals_data_streaming(device_ip, device_port, stream_token)
            if error:
                st.session_state.stream_error = error
                bpm = None
            else:
                st.session_state.stream_error = None
                bpm = payload.get("bpm", 0) if payload else None
                if payload and bpm and bpm > 0:
                    update_rolling_dataframe_streaming(payload)
        else:
            # Non-streaming: usa api_url_effective (default o custom)
            bpm = get_bpm(api_url_effective, auth_method, custom_header_name, token)
            
            if st.session_state.debug_mode:
                logger.info(f"[POLL] Fetched BPM: {bpm}")
            
            # Aggiungi al history se abbiamo un BPM valido
            if bpm:
                sec_now = len(st.session_state.history)
                new_row = pd.DataFrame([{'Sec': sec_now, 'BPM': bpm}])
                st.session_state.history = pd.concat([st.session_state.history, new_row], ignore_index=True)
                
                if st.session_state.active_test:
                    st.session_state.test_data = pd.concat([st.session_state.test_data, pd.DataFrame([{'T_Sec': len(st.session_state.test_data), 'BPM': bpm, 'G_Sec': sec_now}])], ignore_index=True)
        
        st.session_state.last_fetch_time = current_time
        # Force refresh della pagina
        st.rerun()
else:
    bpm = None

# Display streaming error if present
if st.session_state.stream_error:
    st.warning(st.session_state.stream_error)

m1, m2, m3, m4 = st.columns(4)
hist = st.session_state.history
if not hist.empty:
    m1.metric(t["fc_live"], f"{bpm if bpm else hist['BPM'].iloc[-1]} BPM")
    m2.metric(t["fc_avg"], f"{hist['BPM'].mean():.1f}")
    m3.metric(t["fc_max"], f"{hist['BPM'].max():.0f}")
    m4.metric(t["fc_min"], f"{hist['BPM'].min():.0f}")
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

if not hist.empty:
    df_plot = hist[(hist['Sec'] >= st.session_state.test_data['G_Sec'].min()-2) & (hist['Sec'] <= st.session_state.test_data['G_Sec'].max()+2)] if st.session_state.freeze_view else hist.tail(win)
    line = alt.Chart(df_plot).mark_line(color='#ff4b4b', interpolate='monotone', size=3).encode(
        x=alt.X('Sec:Q', title="Secondi", scale=alt.Scale(nice=False)),
        y=alt.Y('BPM:Q', title="BPM", scale=alt.Scale(domain=[hist['BPM'].min()-5, hist['BPM'].max()+5]))
    )
    layers = [line]
    if st.session_state.markers:
        layers.append(alt.Chart(pd.DataFrame({'Sec': st.session_state.markers})).mark_rule(color='#00e5ff', strokeDash=[5,5]).encode(x='Sec:Q'))
    st.altair_chart(alt.layer(*layers).interactive(), use_container_width=True)

# --- MENU TEST CLINICI (Sostituisce le Tabs per non perdere la selezione) ---
st.markdown("---")
st.subheader(t["clinical"])

# Stile navigazione Orizzontale al posto delle Tabs
opzioni_test = [f"🌬️ {t['respiro']}", f"😤 {t['valsalva']}", f"🧍 {t['tilt']}"]
scelta_test = st.radio("Seleziona Test", opzioni_test, horizontal=True, label_visibility="collapsed")

def render_test_ui(name):
    cs, ce = st.columns(2)
    # Pulsanti fulminei con callback
    cs.button(t["start_test"], key=f"s_{name}", disabled=not st.session_state.running, on_click=cb_start_test, args=(name,))
    ce.button(t["stop_test"], key=f"e_{name}", disabled=st.session_state.active_test != name, on_click=cb_stop_test, args=(name,))

    res = st.session_state.results.get(name)
    if res == "error": 
        st.warning(t["wait"])
    elif isinstance(res, dict):
        st.success("Test OK")
        if 'max' in res:
            rc = st.columns(4)
            rc[0].metric(t["fc_max"], f"{res['max']:.0f}")
            rc[1].metric(t["fc_min"], f"{res['min']:.0f}")
            rc[2].metric(t["fc_diff"], f"{res['diff']:.0f}")
            rc[3].metric("Ratio", f"{res['ratio']:.2f}")
        else:
            rc = st.columns(3)
            rc[0].metric("15s", f"{res['v15']:.0f}")
            rc[1].metric("30s", f"{res['v30']:.0f}")
            rc[2].metric("30:15", f"{res['ratio']:.2f}")

# Renderizza solo l'UI del test selezionato dal radio button
if scelta_test == opzioni_test[0]: render_test_ui("res")
elif scelta_test == opzioni_test[1]: render_test_ui("val")
else: render_test_ui("tilt")
