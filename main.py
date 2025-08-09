import streamlit as st
from openai import OpenAI
from fpdf import FPDF
import datetime
from supabase import create_client
import requests
import tempfile
import os

# ---------------- Config ----------------
st.set_page_config(page_title="ImmigrAI – AI USCIS Checklist", layout="centered")
DEBUG = True  # flip to True to see raw responses/errors

# ---------------- Secrets / Clients ----------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_ROLE_KEY"])

# ---------------- UI ----------------
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

def remove_non_latin1(text: str) -> str:
    # fpdf (classic) is latin-1; strip emojis/curly quotes/etc
    return text.encode("latin1", "ignore").decode("latin1")

if submit:
    with st.spinner("🧠 Generating checklist..."):
        prompt = (
            f"Create a detailed USCIS document checklist for a {visa_type} visa based on the relationship: "
            f"{relationship}. Petitioner: {petitioner_name}, Beneficiary: {beneficiary_name}."
        )
        resp = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.5,
        )
        checklist_text = resp.choices[0].message.content.strip()

    st.success("✅ Checklist Preview")
    st.markdown(checklist_text)

    # ---------- Save to DB (table: leads) ----------
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
        st.warning("⚠️ Could not save lead to database.")
        if DEBUG: st.exception(e)

    # ---------- Build PDF (latin-1 safe) ----------
    cleaned = remove_non_latin1(checklist_text)
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)
    for line in cleaned.split("\n"):
        pdf.multi_cell(0, 10, line)

    # write to a temp file for upload
    timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    file_name = f"{visa_type}_{timestamp}.pdf"
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        pdf.output(tmp.name)
        temp_path = tmp.name

    # ---------- Upload to Supabase Storage ----------
    signed_url = None
    try:
        with open(temp_path, "rb") as f:
            upload_resp = supabase.storage.from_("casefiles").upload(
                path=file_name,
                file=f,
                file_options={"content-type": "application/pdf"}
            )
        if DEBUG:
            st.text("Upload response:")
            st.write(upload_resp)

        signed_resp = supabase.storage.from_("casefiles").create_signed_url(
            path=file_name,
            expires_in=3600
        )
        if DEBUG:
            st.text("Signed URL response:")
            st.write(signed_resp)

        signed_url = signed_resp.get("signedURL", "")
    except Exception as e:
        st.warning("⚠️ Could not upload your checklist. You may still receive it via email.")
        if DEBUG: st.exception(e)
    finally:
        try: os.remove(temp_path)
        except Exception: pass

    # ---------- Email via Resend (only if upload worked) ----------
    if signed_url:
        try:
            r = requests.post(
                "https://api.resend.com/emails",
                headers={
                    "Authorization": f"Bearer {st.secrets['RESEND_API_KEY']}",
                    "Content-Type": "application/json"
                },
                json={
                    "from": st.secrets["FROM_EMAIL"],
                    "to": email,
                    "subject": "Your AI-generated USCIS Checklist",
                    "html": (
                        f"<p>Hi {remove_non_latin1(petitioner_name)},</p>"
                        f"<p>Here is your personalized checklist for your {remove_non_latin1(visa_type)} visa application.</p>"
                        f'<p><a href="{signed_url}">📥 Click here to download your checklist PDF</a></p>'
                        "<br><p>Best,<br>The ImmigrAI Team</p>"
                    ),
                }
            )
            if r.status_code == 202:
                st.success("📧 Checklist emailed to you!")
            else:
                st.warning("⚠️ Email failed — but your download link is still below.")
                if DEBUG: st.text(r.text)
        except Exception as e:
            st.warning("Email delivery failed.")
            if DEBUG: st.exception(e)
    else:
        st.warning("📤 Email skipped due to upload issue.")

    # ---------- Final download / CTA ----------
    if signed_url:
        st.markdown("### 📥 Download Your Checklist")
        st.markdown(f"[Click here to download your checklist PDF]({signed_url})", unsafe_allow_html=True)
    else:
        st.markdown("### 🔒 Unlock Full Checklist PDF")
        st.link_button("💳 Unlock Full Checklist PDF ($19)", "https://buy.stripe.com/dRmfZiccndJ52px6sR4wM0")  # replace with your live link
