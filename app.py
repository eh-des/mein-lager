import streamlit as st
import pandas as pd
from datetime import datetime
import io
from github import Github

st.set_page_config(page_title="Lager-Profi", page_icon="📦")

# --- KONFIGURATION (Bitte prüfen!) ---
GITHUB_REPO = "mein-lager"  # Der Name deines Projekts auf GitHub
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- GITHUB SPEICHER-FUNKTION ---
def save_to_github(df):
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        # Holen des Benutzernamens automatisch oder manuell
        repo = g.get_user().get_repo(GITHUB_REPO)
        
        # Excel-Datei im Speicher erstellen
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        
        # Die Datei auf GitHub finden, um sie zu überschreiben
        contents = repo.get_contents(GITHUB_FILENAME)
        repo.update_file(
            path=GITHUB_FILENAME,
            message=f"Lager-Update: {datetime.now().strftime('%d.%m.%Y %H:%M')}",
            content=excel_data,
            sha=contents.sha
        )
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern auf GitHub: {e}")
        return False

# --- DATEN LADEN ---
@st.cache_data(ttl=60) # Lädt alle 60 Sek. neu, falls extern geändert
def load_data():
    try:
        return pd.read_excel(GITHUB_FILENAME)
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

# Initialisierung
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- NAVIGATION ---
st.title("📦 Lager-System (Auto-Save)")
menu = st.sidebar.radio("Menü", ["Bestand & Scanner", "Wareneingang"])

# --- SEITE 1: BESTAND & SCANNER ---
if menu == "Bestand & Scanner":
    df = st.session_state.lager_daten
    lager_aktuell = df[df["Status"] == "Eingang"]

    st.subheader("Aktueller Lagerbestand")
    st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)

    st.divider()
    st.subheader("QR-Scanner (Verbrauch)")
    scan_input = st.text_input("ID einscannen:", key="scanner_input").strip()

    if scan_input:
        idx_list = df.index[df["QR_ID"].astype(str) == scan_input].tolist()
        if idx_list:
            idx = idx_list[0]
            if df.at[idx, "Status"] == "Eingang":
                st.success(f"Gefunden: {df.at[idx, 'Material']}")
                if st.button("Verbrauch bestätigen & Speichern"):
                    # Änderung im lokalen Speicher
                    df.at[idx, "Status"] = "Verbraucht"
                    df.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                    
                    # JETZT: Direkt zu GitHub hochladen
                    with st.spinner('Speichere auf GitHub...'):
                        if save_to_github(df):
                            st.success("Erfolgreich gespeichert!")
                            st.rerun()
            else:
                st.warning("Dieses Gebinde ist bereits verbraucht.")
        else:
            st.error("ID nicht gefunden.")

# --- SEITE 2: WARENEINGANG ---
else:
    st.subheader("Neues Material aufnehmen")
    with st.form("input_form"):
        f_id = st.text_input("QR-ID")
        f_name = st.text_input("Material Name")
        f_lief = st.text_input("Lieferant")
        f_preis = st.number_input("Preis", min_value=0.0, format="%.2f")
        
        if st.form_submit_button("In Bestand aufnehmen & Speichern"):
            if f_id and f_name:
                neue_daten = {
                    "QR_ID": str(f_id), "Material": str(f_name), "Lieferant": str(f_lief),
                    "Status": "Eingang", "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"),
                    "Datum_Ausgang": "", "Preis": float(f_preis)
                }
                df = st.session_state.lager_daten
                if str(f_id) in df["QR_ID"].astype(str).values:
                    st.error("ID existiert bereits!")
                else:
                    df = pd.concat([df, pd.DataFrame([neue_daten])], ignore_index=True)
                    with st.spinner('Speichere auf GitHub...'):
                        if save_to_github(df):
                            st.session_state.lager_daten = df
                            st.success(f"{f_name} dauerhaft gespeichert!")
            else:
                st.error("Bitte ID und Name ausfüllen.")

# --- INFO BEREICH ---
st.sidebar.info("Daten werden automatisch mit der Excel auf GitHub synchronisiert.")
