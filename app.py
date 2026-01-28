import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
import cv2
import numpy as np
from github import Github

st.set_page_config(page_title="Lager-Diagnose", page_icon="📦", layout="wide")

# --- BITTE HIER PRÜFEN ---
# Gib hier zur Sicherheit deinen GitHub-Namen mit an, z.B. "DeinName/mein-lager"
GITHUB_REPO_PATH = "eh-des/mein-lager" 
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- VERBESSERTE SPEICHER-FUNKTION MIT FEHLERMELDUNG ---
def save_to_github(df):
    try:
        if "GITHUB_TOKEN" not in st.secrets:
            st.error("❌ Schlüssel fehlt: 'GITHUB_TOKEN' nicht in Streamlit Secrets gefunden!")
            return False
            
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(GITHUB_REPO_PATH) # Nutzt jetzt den vollen Pfad
        
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        
        try:
            # Versuche vorhandene Datei zu finden
            contents = repo.get_contents(GITHUB_FILENAME)
            repo.update_file(
                path=GITHUB_FILENAME,
                message=f"Lager-Update {datetime.now().strftime('%H:%M:%S')}",
                content=excel_data,
                sha=contents.sha
            )
            return True
        except Exception as file_e:
            # Wenn Datei nicht da, neu anlegen
            st.warning(f"Datei nicht gefunden, erstelle neu... ({file_e})")
            repo.create_file(
                path=GITHUB_FILENAME,
                message="Erster Lagerbestand",
                content=excel_data
            )
            return True
            
    except Exception as e:
        st.error(f"❌ GitHub-Fehler: {e}")
        st.info("Prüfe, ob der Repository-Name und dein Token korrekt sind.")
        return False

def load_data():
    try:
        # Wir versuchen die Datei direkt zu laden
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_repo(GITHUB_REPO_PATH)
        contents = repo.get_contents(GITHUB_FILENAME)
        return pd.read_excel(io.BytesIO(contents.decoded_content))
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

# --- SESSION STATE ---
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- SIDEBAR & EXPORT ---
st.sidebar.title("📦 Lager-Profi")
if st.sidebar.button("🔄 Daten von GitHub neu laden"):
    st.session_state.lager_daten = load_data()
    st.rerun()

df_current = st.session_state.lager_daten
lager_bestand = df_current[df_current["Status"] == "Eingang"]

# Export Button
buf = io.BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as writer:
    lager_bestand.to_excel(writer, index=False)
st.sidebar.download_button("📥 Inventur-Export (Excel)", buf.getvalue(), f"Lager_{datetime.now().strftime('%d-%m')}.xlsx")

st.sidebar.divider()
menu = st.sidebar.radio("Menü:", ["📥 Annahme", "📤 Ausgang", "📊 Bestand"])

# --- SCANNER ---
def scan():
    img = st.camera_input("Kamera")
    if img:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(cv2.imdecode(np.asarray(bytearray(img.read()), dtype=np.uint8), 1))
        return data
    return None

# --- LOGIK ---
if menu == "📥 Annahme":
    st.header("Wareneingang")
    data = scan()
    if data:
        p = data.split(";")
        if len(p) >= 2:
            s_id, s_mat = p[0].strip(), p[1].strip()
            st.success(f"Gelesen: {s_mat}")
            if st.button("Speichern"):
                nz = {"QR_ID": s_id, "Material": s_mat, "Lieferant": p[2] if len(p)>2 else "", "Status": "Eingang", "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"), "Datum_Ausgang": "", "Preis": float(p[3]) if len(p)>3 else 0.0}
                st.session_state.lager_daten = pd.concat([st.session_state.lager_daten, pd.DataFrame([nz])], ignore_index=True)
                if save_to_github(st.session_state.lager_daten):
                    st.success("Dauerhaft auf GitHub gespeichert!")
                    st.balloons()
        else:
            st.error("QR-Format falsch!")

elif menu == "📤 Ausgang":
    st.header("Warenausgang")
    sid = scan()
    if sid:
        clean_id = sid.split(";")[0].strip()
        df = st.session_state.lager_daten
        t = df[(df["QR_ID"] == clean_id) & (df["Status"] == "Eingang")]
        if not t.empty:
            st.warning(f"Material: {df.at[t.index[0], 'Material']}")
            if st.button("Abbuchung Bestätigen"):
                df.at[t.index[0], "Status"] = "Verbraucht"
                df.at[t.index[0], "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                if save_to_github(df):
                    st.success("Abgebucht!")
                    st.rerun()
        else:
            st.error("ID nicht gefunden.")

elif menu == "📊 Bestand":
    st.header("Lagerbestand")
    st.dataframe(lager_bestand, use_container_width=True)
