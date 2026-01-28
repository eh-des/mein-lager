import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
import cv2
import numpy as np
from github import Github

st.set_page_config(page_title="Lager-Master", page_icon="📦", layout="wide")

# --- KONFIGURATION ---
GITHUB_REPO = "mein-lager"
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- FUNKTIONEN ---
def save_to_github(df):
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_user().get_repo(GITHUB_REPO)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        contents = repo.get_contents(GITHUB_FILENAME)
        repo.update_file(path=GITHUB_FILENAME, message="Lager-Update", content=output.getvalue(), sha=contents.sha)
        return True
    except Exception as e:
        st.error(f"Speicherfehler: {e}")
        return False

def load_data():
    try:
        df = pd.read_excel(GITHUB_FILENAME)
        df["QR_ID"] = df["QR_ID"].astype(str)
        df["Status"] = df["Status"].astype(str)
        return df
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- NAVIGATION ---
st.sidebar.title("Lager-Steuerung")
menu = st.sidebar.radio("Aktion wählen:", ["📥 Warenannahme", "📤 Warenausgang", "📊 Bestandsliste", "🖨 QR-Druck"])

# --- FUNKTION: QR-SCANNER ---
def qr_scanner_logic(label):
    img_file = st.camera_input(label)
    if img_file:
        file_bytes = np.asarray(bytearray(img_file.read()), dtype=np.uint8)
        opencv_image = cv2.imdecode(file_bytes, 1)
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(opencv_image)
        return data
    return None

# --- SEITE: WARENANNAHME ---
if menu == "📥 Warenannahme":
    st.header("Neue Ware einscannen")
    st.info("Scanner erkennt Format: ID;Material;Lieferant;Preis")
    
    scanned_data = qr_scanner_logic("Kamera für ANNAHME")
    
    if scanned_data:
        # Zerlegen der Daten (ID;Name;Lief;Preis)
        parts = scanned_data.split(";")
        if len(parts) >= 2:
            s_id = parts[0]
            s_mat = parts[1]
            s_lief = parts[2] if len(parts) > 2 else "Unbekannt"
            s_preis = parts[3] if len(parts) > 3 else 0.0
            
            st.write(f"**Gelesen:** ID: {s_id} | Material: {s_mat}")
            
            if st.button(f"Gebinde {s_id} jetzt EINLAGERN"):
                df = st.session_state.lager_daten
                if s_id in df["QR_ID"].astype(str).values:
                    st.error("Dieses Gebinde (ID) ist bereits im System!")
                else:
                    neue_zeile = {
                        "QR_ID": str(s_id), "Material": str(s_mat), "Lieferant": str(s_lief),
                        "Status": "Eingang", "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"),
                        "Datum_Ausgang": "", "Preis": float(s_preis)
                    }
                    df = pd.concat([df, pd.DataFrame([neue_zeile])], ignore_index=True)
                    if save_to_github(df):
                        st.session_state.lager_daten = df
                        st.success("Ware erfolgreich eingebucht!")
        else:
            st.error("QR-Code Format ungültig (ID;Name;Lief;Preis erwartet)")

# --- SEITE: WARENAUSGANG ---
elif menu == "📤 Warenausgang":
    st.header("Ware verbrauchen")
    scanned_id = qr_scanner_logic("Kamera für AUSGANG")
    
    if scanned_id:
        # Falls der ganze Code gescannt wurde, nur die ID nehmen
        clean_id = scanned_id.split(";")[0]
        df = st.session_state.lager_daten
        idx_list = df.index[df["QR_ID"].astype(str) == clean_id].tolist()
        
        if idx_list:
            idx = idx_list[0]
            if df.at[idx, "Status"] == "Eingang":
                st.warning(f"Material gefunden: **{df.at[idx, 'Material']}**")
                if st.button("Als VERBRAUCHT markieren"):
                    df.at[idx, "Status"] = "Verbraucht"
                    df.at[idx, "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                    if save_to_github(df):
                        st.success("Ware ausgebucht!")
                        st.rerun()
            else:
                st.error("Dieses Gebinde wurde bereits ausgebucht!")
        else:
            st.error("ID nicht im Bestand gefunden.")

# --- SEITE: BESTANDSLISTE ---
elif menu == "📊 Bestandsliste":
    st.header("Aktueller Ist-Bestand")
    df = st.session_state.lager_daten
    lager_aktuell = df[df["Status"] == "Eingang"]
    st.write(f"Aktuell befinden sich {len(lager_aktuell)} Gebinde im Lager.")
    st.dataframe(lager_aktuell[["QR_ID", "Material", "Lieferant", "Preis", "Datum_Eingang"]], use_container_width=True)

# --- SEITE: QR-DRUCK ---
else:
    st.header("Eigene QR-Codes erzeugen")
    t_id = st.text_input("ID")
    t_mat = st.text_input("Material Name")
    t_lief = st.text_input("Lieferant")
    t_preis = st.number_input("Preis", min_value=0.0)
    
    if t_id and t_mat:
        full_code = f"{t_id};{t_mat};{t_lief};{t_preis}"
        qr_img = qrcode.make(full_code)
        buf = io.BytesIO()
        qr_img.save(buf, format="PNG")
        st.image(buf.getvalue(), caption=f"Code für Lieferant: {full_code}", width=250)
        st.download_button("QR-Code herunterladen", buf.getvalue(), f"QR_{t_id}.png")
