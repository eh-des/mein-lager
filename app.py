import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
import cv2
import numpy as np
from PIL import Image
from github import Github

st.set_page_config(page_title="Lager-System", page_icon="📦")

# --- KONFIGURATION ---
GITHUB_REPO = "mein-lager"
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- FUNKTIONEN (Speichern & Laden) ---
def save_to_github(df):
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_user().get_repo(GITHUB_REPO)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        excel_data = output.getvalue()
        contents = repo.get_contents(GITHUB_FILENAME)
        repo.update_file(path=GITHUB_FILENAME, message="Lager-Update", content=excel_data, sha=contents.sha)
        return True
    except Exception as e:
        st.error(f"Fehler beim Speichern: {e}")
        return False

def load_data():
    try:
        return pd.read_excel(GITHUB_FILENAME)
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

# Initialisierung
if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- NAVIGATION ---
menu = st.sidebar.radio("Menü", ["Bestand & Scanner", "Wareneingang", "QR-Code erzeugen"])

# --- SEITE 1: BESTAND & SCANNER ---
if menu == "Bestand & Scanner":
    st.title("📦 Lagerbestand")
    df = st.session_state.lager_daten
    lager_aktuell = df[df["Status"] == "Eingang"]
    st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis"]], use_container_width=True)
    
    st.divider()
    st.subheader("Scanner")
    
    # NEU: Kamera-Scanner Funktion
    img_file = st.camera_input("📷 Code scannen")
    
    scan_id = ""
    if img_file:
        # Bild verarbeiten und QR-Code suchen
        file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        opencv_image = cv2.imdecode(file_bytes, 1)
        detector = cv2.QRCodeDetector()
        data, points, _ = detector.detectAndDecode(opencv_image)
        if data:
            scan_id = data
            st.success(f"Code erkannt: {scan_id}")
        else:
            st.warning("Kein QR-Code im Bild gefunden. Bitte näher ran oder besser beleuchten.")

    # Manuelle Eingabe (wird automatisch gefüllt, wenn Kamera scannt)
    id_eingabe = st.text_input("Gescannte ID:", value=scan_id).strip()
    
    if id_eingabe:
        idx_list = df.index[df["QR_ID"].astype(str) == id_eingabe].tolist()
        if idx_list:
            idx = idx_list[0]
            material = df.at[idx, "Material"]
            if df.at[idx, "Status"] == "Eingang":
                st.info(f"Gefunden: **{material}**")
                if st.button(f"✅ {material} jetzt verbrauchen"):
                    df.at[idx, "Status"] = "Verbraucht"
                    df.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                    if save_to_github(df):
                        st.success("Erfolgreich ausgebucht!")
                        st.rerun()
            else:
                st.warning(f"Achtung: Wurde bereits am {df.at[idx, 'Datum_Ausgang']} verbraucht.")
        else:
            st.error("Diese ID existiert nicht im System.")

# (Restliche Seiten bleiben gleich wie vorher...)
elif menu == "Wareneingang":
    st.title("➕ Wareneingang")
    with st.form("in_form"):
        f_id = st.text_input("QR-ID")
        f_name = st.text_input("Material Name")
        f_lief = st.text_input("Lieferant")
        f_preis = st.number_input("Preis", min_value=0.0)
        if st.form_submit_button("Speichern"):
            df = st.session_state.lager_daten
            neue_zeile = {"QR_ID": str(f_id), "Material": str(f_name), "Lieferant": str(f_lief), "Status": "Eingang", "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"), "Datum_Ausgang": "", "Preis": float(f_preis)}
            df = pd.concat([df, pd.DataFrame([neue_zeile])], ignore_index=True)
            if save_to_github(df):
                st.session_state.lager_daten = df
                st.success("Gespeichert!")

else:
    st.title("🖨 QR-Generator")
    qr_id_input = st.text_input("ID für Etikett eingeben:")
    if qr_id_input:
        qr = qrcode.make(qr_id_input)
        buf = io.BytesIO()
        qr.save(buf, format="PNG")
        st.image(buf.getvalue(), caption=f"ID: {qr_id_input}", width=200)
        st.download_button("Download QR-Code", buf.getvalue(), f"QR_{qr_id_input}.png")
