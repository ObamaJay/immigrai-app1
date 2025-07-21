import os
from supabase import create_client, Client
from pathlib import Path

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_checklist_text_to_supabase(petitioner_name: str, beneficiary_name: str, checklist_text: str) -> str:
    filename = f"{petitioner_name.lower().replace(' ', '_')}_{beneficiary_name.lower().replace(' ', '_')}_checklist.txt"
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
        raise RuntimeError(f"❌ Checklist upload failed: {e}")
