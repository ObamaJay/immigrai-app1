import os
from supabase import create_client, Client

# ✅ SETUP SUPABASE
url = "https://jdkfxiftaleaxobenwiy.supabase.co"
key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Impka2Z4aWZ0YWxlYXhvYmVud2l5Iiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTI2OTk3MDksImV4cCI6MjA2ODI3NTcwOX0.m3gUT1lEwk653PBiFdLnzWnKkX_zxu0RChICkBPozKc"
supabase: Client = create_client(url, key)

# ✅ CASE DETAILS
petitioner_name = "Sarah Johnson"
beneficiary_name = "Ahmed Kahn"
checklist_text = """USCIS Document Checklist:
1. Form I-130, Petition for Alien Relative
2. Copy of petitioner's birth certificate
3. Copy of beneficiary's birth certificate
4. Marriage certificate
5. Proof of petitioner's U.S. citizenship or lawful permanent resident status
6. Proof of bona fide marriage relationship (e.g. joint bank accounts, lease agreements, photos together)
7. Passport-style photos of petitioner and beneficiary
8. Any relevant divorce decrees or death certificates if either party was previously married
"""

filename = f"{petitioner_name.lower().replace(' ', '_')}_{beneficiary_name.lower().replace(' ', '_')}_checklist.txt"
local_path = f"./{filename}"
storage_path = f"checklists/{filename}"

# ✅ 1. SAVE CHECKLIST TEXT LOCALLY
with open(local_path, "w", encoding="utf-8") as f:
    f.write(checklist_text)

# ✅ 2. UPLOAD TO SUPABASE STORAGE
try:
    supabase.storage.from_("casefiles").upload(
        storage_path,
        local_path,
        {"content-type": "text/plain"}
    )

    # Make it public (optional: only if your bucket isn't public by default)
    public_url = supabase.storage.from_("casefiles").get_public_url(storage_path)

    print("✅ Uploaded checklist to:", public_url)

except Exception as e:
    print("❌ Upload failed:", e)
    exit()

# ✅ 3. INSERT CASE RECORD INTO DATABASE
case_data = {
    "petitioner_name": petitioner_name,
    "beneficiary_name": beneficiary_name,
    "relationship": "Spouse",
    "visa_type": "I-130 (Spouse)",
    "checklist_text": "Checklist stored in Supabase Storage.",
    "checklist_txt_url": public_url,
    "pdf_path": "generated/checklist.pdf",
    "form_path": "generated/filled_i130.pdf",
}

try:
    supabase.table("cases").insert(case_data).execute()
    print("✅ Case saved to database.")

except Exception as e:
    print("❌ Failed to insert case:", e)
