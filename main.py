import streamlit as st
import streamlit.components.v1 as components
from openai import OpenAI
from fpdf import FPDF
import datetime
from supabase import create_client
import requests
import tempfile
import os
import uuid   # 👈 NEW for GA4 client_id

# ---------------- Page config ----------------
st.set_page_config(page_title="ImmigrAI – AI USCIS Checklist", layout="centered")

# ---------------- Feature flags ----------------
PAYWALL = True
TABLE_NAME = "leads"

# ---------------- Clients & secrets ----------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_ROLE_KEY"])

# 👇 NEW: GA4 config
GA4_MEASUREMENT_ID = st.secrets.get("GA4_MEASUREMENT_ID", "")
GA4_API_SECRET = st.secrets.get("GA4_API_SECRET", "")

def send_ga4_event(name: str, params: dict, client_id: str = None):
    """Send a GA4 event via Measurement Protocol."""
    if not GA4_MEASUREMENT_ID or not GA4_API_SECRET:
        return
    if not client_id:
        client_id = str(uuid.uuid4())
    try:
        requests.post(
            f"https://www.google-analytics.com/mp/collect?measurement_id={GA4_MEASUREMENT_ID}&api_secret={GA4_API_SECRET}",
            json={
                "client_id": client_id,
                "events": [{"name": name, "params": params}],
            },
            timeout=5,
        )
    except Exception as e:
        print("⚠️ GA4 event failed:", e)

# ---------------- Helpers ----------------
def strip_non_latin1(text: str) -> str:
    return text.encode("latin1", "ignore").decode("latin1")

def send_resend_email(to_email: str, from_email: str, petitioner: str, visa: str, signed_url: str) -> bool:
    payload = {
        "from": f"ImmigrAI <{from_email}>",
        "to": [to_email],
        "subject": "Your ImmigrAI USCIS Checklist",
        "html": (
            f"<p>Hi {strip_non_latin1(petitioner)},</p>"
            f"<p>Here is your personalized checklist for your {strip_non_latin1(visa)} visa application.</p>"
            f'<p><a href="{signed_url}">Click here to download your checklist PDF</a></p>'
            "<br><p>Best,<br>The ImmigrAI Team</p>"
        ),
        "reply_to": [from_email],
    }
    r = requests.post(
        "https://api.resend.com/emails",
        headers={"Authorization": f"Bearer {st.secrets['RESEND_API_KEY']}", "Content-Type": "application/json"},
        json=payload,
        timeout=20,
    )
    return r.status_code in (200, 202)

# ---------------- UI ----------------
st.title("📄 ImmigrAI: Smart USCIS Checklist Generator")
st.write("Get your personalized immigration checklist in seconds. Free preview; $19 for single checklist or $49 for unlimited 30 days.")

st.markdown("**Start here**")
email = st.text_input("📧 Your email", placeholder="you@example.com")
if not email:
    st.info("Enter your email to begin.")
    st.stop()

with st.form("case_form", clear_on_submit=False):
    st.subheader("📝 Case Information")
    petitioner_name = st.text_input("Petitioner's full name")
    beneficiary_name = st.text_input("Beneficiary's full name")
    relationship = st.selectbox("Relationship", ["Spouse", "Child", "Parent", "Sibling", "Other"])
    visa_type = st.selectbox("Visa type", ["I-130 (Family)", "I-129F (Fiancé)", "I-485 (Adjustment)", "Other"])
    submit = st.form_submit_button("🔍 Generate Checklist")

if not submit:
    st.caption("We don’t store sensitive documents — only the checklist we generate for you.")
    st.stop()

# ---------------- Generate checklist (preview) ----------------
with st.spinner("🧠 Generating your checklist..."):
    prompt = (
        f"Create a detailed USCIS document checklist for a {visa_type} visa for a {relationship} case. "
        f"Petitioner: {petitioner_name}. Beneficiary: {beneficiary_name}. "
        "Use clear, numbered items and short explanations."
    )
    resp = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
    )
    checklist_text = resp.choices[0].message.content.strip()

st.success("✅ Checklist Preview")
st.markdown(checklist_text)

# ---------------- Save lead/case ----------------
try:
    supabase.table(TABLE_NAME).insert({
        "email": email,
        "petitioner_name": petitioner_name,
        "beneficiary_name": beneficiary_name,
        "relationship": relationship,
        "visa_type": visa_type,
        "checklist_text": checklist_text,
        "created_at": datetime.datetime.utcnow().isoformat(),
    }).execute()
except Exception:
    st.caption("")

# ---------------- Paywall logic ----------------
# ---------------- Paywall logic ----------------
if PAYWALL:
    st.divider()
    st.markdown("### 🔒 Unlock Your Full Checklist PDF")
    st.write("Choose your plan below to get your professionally formatted checklist PDF and email delivery.")

    STRIPE_19 = "https://buy.stripe.com/dRmfZiccndJ52px6sR4wM01"
    STRIPE_49 = "https://buy.stripe.com/cNi28sccn34rggn2cB4wM02"

    col1, col2 = st.columns(2)
    with col1:
        if st.button("💳 Get Checklist — $19", use_container_width=True):
            send_ga4_event("checkout_clicked", {"plan": "19"})
            # Force top-level redirect (works in embed with proper sandbox flag)
            st.write(
                f'<script>window.top.location.href="{STRIPE_19}";</script>',
                unsafe_allow_html=True,
            )

    with col2:
        if st.button("📦 Checklist + PDF — $49", use_container_width=True):
            send_ga4_event("checkout_clicked", {"plan": "49"})
            st.write(
                f'<script>window.top.location.href="{STRIPE_49}";</script>',
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.caption(
        "ImmigrAI is not a law firm and does not provide legal advice. "
        "This service offers informational checklists based on publicly available USCIS guidance."
    )
    st.stop()


# ---------------- If paywall is OFF: generate + deliver immediately ----------------
# (unchanged preview/PDF/email logic here)
