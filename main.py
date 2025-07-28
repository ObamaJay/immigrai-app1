import streamlit as st
from openai import OpenAI
from dotenv import load_dotenv
import os
from fpdf import FPDF
from pdfrw import PdfReader, PdfWriter
import datetime
import unicodedata
import zipfile
from io import BytesIO
import smtplib
from email.message import EmailMessage
from supabase import create_client
from pathlib import Path

# ---- Load Environment ----
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ---- Config ----
st.set_page_config(page_title="ImmigrAI", layout="centered")
st.title("🇺🇸 ImmigrAI – Immigration Assistant")

# ---- Text Cleaner ----
def clean_text(text):
    import re
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"(?<=\w) (?=\w)", "", text)  # remove space between letters
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# ---- GPT Call ----
def call_gpt(prompt):
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.4,
    )
    return response.choices[0].message.content

# ---- Checklist PDF ----
def generate_pdf(text, filename="checklist.pdf"):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue
        if line.endswith(":") and len(line.split()) <= 6:
            pdf.set_font("Arial", 'B', 12)
            pdf.cell(0, 10, line, ln=True)
            pdf.set_font("Arial", size=12)
        elif line.startswith("- ") or line.startswith("* ") or line[0].isdigit():
            content = line.lstrip("1234567890. ").strip("-* ").strip()
            pdf.cell(10)
            pdf.cell(0, 10, f"[ ] {content}", ln=True)
        else:
            pdf.multi_cell(0, 10, line)

    os.makedirs("generated", exist_ok=True)
    pdf_path = os.path.join("generated", filename)
    pdf.output(pdf_path)
    with open(pdf_path, "rb") as f:
        f.read()  # force OS to finalize write
    return pdf_path

# ---- Fill Form PDF ----
def fill_form_pdf(input_pdf_path, output_pdf_path, data_dict):
    pdf = PdfReader(input_pdf_path)
    for page in pdf.pages:
        annotations = page['/Annots']
        if annotations:
            for annotation in annotations:
                if annotation['/Subtype'] == '/Widget' and annotation.get('/T'):
                    key = annotation['/T'][1:-1]
                    if key in data_dict:
                        annotation.update({PdfReader.PdfName('/V'): f"{data_dict[key]}"})
    PdfWriter().write(output_pdf_path, pdf)
    with open(output_pdf_path, "rb") as f:
        f.read()  # force flush
    return output_pdf_path

# ---- Send Email ----
import requests

def send_case_email(to_email, subject, body, attachments):
    FROM_EMAIL = "checklist@immigrai.org"
    RESEND_API_KEY = os.getenv("RESEND_API_KEY")

    file_links_html = ""
    for filename, public_url in attachments.items():
        file_links_html += f'<li><a href="{public_url}" download="{filename}">{filename}</a></li>'

    html_body = f"""
    <p>{body}</p>
    <p>Download your documents:</p>
    <ul>{file_links_html}</ul>
    """

    try:
        response = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "from": FROM_EMAIL,
                "to": [to_email],
                "subject": subject,
                "html": html_body
            }
        )
        if response.status_code == 200:
            return True
        else:
            st.error(f"❌ Email failed: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        st.error(f"❌ Email error: {e}")
        return False



# ---- Supabase Helpers ----
def save_case_to_supabase(data):
    try:
        supabase.table("cases").insert([data]).execute()
    except Exception as e:
        st.error(f"Failed to save case: {e}")

def get_saved_cases():
    try:
        response = supabase.table("cases").select("id, petitioner_name, created_at").order("created_at", desc=True).limit(10).execute()
        return response.data
    except:
        return []

def load_case_by_id(case_id):
    try:
        response = supabase.table("cases").select("*").eq("id", case_id).limit(1).execute()
        return response.data[0] if response.data else None
    except:
        return None
   
def upload_to_supabase(filepath, filename):
    try:
        with open(filepath, "rb") as f:
            file_data = f.read()

        # Delete existing file if present
        supabase.storage.from_("casefiles").remove([filename])

        # Upload file
        supabase.storage.from_("casefiles").upload(filename, file_data)

        # Create signed URL (valid 1 hour)
        signed = supabase.storage.from_("casefiles").create_signed_url(filename, 3600)

        if not signed or "signedURL" not in signed:
            st.error("Upload failed: No signed URL returned.")
            return None

        # ✅ Construct correct full URL (handle both relative or full format)
        if signed["signedURL"].startswith("http"):
            public_url = signed["signedURL"]
        else:
            public_url = st.secrets["SUPABASE_URL"].rstrip("/") + signed["signedURL"]

        # ❌ Do NOT append "&download=true" — breaks filename
        return public_url

    except Exception as e:
        st.error(f"Upload error: {e}")
        return None







# ---- Sidebar ----
st.sidebar.title("📜 Saved Cases")
saved_cases = get_saved_cases()
if saved_cases:
    selected = st.sidebar.selectbox("Select a case to load:", saved_cases, format_func=lambda x: f"{x['petitioner_name']} ({x['created_at'][:10]})")
    if selected:
        loaded = load_case_by_id(selected['id'])
        if loaded:
            st.session_state['loaded_case'] = loaded

# ---- Form ----
with st.form("visa_form"):
    st.subheader("Petitioner Information")
    petitioner_first = st.text_input("Petitioner First Name")
    petitioner_last = st.text_input("Petitioner Last Name")
    petitioner_country = st.text_input("Petitioner Country of Birth", value="United States")
    dob_petitioner = st.date_input("Petitioner Date of Birth", value=datetime.date(1990, 1, 1))

    st.subheader("Beneficiary Information")
    beneficiary_first = st.text_input("Beneficiary First Name")
    beneficiary_last = st.text_input("Beneficiary Last Name")
    beneficiary_country = st.text_input("Beneficiary Country of Birth")
    dob_beneficiary = st.date_input("Beneficiary Date of Birth", value=datetime.date(1990, 1, 1))

    st.subheader("Relationship Details")
    relationship = st.selectbox("Relationship Type", ["Spouse", "Fiancé", "Parent", "Child", "Other"])
    visa_type = st.selectbox("Visa Type", ["I-130 (Spouse)", "K-1 (Fiancé)", "Other"])
    marriage_date = st.date_input("Date of Marriage (if applicable)", value=datetime.date.today())
    submit = st.form_submit_button("Generate Checklist")

if submit:
    prompt = f'''
Petitioner: {petitioner_first} {petitioner_last}
Beneficiary: {beneficiary_first} {beneficiary_last}
Relationship: {relationship}
Visa Type: {visa_type}
Country of Birth: {beneficiary_country}
Date of Marriage: {marriage_date.strftime('%B %d, %Y')}
Petitioner DOB: {dob_petitioner.strftime('%B %d, %Y')}
Beneficiary DOB: {dob_beneficiary.strftime('%B %d, %Y')}

Create a USCIS document checklist and draft form field summary for this immigration case.
'''
    output = call_gpt(prompt)
    cleaned_output = clean_text(output)
    checklist_path = generate_pdf(cleaned_output, "checklist.pdf")

    form_data = {
        "form1[0].#subform[0].Pt1Line1_FamilyName[0]": petitioner_last,
        "form1[0].#subform[0].Pt1Line1_GivenName[0]": petitioner_first,
        "form1[0].#subform[0].Pt1Line5_DateofBirth[0]": dob_petitioner.strftime("%m/%d/%Y"),
        "form1[0].#subform[0].Pt1Line6_Country[0]": petitioner_country,
        "form1[0].#subform[0].Pt4Line1_FamilyName[0]": beneficiary_last,
        "form1[0].#subform[0].Pt4Line1_GivenName[0]": beneficiary_first,
        "form1[0].#subform[0].Pt4Line5_DateofBirth[0]": dob_beneficiary.strftime("%m/%d/%Y"),
        "form1[0].#subform[0].Pt4Line6_Country[0]": beneficiary_country,
    }

    input_pdf = os.path.join("forms", "i-130_form.pdf")
    output_pdf = os.path.join("generated", "filled_i130.pdf")
    filled_path = fill_form_pdf(input_pdf, output_pdf, form_data)

    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zip_file:
        zip_file.write(checklist_path, arcname="ImmigrAI_Checklist.pdf")
        zip_file.write(filled_path, arcname="Filled_I130.pdf")
    zip_buffer.seek(0)
    zip_path = os.path.join("generated", "ImmigrAI_CasePackage.zip")
    with open(zip_path, "wb") as f:
        f.write(zip_buffer.getvalue())
        f.flush()
        os.fsync(f.fileno())


    st.session_state["checklist_text"] = output
    st.session_state["checklist_path"] = checklist_path
    st.session_state["filled_path"] = filled_path
    st.session_state["zip_path"] = zip_path

    checklist_txt_url = ""
    try:
        checklist_txt_url = checklist_txt_url = upload_checklist_text_to_supabase(petitioner_first, beneficiary_first, cleaned_output)
    except:
        pass

    case_data = {
        "petitioner_name": f"{petitioner_first} {petitioner_last}".strip(),
        "beneficiary_name": f"{beneficiary_first} {beneficiary_last}".strip(),
        "relationship": relationship,
        "visa_type": visa_type,
        "checklist_text": output.replace("\n", " ").replace("\xa0", " ").strip()[:900],
        "pdf_path": checklist_path.replace("\\", "/").strip(),
        "form_path": filled_path.replace("\\", "/").strip(),
        "checklist_txt_url": checklist_txt_url.strip() if checklist_txt_url else "",
        "bucket_id": "casefiles"
    }

    save_case_to_supabase(case_data)

    st.subheader("✅ Suggested USCIS Checklist")
    st.text_area("Checklist Preview", output, height=300)

    with open(checklist_path, "rb") as f:
        st.download_button("📄 Download Checklist PDF", f, file_name="ImmigrAI_Checklist.pdf")
    with open(filled_path, "rb") as f:
        st.download_button("🖑️ Download Filled I-130 PDF", f, file_name="Filled_I130.pdf")
    st.download_button("📦 Download Full Case ZIP", zip_buffer, file_name="ImmigrAI_CasePackage.zip", mime="application/zip")

# ---- Email Section ----
# ---- Email Section ----
if "checklist_path" in st.session_state and "filled_path" in st.session_state:
    st.markdown("---")
    st.subheader("📧 Email Package")
    email_to = st.text_input("Recipient Email")
    email_message = st.text_area("Optional Message", value="Attached is your immigration case package.")
    send_email = st.button("Send Email")  # ✅ make sure this is here

    if send_email:
        if not email_to:
            st.warning("Please enter an email address.")
        else:
            attachments = {}
            for name, path in {
                "ImmigrAI_Checklist.pdf": st.session_state["checklist_path"],
                "Filled_I130.pdf": st.session_state["filled_path"],
                "ImmigrAI_CasePackage.zip": st.session_state["zip_path"],
            }.items():
                url = upload_to_supabase(path, name)
                if url:
                    attachments[name] = url

            success = send_case_email(
                to_email=email_to,
                subject="Your USCIS Immigration Package",
                body=email_message,
                attachments=attachments,
            )
            if success:
                st.success("✅ Email sent successfully!")


