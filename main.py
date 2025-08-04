import streamlit as st
import os
from openai import OpenAI
from dotenv import load_dotenv
from fpdf import FPDF
from io import BytesIO
from supabase import create_client
from email.message import EmailMessage
import smtplib
import datetime

# ---- Load Environment ----
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- Page Config ----
st.set_page_config(page_title="ImmigrAI – AI Visa Checklist Generator", layout="centered")

# ---- UI ----
st.title("📄 ImmigrAI: Smart USCIS Checklist Generator")
st.markdown("Get your **AI-powered visa checklist** in seconds. Free preview. Pay to download official PDF.")

# ---- Email Capture ----
email = st.text_input("Enter your email to begin:", placeholder="you@example.com")
if not email:
    st.stop()

# ---- User Input Form ----
with st.form("checklist_form"):
    st.subheader("Case Information")
    petitioner_name = st.text_input("Petitioner's Full Name")
    beneficiary_name = st.text_input("Beneficiary's Full Name")
    relationship = st.selectbox("Relationship", ["Spouse", "Child", "Parent", "Sibling", "Other"])
    visa_type = st.selectbox("Visa Type", ["I-130 (Family)", "I-129F (Fiancé)", "I-485 (Adjustment)", "Other"])
    submit = st.form_submit_button("Generate Checklist")

# ---- Generate Checklist ----
if submit:
    with st.spinner("Generating your checklist..."):
        prompt = f"Create a detailed USCIS document checklist for a {visa_type} visa based on this relationship: {relationship}. Petitioner: {petitioner_name}, Beneficiary: {beneficiary_name}."
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        checklist_text = response.choices[0].message.content.strip()

        # Show preview
        st.success("✅ Checklist Preview")
        st.markdown(checklist_text)

        # Save preview info (optional: Supabase log)
        supabase.table("leads").insert({
            "email": email,
            "petitioner_name": petitioner_name,
            "beneficiary_name": beneficiary_name,
            "relationship": relationship,
            "visa_type": visa_type,
            "checklist_text": checklist_text,
            "created_at": datetime.datetime.utcnow().isoformat()
        }).execute()

        # Gate the PDF behind Stripe
        st.markdown("### 📥 Want your printable PDF?")
        st.markdown("Unlock full checklist + formatted PDF + email delivery.")

        st.link_button("💳 Unlock Full Checklist ($19)", "https://buy.stripe.com/test_123456789")  # Replace with your live Stripe link
