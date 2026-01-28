import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
import cv2
import numpy as np
from github import Github

st.set_page_config(page_title="Lager-Master v3.4", page_icon="📦", layout="wide")

GITHUB_REPO = "mein-lager"
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- GITHUB FUNKTIONEN ---
def save_to_github(df):
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_user().get_repo(GITHUB_REPO)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        try:
            contents = repo.get_contents(GITHUB_FILENAME)
            repo.update_file(path=GITHUB_FILENAME, message=f"Update {datetime.now()}", content=output.getvalue(), sha=contents.sha)
        except:
            repo.create_file(path=GITHUB_FILENAME, message="Initial", content=output.getvalue())
        return True
    except:
        return False

def load_data():
    try:
        df = pd.read_excel(GITHUB_FILENAME)
        for col in ["QR_ID", "Status", "Material"]:
            if col in df.columns: 
                df[col] = df[col].astype(str).replace("nan", "")
        return df
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- NAVIGATION & EXPORT ---
st.sidebar.title("📦 Lager-Menü")

# EXPORT BUTTON JETZT IMMER SICHTBAR
df_current = st.session_state.lager_daten
lager_bestand = df_current[df_current["Status"] == "Eingang"]

buf = io.BytesIO()
with pd.ExcelWriter(buf, engine='openpyxl') as writer:
    # Wir exportieren den aktuellen Bestand (auch wenn er leer ist, ist dann die Tabelle da)
    lager_bestand.to_excel(writer, index=False)

st.sidebar.download_button(
    label="📥 Inventur-Export (Excel)",
    data=buf.getvalue(),
    file_name=f"Lagerstand_{datetime.now().strftime('%d-%m')}.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    help="Lädt den aktuellen Bestand als Excel-Datei herunter"
)

st.sidebar.divider()
menu = st.sidebar.radio("Aktion wählen:", ["📥 Warenannahme", "📤 Warenausgang", "📊 Bestandsliste", "🖨 QR-Druck"])

# --- SCANNER FUNKTION ---
def scan():
    img = st.camera_input("Kamera-Scanner")
    if img:
        try:
            file_bytes = np.asarray(bytearray(img.read()), dtype=np.uint8)
            opencv_image = cv2.imdecode(file_bytes, 1)
            detector = cv2.QRCodeDetector()
            data, _, _ = detector.detectAndDecode(opencv_image)
            return data
        except:
            return None
    return None

# --- SEITEN-LOGIK ---
if menu == "📥 Warenannahme":
    st.header("Wareneingang buchen")
    data = scan()
    if data:
        p = data.split(";")
        if len(p) >= 2:
            s_id, s_mat = p[0].strip(), p[1].strip()
            st.success(f"Erkannt: {s_mat} (ID: {s_id})")
            if st.button("Jetzt einlagern"):
                df = st.session_state.lager_daten
                if not df.empty and ((df["QR_ID"] == s_id) & (df["Status"] == "Eingang")).any():
                    st.error("Diese ID liegt bereits im Lager!")
                else:
                    nz = {
                        "QR_ID": s_id, 
                        "Material": s_mat, 
                        "Lieferant": p[2] if len(p)>2 else "Unbekannt", 
                        "Status": "Eingang", 
                        "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"), 
                        "Datum_Ausgang": "", 
                        "Preis": float(p[3]) if len(p)>3 else 0.0
                    }
                    st.session_state.lager_daten = pd.concat([df, pd.DataFrame([nz])], ignore_index=True)
                    if save_to_github(st.session_state.lager_daten):
                        st.success("Erfolgreich gespeichert!")
                        st.rerun()

elif menu == "📤 Warenausgang":
    st.header("Warenausgang buchen")
    sid = scan()
    if sid:
        clean_id = sid.split(";")[0].strip()
        df = st.session_state.lager_daten
        t = df[(df["QR_ID"] == clean_id) & (df["Status"] == "Eingang")]
        if not t.empty:
            st.warning(f"Material gefunden: {df.at[t.index[0], 'Material']}")
            if st.button("Als VERBRAUCHT markieren"):
                df.at[t.index[0], "Status"] = "Verbraucht"
                df.at[t.index[0], "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                if save_to_github(df):
                    st.success("Abgebucht!")
                    st.rerun()
        else:
            st.error("Diese ID ist nicht im aktuellen Bestand vorhanden.")

elif menu == "📊 Bestandsliste":
    st.header("Aktueller Lagerbestand")
    if lager_bestand.empty:
        st.info("Das Lager ist aktuell leer.")
    else:
        st.dataframe(lager_bestand, use_container_width=True)

else:
    st.header("QR-Generator (Intern)")
    c1, c2 = st.columns(2)
    id_in = c1.text_input("ID")
    ma_in = c2.text_input("Material")
    if id_in and ma_in:
        code = f"{id_in};{ma_in};Intern;0.0"
        buf = io.BytesIO()
        qrcode.make(code).save(buf, format="PNG")
        st.image(buf.getvalue(), width=200)
        st.download_button("QR Herunterladen", buf.getvalue(), f"QR_{id_in}.png")
