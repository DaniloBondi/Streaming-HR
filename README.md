# 📊 Monitoraggio HR e HRV per scopi didattici 💓

![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)

Questa applicazione web consente il monitoraggio in tempo reale della **Frequenza cardiaca (HR)** e della **Variabilità della frequenza cardiaca (HRV)** utilizzando i dati provenienti da sensori *[...]

---

## 🚀 Funzionalità principali

- **Streaming in tempo reale**: Connessione diretta con l'API del provider per dati HR ad alta frequenza
- **Analisi HRV esemplificativa**: 
  - Calcolo della metrica **RMSSD** (Root Mean Square of Successive Differences).
  - Finestra mobile di **30 secondi** per il monitoraggio live.
  - Report globale (Media BPM e RMSSD totale) al termine della sessione.
- **Report della sessione (Media BPM e RMSSD totale) allo STOP**
- **Grafica Interattiva**: Visualizzazione dinamica con linea di tendenza tramite libreria *Altair*
- **Esportazione Dati**: Download immediato della sessione in formato `.csv` per analisi successive
- **Scala Temporale Relativa**: Il grafico mostra il tempo trascorso dall'inizio della registrazione

---

## 📸 Schermata di Esempio

Di seguito viene mostrata una schermata di esempio dell'interfaccia dell'app durante una registrazione attiva, dopo la fase di attesa iniziale di 30 secondi per visualizzare i dati di HRV.

![Schermata di esempio dell'app Moofit HRV Monitor](screenshot_Streamlit.png)

---

## 🛠️ Requisiti Tecnici

L'app è sviluppata in **Python** e richiede le seguenti librerie (incluse in `requirements.txt`):
* `streamlit`: Framework per l'interfaccia web
* `pandas` & `numpy`: Elaborazione dati e calcoli statistici
* `altair`: Visualizzazione dati
* `streamlit-autorefresh`: Gestione del refresh dinamico
* `pytz`: Gestione dei fusi orari

---

## 📖 Come iniziare

1. **Configurazione API / Token**:
   - Assicurati che il tuo sensore sia collegato correttamente tramite Bluetooth all'app smartphone che usi per acquisire i dati
   - Ottieni il tuo **Access Token** dall'app o dal servizio che fornisce i dati
2. **Setup della web App**:
   - Inserisci il token nella barra a sinistra e premi Invio
3. **Utilizzo**:
   - Clicca **START** per iniziare la registrazione.
   - Dopo 30 secondi apparirà il valore RMSSD live.
   - Clicca **STOP** per visualizzare il riepilogo finale e scaricare il CSV.

---

## 🔐 Impostare il token API (provider)

Questa app legge il token in questo ordine di priorità:

1. Streamlit Secrets: `st.secrets['API_TOKEN']` (es. su Streamlit Cloud o file `.streamlit/secrets.toml`)
2. Variabile d'ambiente `API_TOKEN` per esecuzione locale
3. Campo di input nella sidebar (per override temporaneo della sessione)

Esempio: creare `.streamlit/secrets.toml` con questo contenuto (NON committare token reali):

````toml
API_TOKEN = "metti-il-tuo-token-qui"
````

Streamlit Cloud:

- Vai al tuo deploy su Streamlit Cloud → Settings → Secrets.
- Aggiungi una chiave `API_TOKEN` con il valore del token.

Locale:

- Linux/macOS: `export API_TOKEN="il_tuo_token"`
- Windows (PowerShell): `$env:API_TOKEN = "il_tuo_token"`

Copiare il token dall'app smartphone:

- Apri l'app sullo smartphone, copia il token (usa l'opzione "Copy" o condividi tramite canale sicuro).
- Puoi trasferirlo tramite copia-incolla, QR code (se supportato dall'app), o inviandolo a te stesso via email sicura.
- Evita di condividere il token in canali non sicuri o pubblici.

Debug:

- Per abilitare informazioni di debug leggere le chiamate API impostare la variabile d'ambiente `DEBUG=true` (mostrerà solo informazioni diagnostiche nell'interfaccia, non il valore del token).

---

## 🔬 Alert

### Validità dei dati

Sia il sensore che la metodica di acquisizione dati non permettono di utilizzare questi valori per scopi clinici o di ricerca; la web app è stat creata per soli scopi didattici!

---

## Sicurezza!!!

**Chiavi API:** i file secrets.toml o i file .env che contengono le chiavi API rimangono privati

**Data leakage:** Eventuali database locali non finiscono online

**Data sharing:** I dati di sessione non vengono resi disponibili ad eventuali altri utenti connessi contemporaneamente

**RAM:** I dati restano nella RAM solo finché l'utente tiene aperta la pagina, dopodichè i dati spariscono per sempre dal server di Streamlit

**Informativa:** è presente nella sidebar laterale

---

## 🎓 Credits
**Sviluppato da:** Danilo Bondi

**Data di rilascio:** 16 marzo 2026

**Enti di riferimento:**
* Università degli Studi "G. d'Annunzio" Chieti-Pescara
* Università degli Studi dell'Aquila

![Logo UDA](logo%20UDA.png)
![Logo UnivAq](Logo%20UnivAq.png)

**AI Support:** Progettato con l'ausilio di Gemini (Google AI).
