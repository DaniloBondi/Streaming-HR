import streamlit as st
import requests
import pandas as pd
import numpy as np
from datetime import datetime
from streamlit_autorefresh import st_autorefresh
import pytz
import altair as alt
import os

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
        "credits": "**Smartphone app:** Pulsoid | **Repository:** GitHub | **Web app:** Streamlit | **AI:** Gemini",
        "creator": "**Creator:** Danilo Bondi",
        "privacy_title": "🛡️ Informativa Privacy e Dati",
        "privacy_text": "Nessun salvataggio: i dati restano solo nella RAM temporanea della sessione.<br>Cancellazione: alla chiusura del browser, i dati vengono eliminati.<br>Sicurezza: il token Pulsoid inserito non viene mai archiviato.",
        "token_label": "🔑 Token Pulsoid", "win_label": "Finestra temporale (sec)"
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
        "credits": "**Smartphone app:** Pulsoid | **Repository:** GitHub | **Web app:** Streamlit | **AI:** Gemini",
        "creator": "**Creator:** Danilo Bondi",
        "privacy_title": "🛡️ Privacy Policy",
        "privacy_text": "No storage: data remains only in temporary RAM.<br>Deletion: browser closing deletes data.<br>Security: token is never stored.",
        "token_label": "🔑 Pulsoid Token", "win_label": "Time window (sec)"
    }
}

st_autorefresh(interval=500, key="hr_refresher")

# --- STATO DELLA SESSIONE ---
for key, default in {
    'history': pd.DataFrame(columns=['Sec', 'BPM']), 'running': False,
    'active_test': None, 'freeze_view': False,
    'test_data': pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec']),
    'markers': [], 'results': {}, 'last_ts': ""
}.items():
    if key not in st.session_state: st.session_state[key] = default

def get_bpm(token):
    if not token: return None
    try:
        r = requests.get("https://dev.pulsoid.net/api/v1/data/heart_rate/latest", headers={"Authorization": f"Bearer {token}"}, timeout=1)
        return r.json().get('data', {}).get('heart_rate') if r.status_code == 200 else None
    except: return None

# --- SIDEBAR ---
with st.sidebar:
    lang = st.radio("Lang", ["🇮🇹 ITA", "🇬🇧 ENG"], horizontal=True, label_visibility="collapsed")
    t = LANGS[lang]
    st.markdown("---")
    st.markdown(f"### 🕐 {datetime.now(pytz.timezone('Europe/Rome')).strftime('%H:%M:%S')}")

    token = st.text_input(t["token_label"], type="password")
    
    c1, c2 = st.columns(2)
    if c1.button(t["start_rec"], type="primary", disabled=not token):
        st.session_state.running, st.session_state.freeze_view = True, False
    if c2.button(t["stop_rec"]):
        st.session_state.running, st.session_state.active_test = False, None

    win = st.slider(t["win_label"], 10, 300, 60)
    
    if st.button("🗑 Reset", use_container_width=True):
        st.session_state.history = pd.DataFrame(columns=['Sec', 'BPM'])
        st.session_state.markers, st.session_state.results = [], {}
        st.session_state.freeze_view, st.session_state.running, st.session_state.active_test = False, False, None
        st.rerun()

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
bpm = get_bpm(token)
curr_ts = datetime.now().strftime("%H:%M:%S")

# Registrazione Dati
if bpm and st.session_state.running:
    if st.session_state.last_ts != curr_ts:
        sec_now = len(st.session_state.history)
        st.session_state.history = pd.concat([st.session_state.history, pd.DataFrame([{'Sec': sec_now, 'BPM': bpm}])], ignore_index=True)
        st.session_state.last_ts = curr_ts
        if st.session_state.active_test:
            st.session_state.test_data = pd.concat([st.session_state.test_data, pd.DataFrame([{'T_Sec': len(st.session_state.test_data), 'BPM': bpm, 'G_Sec': sec_now}])], ignore_index=True)

# UI Metriche
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

# Cronometro Dinamico
if st.session_state.active_test:
    elapsed = len(st.session_state.test_data)
    if st.session_state.active_test == "res":
        # Logica 5s Inspira / 5s Espira
        cycle_time = elapsed % 10
        if cycle_time < 5:
            phase_text = t["inspira"]
            sec_left = 5 - cycle_time
        else:
            phase_text = t["espira"]
            sec_left = 10 - cycle_time
        st.markdown(f"<div class='timer-box'>{phase_text} ({sec_left}s)<br><span class='timer-small'>⏱️ TOT: {elapsed}s</span></div>", unsafe_allow_html=True)
    else:
        # Cronometro normale per gli altri test
        st.markdown(f"<div class='timer-box'>⏱️ TEST: {elapsed}s</div>", unsafe_allow_html=True)

# Grafico (Linea continua senza sfumatura)
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

# --- TEST CLINICI ---
st.markdown("---")
st.subheader(t["clinical"])
tabs = st.tabs([f"🌬️ {t['respiro']}", f"😤 {t['valsalva']}", f"🧍 {t['tilt']}"])

def handle_test(name):
    cs, ce = st.columns(2)
    if cs.button(t["start_test"], key=f"s_{name}", disabled=not st.session_state.running):
        st.session_state.active_test, st.session_state.freeze_view = name, False
        st.session_state.test_data = pd.DataFrame(columns=['T_Sec', 'BPM', 'G_Sec'])
        st.session_state.markers.append(len(st.session_state.history))
        st.rerun()
    
    if ce.button(t["stop_test"], key=f"e_{name}", disabled=st.session_state.active_test != name):
        if len(st.session_state.test_data) < 30:
            st.session_state.results[name] = "error"
        else:
            d = st.session_state.test_data
            st.session_state.freeze_view = True
            
            # Calcoli unificati per respiro e valsalva/cough/handgrip (aggiunto 'diff')
            if name in ["res", "val"]:
                st.session_state.results[name] = {
                    'max': d['BPM'].max(), 
                    'min': d['BPM'].min(), 
                    'diff': d['BPM'].max() - d['BPM'].min(),
                    'ratio': d['BPM'].max() / d['BPM'].min() if d['BPM'].min() > 0 else 0
                }
            else:
                v15 = d.iloc[15]['BPM'] if len(d)>15 else d['BPM'].iloc[-1]
                v30 = d.iloc[30]['BPM'] if len(d)>30 else d['BPM'].iloc[-1]
                st.session_state.results[name] = {'v15': v15, 'v30': v30, 'ratio': v30/v15}
        
        st.session_state.active_test = None
        st.rerun()

    res = st.session_state.results.get(name)
    if res == "error": st.warning(t["wait"])
    elif isinstance(res, dict):
        st.success("Test OK")
        # Visualizzazione risultati
        if 'max' in res:
            rc = st.columns(4) # Ora sono 4 colonne per far spazio alla 'diff'
            rc[0].metric(t["fc_max"], f"{res['max']:.0f}")
            rc[1].metric(t["fc_min"], f"{res['min']:.0f}")
            rc[2].metric(t["fc_diff"], f"{res['diff']:.0f}") # FCmax - FCmin aggiunto anche in Valsalva
            rc[3].metric("Ratio", f"{res['ratio']:.2f}")
        else:
            rc = st.columns(3)
            rc[0].metric("15s", f"{res['v15']:.0f}")
            rc[1].metric("30s", f"{res['v30']:.0f}")
            rc[2].metric("30:15", f"{res['ratio']:.2f}")

with tabs[0]: handle_test("res")
with tabs[1]: handle_test("val")
with tabs[2]: handle_test("tilt")
