import streamlit as st
from openai import OpenAI
from fpdf import FPDF
import datetime
from supabase import create_client
import requests
import tempfile
import os

# ---------------- Page config ----------------
st.set_page_config(page_title="ImmigrAI – AI USCIS Checklist", layout="centered")

# ---------------- Clients & secrets ----------------
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
supabase = create_client(st.secrets["SUPABASE_URL"], st.secrets["SUPABASE_SERVICE_ROLE_KEY"])

TABLE_NAME = "leads"  # switch to "cases" if you prefer that table name

# ---------------- Helpers ----------------
def strip_non_latin1(text: str) -> str:
    # fpdf classic supports latin-1 only; strip emojis/curly quotes/etc
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
st.write("Get your personalized immigration checklist in seconds. Free preview; $19 for full download + email.")

with st.container():
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

# ---------------- Generate checklist ----------------
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
    # Keep UX clean; logging can be added later
    st.caption("")

# ---------------- Build PDF ----------------
cleaned = strip_non_latin1(checklist_text)
pdf = FPDF()
pdf.add_page()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.set_font("Arial", size=12)
for line in cleaned.split("\n"):
    pdf.multi_cell(0, 10, line)

timestamp = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
file_name = f"{visa_type}_{timestamp}.pdf"

with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
    pdf.output(tmp.name)
    temp_path = tmp.name

# ---------------- Upload to Supabase Storage ----------------
signed_url = None
try:
    with open(temp_path, "rb") as f:
        supabase.storage.from_("casefiles").upload(
            path=file_name,  # bucket-scoped; no leading folder
            file=f,
            file_options={"content-type": "application/pdf"},
        )
    signed_resp = supabase.storage.from_("casefiles").create_signed_url(path=file_name, expires_in=3600)
    signed_url = signed_resp.get("signedURL", "")
except Exception:
    pass
finally:
    try:
        os.remove(temp_path)
    except Exception:
        pass

# ---------------- Delivery / CTA ----------------
st.divider()
if signed_url:
    st.markdown("### 📥 Download & Email")
    st.markdown(f"[Download your checklist PDF]({signed_url})")
    from_email = st.secrets.get("FROM_EMAIL", "onboarding@resend.dev")
    if send_resend_email(email, from_email, petitioner_name or "there", visa_type, signed_url):
        st.success("📧 We also emailed you the download link.")
    else:
        st.warning("Email couldn’t be sent right now, but your direct download link is above.")
else:
    st.markdown("### 🔒 Unlock Full Checklist PDF")
    st.write("Get the professionally formatted PDF and email delivery.")
    st.link_button("💳 Unlock for $19", "https://buy.stripe.com/dRmfZiccndJ52px6sR4wM01")  # replace with your live link

# ---------------- Footer / Trust ----------------
st.markdown("---")
st.caption(
    "ImmigrAI is not a law firm and does not provide legal advice. "
    "This service offers informational checklists based on publicly available USCIS guidance."
)
