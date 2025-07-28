import streamlit as st
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import re

st.set_page_config(page_title="WhatsApp Bulk Sender", layout="centered")

st.title("📲 WhatsApp Bulk Message Sender")
st.markdown("Upload Excel or Google Sheet, customize your message, and send to auto-detected phone numbers via WhatsApp Web.")

# Input fields
gsheet_url = st.text_input("🔗 Google Sheet URL (optional)")
uploaded_file = st.file_uploader("📤 Or upload Excel (.xlsx)", type=["xlsx"])
message_template = st.text_area("💬 Message (use {{name}} if needed)", 
                                "Hi {{name}}, please join our group: https://chat.whatsapp.com/YourLinkHere")
start_button = st.button("🚀 Start Sending")
log_area = st.empty()

# Detect phone number column
def detect_phone_column(df):
    keywords = ["phone", "mobile", "number", "contact", "whatsapp"]
    for col in df.columns:
        col_lower = col.strip().lower()
        if any(k in col_lower for k in keywords):
            return col
    return None

# Extract Google Sheet CSV URL
def extract_sheet_id(url):
    match = re.search(r"/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else None

# Load data
def load_data():
    if uploaded_file:
        df = pd.read_excel(uploaded_file)
    elif gsheet_url:
        sheet_id = extract_sheet_id(gsheet_url)
        if not sheet_id:
            st.error("❌ Invalid Google Sheet URL")
            return None
        try:
            df = pd.read_csv(f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv")
        except Exception as e:
            st.error(f"❌ Failed to load Google Sheet: {e}")
            return None
    else:
        st.warning("Please upload a file or provide a Google Sheet URL.")
        return None

    phone_col = detect_phone_column(df)
    if not phone_col:
        st.error("❌ No phone number column detected.")
        return None

    df = df.copy()
    df["phone"] = df[phone_col].astype(str).str.replace(r"\D", "", regex=True)
    df["name"] = df[df.columns[0]].astype(str) if "name" not in df.columns else df["name"].astype(str)
    return df[["phone", "name"]]

# Message template
def personalize(template, name):
    return template.replace("{{name}}", name)

# WhatsApp sender
def send_whatsapp(df, template):
    status_log = []
    st.warning("📲 Launching Chrome. Please scan the QR code.")
    driver = webdriver.Chrome()
    driver.get("https://web.whatsapp.com")
    input("🔐 Scan QR code and press ENTER in terminal...")

    for _, row in df.iterrows():
        number = row["phone"]
        name = row["name"]
        message = personalize(template, name)
        encoded = message.replace(" ", "%20")
        url = f"https://web.whatsapp.com/send?phone={number}&text={encoded}"
        driver.get(url)
        time.sleep(10)

        try:
            send_btn = driver.find_element(By.XPATH, '//span[@data-icon="send"]')
            send_btn.click()
            status_log.append({"phone": number, "name": name, "status": "✅ Sent"})
            log_area.write(f"✅ Sent to {name} ({number})")
        except Exception as e:
            status_log.append({"phone": number, "name": name, "status": f"❌ Failed: {e}"})
            log_area.write(f"❌ Failed to {name} ({number})")

        time.sleep(5)

    driver.quit()
    return pd.DataFrame(status_log)

# Trigger flow
if start_button and message_template.strip():
    df = load_data()
    if df is not None:
        st.success(f"📄 Loaded {len(df)} valid rows.")
        result_df = send_whatsapp(df, message_template)
        st.success("🎉 Completed!")
        st.dataframe(result_df)

        csv = result_df.to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Download Result", csv, "whatsapp_results.csv", "text/csv")
