[🇬🇧 English version available here](README(Eng).md)

# 📊 Monitoraggio HR e HRV per scopi didattici 💓

![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)
![Python Version](https://img.shields.io/badge/python-3.9%2B-blue)

Questa applicazione web consente il monitoraggio in tempo reale della **Frequenza cardiaca (HR)** e della **Variabilità della frequenza cardiaca (HRV)** utilizzando i dati provenienti da sensori **Moofit** tramite l'ecosistema **Pulsoid** e web app customizzata **Streamlit** 

---

## 🚀 Funzionalità principali

- **Streaming in tempo reale**: Connessione diretta con l'API di Pulsoid per dati HR ad alta frequenza
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

1. **Configurazione Pulsoid**:
   - Assicurati che il tuo Moofit sia collegato all'app Pulsoid sul telefono.
   - Ottieni il tuo **Access Token** dal sito [Pulsoid.net](https://pulsoid.net).
2. **Setup della web App**:
   - Inserisci il token nella barra a sinistra e premi Invio
3. **Utilizzo**:
   - Clicca **START** per iniziare la registrazione.
   - Dopo 30 secondi apparirà il valore RMSSD live.
   - Clicca **STOP** per visualizzare il riepilogo finale e scaricare il CSV.

---

## 🔬 Alert

### Validità dei dati
Sia il sensore che la metodica di acquisizione dati non permettono di utilizzare questi valori per scopi clinici o di ricerca; la web app è stat creata per soli scopi didattici!

---

## 🎓 Crediti
**Sviluppato da:** Danilo Bondi

**Data di rilascio:** 16 marzo 2026

**Enti di riferimento:**
* Università degli Studi "G. d'Annunzio" Chieti-Pescara
* Università degli Studi dell'Aquila

![Logo UDA](logo%20UDA.png)
![Logo UnivAq](Logo%20UnivAq.png)

**AI Support:** Progettato con l'ausilio di Gemini (Google AI).
