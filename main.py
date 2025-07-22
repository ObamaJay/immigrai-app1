
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
from supabase import create_client, Client
from pathlib import Path

# ---- Load Environment ----
load_dotenv()
client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]
supabase: Client = st.secrets["SUPABASE_SERVICE_ROLE_KEY"]

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

    
    output = response.choices[0].message.content


    return response.choices[0].message["content"]

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
    return output_pdf_path

# ---- Upload checklist text to Supabase Storage ----





def upload_checklist_text_to_supabase(petitioner_name: str, beneficiary_name: str, checklist_text: str) -> str:
    filename = f"{petitioner_name.lower().replace(' ', '_')}_{beneficiary_name.lower().replace(' ', '_')}_checklist.txt"
    local_path = Path("generated") / filename
    storage_path = f"checklists/{filename}"

    os.makedirs("generated", exist_ok=True)

    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(checklist_text)

        # Simulate upsert by removing old file
        supabase.storage.from_("casefiles").remove([storage_path])

        # Upload new file without parsing response
        with open(local_path, "rb") as f:
            supabase.storage.from_("casefiles").upload(
                storage_path,
                f,
                {"content-type": "text/plain"}
            )

        public_url = supabase.storage.from_("casefiles").get_public_url(storage_path)
        return public_url.strip()

    except Exception as e:
        st.error(f"❌ Checklist upload failed: {e}")
        return ""

    local_path = Path("generated") / filename
    storage_path = f"checklists/{filename}"

    os.makedirs("generated", exist_ok=True)

    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(checklist_text)

        try:
            supabase.storage.from_("casefiles").remove([storage_path])
        except:
            pass

        with open(local_path, "rb") as f:
            supabase.storage.from_("casefiles").upload(
                storage_path,
                f,
                {"content-type": "text/plain"}
            )

        public_url = supabase.storage.from_("casefiles").get_public_url(storage_path)
        return public_url.strip()

    except Exception as e:
        st.error(f"❌ Checklist upload failed: {e}")
        return ""

    local_path = Path("generated") / filename
    storage_path = f"checklists/{filename}"

    os.makedirs("generated", exist_ok=True)

    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(checklist_text)

        try:
            supabase.storage.from_("casefiles").remove([storage_path])
        except:
            pass  # ignore if file doesn't exist

        with open(local_path, "rb") as f:
            _ = supabase.storage.from_("casefiles").upload(
                storage_path,
                f,
                {"content-type": "text/plain"}
            )

        public_url = supabase.storage.from_("casefiles").get_public_url(storage_path)
        return public_url

    except Exception as e:
        st.error(f"❌ Checklist upload failed: {e}")
        return ""

    local_path = Path("generated") / filename
    storage_path = f"checklists/{filename}"

    os.makedirs("generated", exist_ok=True)

    try:
        # Save checklist text locally
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(checklist_text)

        # Delete existing file (if any) to simulate upsert
        try:
            supabase.storage.from_("casefiles").remove([storage_path])
        except:
            pass  # Ignore if file doesn't exist

        # Upload new file
        with open(local_path, "rb") as f:
            supabase.storage.from_("casefiles").upload(
                storage_path,
                f,
                {"content-type": "text/plain"}
            )

        public_url = supabase.storage.from_("casefiles").get_public_url(storage_path)
        return public_url
    except Exception as e:
        st.error(f"❌ Checklist upload failed: {e}")
        return ""

    local_path = Path("generated") / filename
    storage_path = f"checklists/{filename}"

    os.makedirs("generated", exist_ok=True)

    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(checklist_text)

        with open(local_path, "rb") as f:
            supabase.storage.from_("casefiles").upload(
                storage_path,
                f,
                file_options={"content-type": "text/plain"},
                upsert=True
            )

        public_url = supabase.storage.from_("casefiles").get_public_url(storage_path)
        return public_url
    except Exception as e:
        st.error(f"❌ Checklist upload failed: {e}")
        return ""

    local_path = Path("generated") / filename
    storage_path = f"checklists/{filename}"

    os.makedirs("generated", exist_ok=True)

    try:
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(checklist_text)

        with open(local_path, "rb") as f:
            supabase.storage.from_("casefiles").upload(
                storage_path,
                f,
                {"content-type": "text/plain", "upsert": True}
            )

        public_url = supabase.storage.from_("casefiles").get_public_url(storage_path)
        return public_url
    except Exception as e:
        st.error(f"❌ Checklist upload failed: {e}")
        return ""

# ---- Send Email ----
def send_case_email(to_email, subject, body, attachments):
    from_email = "yourgmail@gmail.com"
    app_password = "your_app_password"

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.set_content(body)

    for filename, filepath in attachments.items():
        with open(filepath, "rb") as f:
            file_data = f.read()
            msg.add_attachment(file_data, maintype="application", subtype="octet-stream", filename=filename)

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(from_email, app_password)
            smtp.send_message(msg)
        return True
    except Exception as e:
        st.error(f"❌ Email failed: {e}")
        return False

# ---- Supabase Save ----
def save_case_to_supabase(data):
    try:
        supabase.table("cases").insert([data]).execute()
    except Exception as e:
        st.error(f"Failed to save case: {e}")

# ---- Supabase Load ----
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

# ---- Sidebar: Load Previous Case ----
st.sidebar.title("📜 Saved Cases")
saved_cases = get_saved_cases()
if saved_cases:
    selected = st.sidebar.selectbox("Select a case to load:", saved_cases, format_func=lambda x: f"{x['petitioner_name']} ({x['created_at'][:10]})")
    if selected:
        loaded = load_case_by_id(selected['id'])
        if loaded:
            st.session_state['loaded_case'] = loaded

# ---- Streamlit Form ----
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

    checklist_txt_url = upload_checklist_text_to_supabase(petitioner_first, beneficiary_first, cleaned_output)

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

    st.session_state["checklist_text"] = output
    st.session_state["checklist_path"] = checklist_path
    st.session_state["filled_path"] = filled_path
    st.session_state["zip_path"] = zip_path

    

    
    
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



    
    st.write("Saving to Supabase:", case_data)
    save_case_to_supabase(case_data)

    st.subheader("✅ Suggested USCIS Checklist")
    st.markdown("```{}```".format(output))

    with open(checklist_path, "rb") as f:
        st.download_button("📄 Download Checklist PDF", f, file_name="ImmigrAI_Checklist.pdf")
    with open(filled_path, "rb") as f:
        st.download_button("🖑️ Download Filled I-130 PDF", f, file_name="Filled_I130.pdf")
    st.download_button("📦 Download Full Case ZIP", zip_buffer, file_name="ImmigrAI_CasePackage.zip", mime="application/zip")

# ---- Email Section ----
if "checklist_path" in st.session_state and "filled_path" in st.session_state:
    st.markdown("---")
    st.subheader("📧 Email Package")
    email_to = st.text_input("Recipient Email")
    email_message = st.text_area("Optional Message", value="Attached is your immigration case package.")
    send_email = st.button("Send Email")

    if send_email:
        if not email_to:
            st.warning("Please enter an email address.")
        else:
            attachments = {
                "ImmigrAI_Checklist.pdf": st.session_state["checklist_path"],
                "Filled_I130.pdf": st.session_state["filled_path"],
                "ImmigrAI_CasePackage.zip": st.session_state["zip_path"],
            }
            success = send_case_email(
                to_email=email_to,
                subject="Your USCIS Immigration Package",
                body=email_message,
                attachments=attachments,
            )
            if success:
                st.success("✅ Email sent successfully!")
