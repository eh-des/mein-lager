import streamlit as st
import pandas as pd
from datetime import datetime
import io
import qrcode
import cv2
import numpy as np
from github import Github

st.set_page_config(page_title="Lager-Master v3.3", page_icon="📦", layout="wide")

GITHUB_REPO = "mein-lager"
GITHUB_FILENAME = "Lagerbestand.xlsx"

# --- GITHUB SPEICHERN ---
def save_to_github(df):
    try:
        g = Github(st.secrets["GITHUB_TOKEN"])
        repo = g.get_user().get_repo(GITHUB_REPO)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            df.to_excel(writer, index=False)
        contents = repo.get_contents(GITHUB_FILENAME)
        repo.update_file(path=GITHUB_FILENAME, message=f"Update {datetime.now()}", content=output.getvalue(), sha=contents.sha)
        return True
    except:
        return False

def load_data():
    try:
        df = pd.read_excel(GITHUB_FILENAME)
        for col in ["QR_ID", "Status", "Material"]:
            if col in df.columns: df[col] = df[col].astype(str).replace("nan", "")
        return df
    except:
        return pd.DataFrame(columns=["QR_ID", "Material", "Lieferant", "Status", "Datum_Eingang", "Datum_Ausgang", "Preis"])

if "lager_daten" not in st.session_state:
    st.session_state.lager_daten = load_data()

# --- NAVIGATION ---
st.sidebar.title("Lager-Menü")
menu = st.sidebar.radio("Aktion:", ["📥 Warenannahme", "📤 Warenausgang", "📊 Bestandsliste", "🖨 QR-Druck"])

# --- EXPORT (NEU) ---
df_current = st.session_state.lager_daten
lager_bestand = df_current[df_current["Status"] == "Eingang"]
st.sidebar.divider()
if not lager_bestand.empty:
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine='openpyxl') as writer:
        lager_bestand.to_excel(writer, index=False)
    st.sidebar.download_button("📥 Inventur-Export (Excel)", buf.getvalue(), f"Bestand_{datetime.now().strftime('%d-%m')}.xlsx")

# --- SCANNER LOGIK ---
def scan():
    img = st.camera_input("Scanner")
    if img:
        detector = cv2.QRCodeDetector()
        data, _, _ = detector.detectAndDecode(cv2.imdecode(np.asarray(bytearray(img.read()), dtype=np.uint8), 1))
        return data
    return None

# --- SEITEN ---
if menu == "📥 Warenannahme":
    st.header("Wareneingang")
    data = scan()
    if data:
        p = data.split(";")
        if len(p) >= 2:
            s_id, s_mat = p[0].strip(), p[1].strip()
            st.success(f"Gelesen: {s_mat} (ID: {s_id})")
            if st.button("Einlagern"):
                df = st.session_state.lager_daten
                if not df.empty and ((df["QR_ID"] == s_id) & (df["Status"] == "Eingang")).any():
                    st.error("ID bereits vorhanden!")
                else:
                    nz = {"QR_ID": s_id, "Material": s_mat, "Lieferant": p[2] if len(p)>2 else "", "Status": "Eingang", "Datum_Eingang": datetime.now().strftime("%d.%m.%Y"), "Datum_Ausgang": "", "Preis": float(p[3]) if len(p)>3 else 0.0}
                    st.session_state.lager_daten = pd.concat([df, pd.DataFrame([nz])], ignore_index=True)
                    save_to_github(st.session_state.lager_daten)
                    st.rerun()

elif menu == "📤 Warenausgang":
    st.header("Warenausgang")
    sid = scan()
    if sid:
        clean_id = sid.split(";")[0].strip()
        df = st.session_state.lager_daten
        t = df[(df["QR_ID"] == clean_id) & (df["Status"] == "Eingang")]
        if not t.empty:
            st.warning(f"Material: {df.at[t.index[0], 'Material']}")
            if st.button("Abbuchen"):
                df.at[t.index[0], "Status"] = "Verbraucht"
                df.at[t.index[0], "Datum_Ausgang"] = datetime.now().strftime("%d.%m.%Y")
                save_to_github(df)
                st.rerun()

elif menu == "📊 Bestandsliste":
    st.header("Aktueller Bestand")
    st.dataframe(lager_bestand, use_container_width=True)

else:
    st.header("QR-Generator")
    c1, c2 = st.columns(2)
    id_in = c1.text_input("ID")
    ma_in = c2.text_input("Material")
    if id_in and ma_in:
        code = f"{id_in};{ma_in};Lieferant;10.0"
        buf = io.BytesIO()
        qrcode.make(code).save(buf, format="PNG")
        st.image(buf.getvalue(), width=200)
