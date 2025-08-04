import streamlit as st
from openai import OpenAI
from fpdf import FPDF
from io import BytesIO
import datetime
import smtplib
from email.message import EmailMessage
from supabase import create_client

# ---- Config ----
st.set_page_config(page_title="ImmigrAI – AI USCIS Checklist", layout="centered")

# ---- Load Env ----
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- UI Start ----
st.title("📄 ImmigrAI: Smart USCIS Checklist Generator")
st.markdown("Get your personalized checklist in seconds. Free preview. Pay to download official PDF.")

email = st.text_input("📧 Enter your email to begin:", placeholder="you@example.com")
if not email:
    st.stop()

with st.form("checklist_form"):
    st.subheader("📝 Case Info")
    petitioner_name = st.text_input("Petitioner's Full Name")
    beneficiary_name = st.text_input("Beneficiary's Full Name")
    relationship = st.selectbox("Relationship", ["Spouse", "Child", "Parent", "Sibling", "Other"])
    visa_type = st.selectbox("Visa Type", ["I-130 (Family)", "I-129F (Fiancé)", "I-485 (Adjustment)", "Other"])
    submit = st.form_submit_button("🔍 Generate Checklist")

if submit:
    with st.spinner("🧠 Generating checklist..."):
        prompt = f"Create a detailed USCIS document checklist for a {visa_type} visa based on the relationship of a {relationship}. Petitioner: {petitioner_name}, Beneficiary: {beneficiary_name}."
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        checklist_text = response.choices[0].message.content.strip()

        st.success("✅ Checklist Preview")
        st.markdown(checklist_text)

        # Save lead
        supabase.table("leads").insert({
            "email": email,
            "petitioner_name": petitioner_name,
            "beneficiary_name": beneficiary_name,
            "relationship": relationship,
            "visa_type": visa_type,
            "checklist_text": checklist_text,
            "created_at": datetime.datetime.utcnow().isoformat()
        }).execute()

        # PDF creation
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        for line in checklist_text.split("\n"):
            pdf.multi_cell(0, 10, line)
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        # Upload PDF to Supabase
        file_name = f"{visa_type}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"
        try:
            upload = supabase.storage.from_("casefiles").upload(
                path=f"casefiles/{file_name}",
                file=pdf_output,
                file_options={"content-type": "application/pdf"}
            )
            signed_url = supabase.storage.from_("casefiles").create_signed_url(
                path=f"casefiles/{file_name}", expires_in=3600
            ).get("signedURL", "")
        except Exception as e:
            signed_url = None
            print("❌ Upload failed:", str(e))
            st.warning("⚠️ We couldn't upload your checklist. We’ll email it to you shortly.")

        # Send Email
        try:
            msg = EmailMessage()
            msg["Subject"] = "Your ImmigrAI USCIS Checklist"
            msg["From"] = st.secrets["SMTP_SENDER"]
            msg["To"] = email
            msg.set_content("Attached is your AI-generated checklist. Good luck with your visa process!")

            pdf_output.seek(0)
            msg.add_attachment(pdf_output.read(), maintype="application", subtype="pdf", filename="ImmigrAI_Checklist.pdf")

            with smtplib.SMTP(st.secrets["SMTP_SERVER"], st.secrets["SMTP_PORT"]) as server:
                server.starttls()
                server.login(st.secrets["SMTP_SENDER"], st.secrets["SMTP_PASSWORD"])
                server.send_message(msg)

            st.success("📧 Checklist sent to your email!")
        except Exception as e:
            print("❌ Email error:", str(e))
            st.warning("We couldn't send the email, but you can still download your checklist below.")

        # Download or Stripe Gating
        if signed_url:
            st.markdown("### 📥 Download")
            st.markdown(f"[Click here to download your checklist PDF]({signed_url})")
        else:
            st.link_button("💳 Unlock Full Checklist PDF ($19)", "https://buy.stripe.com/test_123456789")  # Replace this link
