# main.py
import os
import uuid
import requests
import streamlit as st
import streamlit.components.v1 as components

# ──────────────────────────────────────────────────────────────
# GA4 CONFIG (Measurement Protocol)
# ──────────────────────────────────────────────────────────────
GA4_MEASUREMENT_ID = st.secrets.get("GA4_MEASUREMENT_ID", os.getenv("GA4_MEASUREMENT_ID", ""))
GA4_API_SECRET     = st.secrets.get("GA4_API_SECRET",     os.getenv("GA4_API_SECRET", ""))
GA4_ENDPOINT = (
    f"https://www.google-analytics.com/mp/collect?measurement_id={GA4_MEASUREMENT_ID}&api_secret={GA4_API_SECRET}"
    if GA4_MEASUREMENT_ID and GA4_API_SECRET else ""
)

def send_ga4_event(name: str, params: dict | None = None, client_id: str | None = None) -> None:
    if not GA4_ENDPOINT:
        return
    if client_id is None:
        client_id = str(uuid.uuid4())
    payload = {"client_id": client_id, "events": [{"name": name, "params": params or {}}]}
    try:
        requests.post(GA4_ENDPOINT, json=payload, timeout=3)
    except Exception:
        pass

# One stable GA client id per Streamlit session
if "ga_client_id" not in st.session_state:
    st.session_state["ga_client_id"] = str(uuid.uuid4())
GA_CLIENT_ID = st.session_state["ga_client_id"]

# ──────────────────────────────────────────────────────────────
# STRIPE MODE + LINKS
# ──────────────────────────────────────────────────────────────
DEFAULT_MODE = st.secrets.get("STRIPE_MODE", os.getenv("STRIPE_MODE", "live")).strip().lower()
ALLOW_SWITCH = st.secrets.get("ALLOW_MODE_SWITCH", os.getenv("ALLOW_MODE_SWITCH", "false")).strip().lower() == "true"

# Persist mode across interactions if switching is allowed
if "stripe_mode" not in st.session_state:
    st.session_state["stripe_mode"] = DEFAULT_MODE

if ALLOW_SWITCH:
    with st.sidebar:
        st.caption("Developer")
        st.session_state["stripe_mode"] = st.selectbox("Stripe Mode", ["test", "live"], index=0 if DEFAULT_MODE=="test" else 1)

MODE = st.session_state["stripe_mode"]

# pull links by mode
def get_link(name: str) -> str:
    key = f"STRIPE_{MODE.upper()}_{name}"
    return st.secrets.get(key, os.getenv(key, ""))

LINK_19 = get_link("LINK_19")
LINK_49 = get_link("LINK_49")

# ──────────────────────────────────────────────────────────────
# PAGE SETUP
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="ImmigrAI – USCIS Checklist Generator", page_icon="🧾", layout="centered")
st.markdown(
    """
# ImmigrAI: Smart USCIS Checklist Generator

Get your personalized immigration checklist in seconds. Free preview; **$19** for a single checklist or **$49** for unlimited 30 days.
"""
)
st.markdown("---")

# ──────────────────────────────────────────────────────────────
# INPUTS & PREVIEW GENERATOR (rules-based — instant, no API needed)
# ──────────────────────────────────────────────────────────────
st.subheader("Start here")
with st.form("intake"):
    colA, colB = st.columns(2)
    with colA:
        full_name = st.text_input("Full name", placeholder="Jane Doe", autocomplete="name")
        email = st.text_input("Email (to send your checklist)", placeholder="jane@example.com")
    with colB:
        form_type = st.selectbox(
            "What are you applying for?",
            ["I-130 (Petition for Alien Relative)", "I-485 (Adjustment of Status)", "I-129F (K-1 fiancé(e))", "N-400 (Naturalization)"],
        )
        is_spouse = st.selectbox("Is the beneficiary your spouse?", ["No", "Yes"])
    relation_notes = st.text_area("Anything else we should consider?", placeholder="Prior marriages, name changes, joint lease, etc.")

    submitted = st.form_submit_button("Generate free preview")
    if submitted:
        send_ga4_event(
            "generate_checklist_started",
            {"form_type": form_type, "spouse": is_spouse.lower() == "yes"},
            client_id=GA_CLIENT_ID,
        )

        base = [
            ("Government ID", "Photo ID for each applicant (passport or driver’s license)."),
            ("Filing Fee Payment", "Check or money order; verify current fee on USCIS.gov."),
            ("USCIS Forms", "Complete & sign the latest USCIS version."),
        ]

        if form_type.startswith("I-130"):
            items = [
                ("Form I-130", "Petition for Alien Relative (latest USCIS version)."),
                ("Proof of Petitioner Status", "Passport, naturalization certificate, or green card."),
                ("Marriage Certificate", "If petitioning a spouse."),
                ("Proof of Relationship", "Joint bank statements, lease/mortgage, photos, affidavits."),
            ]
        elif form_type.startswith("I-485"):
            items = [
                ("Form I-485", "Application to Register Permanent Residence or Adjust Status."),
                ("Two Passport Photos", "2x2 inches, white background."),
                ("I-693 (Medical)", "Sealed envelope from civil surgeon (if required)."),
                ("I-864 (Affidavit of Support)", "If needed based on category."),
            ]
        elif form_type.startswith("I-129F"):
            items = [
                ("Form I-129F", "Petition for Alien Fiancé(e)."),
                ("Proof of Meeting", "Evidence you met in person within 2 years."),
                ("Intent to Marry", "Letters of intent to marry within 90 days of entry."),
            ]
        else:  # N-400
            items = [
                ("Form N-400", "Application for Naturalization."),
                ("Residence Evidence", "Green card (front/back), travel history."),
                ("Selective Service", "If applicable."),
            ]

        if is_spouse == "Yes" and not any("Marriage Certificate" in x[0] for x in items):
            items.append(("Marriage Certificate", "Certified copy; provide translation if not in English."))

        st.session_state["preview_items"] = base + items
        st.session_state["full_name"] = (full_name or "").strip()
        st.session_state["email"] = (email or "").strip()
        st.session_state["form_type"] = form_type

# Show preview if available
if "preview_items" in st.session_state:
    st.success("✅ Preview generated! Review below.")
    st.caption("This is a sample preview. Your purchased checklist PDF will be formatted & personalized.")
    st.markdown("#### Your checklist preview")
    for idx, (title, note) in enumerate(st.session_state["preview_items"], start=1):
        st.markdown(f"**{idx}. {title}** — {note}")

    st.divider()
    st.markdown("#### Email this preview (optional)")
    with st.form("email_preview"):
        email_now = st.text_input("Confirm email", value=st.session_state.get("email", ""))
        send_btn = st.form_submit_button("Send preview")
        if send_btn:
            st.session_state["email"] = (email_now or "").strip()
            st.info(f"Preview queued for **{email_now}** (demo).")
            send_ga4_event(
                "lead_captured",
                {
                    "email_domain": (email_now.split("@", 1)[1] if "@" in email_now else ""),
                    "form_type": st.session_state.get("form_type", ""),
                },
                client_id=GA_CLIENT_ID,
            )

# ──────────────────────────────────────────────────────────────
# PAYWALL SECTION — open checkout in new tab; only fires begin_checkout on click
# ──────────────────────────────────────────────────────────────
st.divider()
st.markdown(f"### 🔒 Unlock Your Full Checklist PDF  \n*Mode:* **{MODE.upper()}**")

def open_checkout(url: str):
    """Open Stripe in a new tab from a user gesture; render a fallback link if pop-up blocked."""
    if not url:
        st.error("No Stripe link configured for this mode.")
        return
    components.html(
        f"""
        <script>
          try {{ window.open("{url}", "_blank", "noopener"); }}
          catch(e) {{ window.location.href = "{url}"; }}
        </script>
        <div style="margin-top:8px">
          <a href="{url}" target="_blank" rel="noopener"
             style="display:inline-block;padding:.6rem 1rem;border-radius:.5rem;
                    background:#635bff;color:white;text-decoration:none;font-weight:600;">
             Open Checkout
          </a>
        </div>
        """,
        height=90,
    )
    st.info("If a new tab didn’t open, click “Open Checkout”.", icon="🔗")

col1, col2 = st.columns(2)

with col1:
    if st.button("💳 Get Checklist — $19", use_container_width=True):
        send_ga4_event(
            "begin_checkout",
            {"currency": "USD", "value": 19.0,
             "items": [{"item_id":"single_checklist","item_name":"Single Checklist","price":19.0,"quantity":1}]},
            client_id=GA_CLIENT_ID,
        )
        open_checkout(LINK_19)

with col2:
    if st.button("📦 Checklist + PDF — $49", use_container_width=True):
        send_ga4_event(
            "begin_checkout",
            {"currency": "USD", "value": 49.0,
             "items": [{"item_id":"unlimited_30_days","item_name":"Unlimited 30 Days","price":49.0,"quantity":1}]},
            client_id=GA_CLIENT_ID,
        )
        open_checkout(LINK_49)

st.markdown("---")
st.caption("ImmigrAI is not a law firm and does not provide legal advice. This service offers informational checklists based on publicly available USCIS guidance.")
