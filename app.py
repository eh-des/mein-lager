import streamlit as st
import pandas as pd
from datetime import datetime
import io
import cv2
import numpy as np
from github import Github

# --- KONFIGURATION ---
st.set_page_config(page_title="Lager-Diagnose", page_icon="📦", layout="wide")

GITHUB_REPO_PATH = "eh-des/mein-lager" 
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- HILFSFUNKTIONEN ---

def save_to_github(df):
    """Speichert den DataFrame als Excel-Datei auf GitHub (Update oder Neuerstellung)."""
    try:
        if "GITHUB_TOKEN" not in st.secrets:
            st.error("❌ GITHUB_TOKEN nicht in Streamlit Secrets gefunden!")
            return False
            
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(GITHUB_REPO_PATH)
        
        # DataFrame in Excel umwandeln
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        
        try:
            # Versuch: Vorhandene Datei aktualisieren
            contents = repo.get_contents(GITHUB_FILENAME)
            repo.update_file(
                path=GITHUB_FILENAME,
                message=f"Lager-Update {datetime.now().strftime('%H:%M:%S')}",
                content=excel_data,
                sha=contents.sha
            )
            return True
        except Exception:
            # Falls Datei gelöscht wurde: Neu erstellen
            repo.create_file(
                path=GITHUB_FILENAME,
                message="Lagerbestand initialisiert",
                content=excel_data
            )
            return True
    except Exception as e:
        st.error(f"❌ GitHub-Fehler: {e}")
        return False

def load_data():
    """Lädt die Excel-Daten von GitHub oder gibt ein leeres Template zurück."""
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(GITHUB_REPO_PATH)
        contents = repo.get_contents(GITHUB_FILENAME)
        return pd.read_excel(io.BytesIO(contents.decoded_content))
    except Exception:
        # Falls Datei nicht existiert oder Fehler auftritt
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

def scan():
    """QR-Code Scanner über die Kamera."""
    img = st.camera_input("Kamera")
    if img:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(cv2.imdecode(np.asarray(bytearray(img.read()), dtype=np.uint8), 1))
        return data
    return None

# --- INITIALISIERUNG ---
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

df_all = st.session_state.lager_daten
# Filter für die App-Ansicht: Nur was noch im Bestand ("Eingang") ist
df_ist = df_all[df_all["Status"] == "Eingang"]

# --- SIDEBAR ---
st.sidebar.title("📦 Lager-Profi")

if st.sidebar.button("🔄 Daten neu laden"):
    st.session_state.lager_daten = load_data()
    st.rerun()

# Export: Komplette Historie (Eingang & Ausgang) für Excel
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as writer:
    df_all.to_excel(writer, index=False)
st.sidebar.download_button("📥 Inventur-Export (Alle Daten)", buf.getvalue(), f"Lager_Logbuch_{datetime.now().strftime('%d-%m')}.xlsx")

st.sidebar.divider()

# --- NEU: LISTE LÖSCHEN BUTTON ---
st.sidebar.subheader("Gefahrenzone")
if st.sidebar.button("🗑️ Gesamte Liste löschen"):
    # Erstellt einen leeren DataFrame mit den gleichen Spalten
    empty_df = pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])
    if save_to_github(empty_df):
        st.session_state.lager_daten = empty_df
        st.sidebar.success("Liste auf GitHub geleert!")
        st.rerun()

st.sidebar.divider()
menu = st.sidebar.radio("Menü:", ["📥 Annahme", "📤 Ausgang", "📊 Bestand"])

# --- HAUPTBEREICH ---

if menu == "📥 Annahme":
    st.header("Wareneingang")
    data = scan()
    if data:
        p = data.split(";")
        if len(p) >= 2:
            s_id, s_mat = p[0].strip(), p[1].strip()
            
            # DOPPELTEN-CHECK: Ist diese ID schon mit Status "Eingang" da?
            ist_vorhanden = not df_all[(df_all["QR_ID"] == s_id) & (df_all["Status"] == "Eingang")].empty
            
            if ist_vorhanden:
                st.error(f"❌ Fehler: '{s_mat}' (ID: {s_id}) ist bereits im Bestand!")
            else:
                st.success(f"Gelesen: {s_mat}")
                if st.button("Speichern"):
                    nz = {
                        "QR_ID": s_id, 
                        "Material": s_mat, 
                        "Lieferant": p[2] if len(p)>2 else "", 
                        "Status": "Eingang", 
                        "Datum_Eingang": datetime.now().strftime("%d.%m.%Y %H:%M:%S"), 
                        "Datum_Ausgang": "", 
                        "Preis": float(p[3]) if len(p)>3 else 0.0
                    }
                    st.session_state.lager_daten = pd.concat([st.session_state.lager_daten, pd.DataFrame([nz])], ignore_index=True)
                    if save_to_github(st.session_state.lager_daten):
                        st.success("Erfolgreich gespeichert!")
                        st.balloons()
                        st.rerun()
        else:
            st.error("QR-Format nicht unterstützt!")

elif menu == "📤 Ausgang":
    st.header("Warenausgang")
    sid = scan()
    if sid:
        clean_id = sid.split(";")[0].strip()
        df = st.session_state.lager_daten
        # Suchen nach dem aktiven Bestand
        t = df[(df["QR_ID"] == clean_id) & (df["Status"] == "Eingang")]
        
        if not t.empty:
            st.warning(f"Material: {df.at[t.index[0], 'Material']}")
            if st.button("Abbuchung Bestätigen"):
                # Status ändern für die Historie
                df.at[t.index[0], "Status"] = "Ausgang"
                df.at[t.index[0], "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y %H:%M:%S")
                if save_to_github(df):
                    st.success("Abgebucht!")
                    st.rerun()
        else:
            st.error("ID nicht gefunden oder bereits abgebucht.")

elif menu == "📊 Bestand":
    st.header("Aktueller Lagerbestand")
    # Zeigt nur die Artikel, die aktuell verfügbar sind
    st.dataframe(df_ist, use_container_width=True)
    
    st.divider()
    st.caption("Hinweis: Im Excel-Export (Sidebar) sind auch alle vergangenen Ausgänge sichtbar.")
