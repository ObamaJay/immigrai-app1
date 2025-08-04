import streamlit as st
from openai import OpenAI
from fpdf import FPDF
from io import BytesIO
import datetime
from supabase import create_client
import requests

# ---- Page Config ----
st.set_page_config(page_title="ImmigrAI – AI USCIS Checklist", layout="centered")

# ---- Load Secrets ----
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- UI ----
st.title("📄 ImmigrAI: Smart USCIS Checklist Generator")
st.markdown("Get your personalized immigration checklist in seconds. Free preview, $19 for full download + email.")

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
        prompt = f"Create a detailed USCIS document checklist for a {visa_type} visa based on the relationship: {relationship}. Petitioner: {petitioner_name}, Beneficiary: {beneficiary_name}."
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        checklist_text = response.choices[0].message.content.strip()

        st.success("✅ Checklist Preview")
        st.markdown(checklist_text)

        # Store lead in Supabase
        try:
            supabase.table("leads").insert({
                "email": email,
                "petitioner_name": petitioner_name,
                "beneficiary_name": beneficiary_name,
                "relationship": relationship,
                "visa_type": visa_type,
                "checklist_text": checklist_text,
                "created_at": datetime.datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            print("Lead log failed:", e)

        # Generate PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        for line in checklist_text.split("\n"):
            pdf.multi_cell(0, 10, line)
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        # Upload to Supabase
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        file_name = f"{visa_type}_{timestamp}.pdf"
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
            print("Supabase upload error:", str(e))
            st.warning("⚠️ Could not upload your checklist. You may still receive it via email.")

        # Send email via Resend
        if signed_url:
            try:
                response = requests.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {st.secrets['RESEND_API_KEY']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": st.secrets["FROM_EMAIL"],
                        "to": email,
                        "subject": "Your AI-generated USCIS Checklist",
                        "html": f"""
                            <p>Hi {petitioner_name},</p>
                            <p>Here is your personalized checklist for your {visa_type} visa application.</p>
                            <p>You can download your checklist here:</p>
                            <p><a href="{signed_url}">📥 Download Checklist PDF</a></p>
                            <br><p>Best,<br>The ImmigrAI Team</p>
                        """
                    }
                )
                if response.status_code == 202:
                    st.success("📧 Checklist emailed to you!")
                else:
                    st.warning("⚠️ Email failed — but your download link is still below.")
                    print("Resend error:", response.text)
            except Exception as e:
                print("Email exception:", str(e))
                st.warning("Something went wrong sending the email.")
        else:
            st.warning("Email not sent due to upload error.")

        # PDF Download + Stripe CTA
        if signed_url:
            st.markdown("### 📥 Download Your PDF")
            st.markdown(f"[Click here to download your checklist PDF]({signed_url})", unsafe_allow_html=True)
        else:
            st.markdown("### 🔒 Unlock Your Checklist PDF")
            st.link_button("💳 Unlock Full Checklist PDF ($19)", "https://buy.stripe.com/dRmfZiccndJ52px6sR4wM01import streamlit as st
from openai import OpenAI
from fpdf import FPDF
from io import BytesIO
import datetime
from supabase import create_client
import requests

# ---- Page Config ----
st.set_page_config(page_title="ImmigrAI – AI USCIS Checklist", layout="centered")

# ---- Load Secrets ----
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- UI ----
st.title("📄 ImmigrAI: Smart USCIS Checklist Generator")
st.markdown("Get your personalized immigration checklist in seconds. Free preview, $19 for full download + email.")

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
        prompt = f"Create a detailed USCIS document checklist for a {visa_type} visa based on the relationship: {relationship}. Petitioner: {petitioner_name}, Beneficiary: {beneficiary_name}."
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        checklist_text = response.choices[0].message.content.strip()

        st.success("✅ Checklist Preview")
        st.markdown(checklist_text)

        # Save lead to Supabase
        try:
            supabase.table("leads").insert({
                "email": email,
                "petitioner_name": petitioner_name,
                "beneficiary_name": beneficiary_name,
                "relationship": relationship,
                "visa_type": visa_type,
                "checklist_text": checklist_text,
                "created_at": datetime.datetime.utcnow().isoformat()
            }).execute()
        except Exception as e:
            print("Lead log failed:", e)

        # Generate PDF
        pdf = FPDF()
        pdf.add_page()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)
        for line in checklist_text.split("\n"):
            pdf.multi_cell(0, 10, line)
        pdf_output = BytesIO()
        pdf.output(pdf_output)
        pdf_output.seek(0)

        # Upload to Supabase
        timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
        file_name = f"{visa_type}_{timestamp}.pdf"
        signed_url = None

        try:
            supabase.storage.from_("casefiles").upload(
                path=f"casefiles/{file_name}",
                file=pdf_output,
                file_options={"content-type": "application/pdf"}
            )
            signed_url = supabase.storage.from_("casefiles").create_signed_url(
                path=f"casefiles/{file_name}", expires_in=3600
            ).get("signedURL", "")
        except Exception as e:
            print("❌ Supabase upload error:", str(e))
            st.warning("⚠️ Could not upload your checklist. You may still receive it via email.")

        # Email via Resend
        if signed_url:
            try:
                response = requests.post(
                    "https://api.resend.com/emails",
                    headers={
                        "Authorization": f"Bearer {st.secrets['RESEND_API_KEY']}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "from": st.secrets["FROM_EMAIL"],
                        "to": email,
                        "subject": "Your AI-generated USCIS Checklist",
                        "html": f"""
                            <p>Hi {petitioner_name},</p>
                            <p>Here is your personalized checklist for your {visa_type} visa application.</p>
                            <p><a href="{signed_url}">📥 Click here to download your checklist PDF</a></p>
                            <br><p>Best,<br>The ImmigrAI Team</p>
                        """
                    }
                )
                if response.status_code == 202:
                    st.success("📧 Checklist emailed to you!")
                else:
                    st.warning("⚠️ Email failed — but your download link is still below.")
                    print("Resend error:", response.text)
            except Exception as e:
                print("❌ Resend exception:", str(e))
                st.warning("Email delivery failed.")
        else:
            st.warning("📤 Email skipped due to upload issue.")

        # Final download section
        if signed_url:
            st.markdown("### 📥 Download Your Checklist")
            st.markdown(f"[Click here to download your checklist PDF]({signed_url})", unsafe_allow_html=True)
        else:
            st.markdown("### 🔒 Unlock Full Checklist PDF")
            st.link_button("💳 Unlock for $19", "https://buy.stripe.com/dRmfZiccndJ52px6sR4wM01")  # Replace with live Stripe link
")  # Replace with live Stripe link
