# main.py
import os
import uuid
import requests
import streamlit as st
from datetime import datetime

# ──────────────────────────────────────────────────────────────
# GA4 CONFIG (Measurement Protocol)
# Provide via Streamlit secrets or environment variables.
#   st.secrets["GA4_MEASUREMENT_ID"]
#   st.secrets["GA4_API_SECRET"]
# ──────────────────────────────────────────────────────────────
GA4_MEASUREMENT_ID = (
    st.secrets.get("GA4_MEASUREMENT_ID")
    if "GA4_MEASUREMENT_ID" in st.secrets
    else os.getenv("GA4_MEASUREMENT_ID", "")
)
GA4_API_SECRET = (
    st.secrets.get("GA4_API_SECRET")
    if "GA4_API_SECRET" in st.secrets
    else os.getenv("GA4_API_SECRET", "")
)
GA4_ENDPOINT = (
    f"https://www.google-analytics.com/mp/collect?measurement_id={GA4_MEASUREMENT_ID}&api_secret={GA4_API_SECRET}"
    if GA4_MEASUREMENT_ID and GA4_API_SECRET
    else ""
)

def send_ga4_event(name: str, params: dict | None = None, client_id: str | None = None) -> None:
    """Fire a GA4 event via the Measurement Protocol (safe/no-throw)."""
    if not GA4_ENDPOINT:
        return
    if client_id is None:
        client_id = str(uuid.uuid4())
    payload = {
        "client_id": client_id,
        "events": [{"name": name, "params": params or {}}],
    }
    try:
        requests.post(GA4_ENDPOINT, json=payload, timeout=3)
    except Exception:
        pass

# One stable GA client id per Streamlit session
if "ga_client_id" not in st.session_state:
    st.session_state["ga_client_id"] = str(uuid.uuid4())
GA_CLIENT_ID = st.session_state["ga_client_id"]

# ──────────────────────────────────────────────────────────────
# PAGE SETUP
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="ImmigrAI – USCIS Checklist Generator",
    page_icon="🧾",
    layout="centered",
)
st.markdown(
    """
# ImmigrAI: Smart USCIS Checklist Generator

Get your personalized immigration checklist in seconds. Free preview; **\\$19** for a single checklist or **\\$49** for unlimited 30 days.
"""
)
st.markdown("---")

# ──────────────────────────────────────────────────────────────
# INPUTS & PREVIEW GENERATOR
# Simple rules-based preview so users always get instant results.
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
            [
                "I-130 (Petition for Alien Relative)",
                "I-485 (Adjustment of Status)",
                "I-129F (K-1 fiancé(e))",
                "N-400 (Naturalization)",
            ],
        )
        is_spouse = st.selectbox("Is the beneficiary your spouse?", ["No", "Yes"])
    relation_notes = st.text_area(
        "Anything else we should consider?",
        placeholder="Prior marriages, name changes, joint lease, etc.",
    )

    submitted = st.form_submit_button("Generate free preview")
    if submitted:
        # Fire a GA4 event that a preview started (optional but useful)
        send_ga4_event(
            "generate_checklist_started",
            {
                "form_type": form_type,
                "spouse": is_spouse.lower() == "yes",
            },
            client_id=GA_CLIENT_ID,
        )

        # Very light rules-based preview
        base = [
            ("Government ID", "Photo ID for each applicant (passport or driver’s license)."),
            ("Filing Fee Payment", "Check or money order; verify current fee on USCIS.gov."),
            ("USCIS Forms", "Complete & sign the latest USCIS version."),
        ]

        if form_type.startswith("I-130"):
            items = [
                ("Form I-130", "Petition for Alien Relative (latest USCIS version)."),
                ("Proof of Petitioner Status", "US citizenship or LPR evidence (passport, naturalization cert, green card)."),
                ("Marriage Certificate", "If petitioning a spouse."),
                ("Proof of Relationship", "Joint bank statements, lease/mortgage, photos, affidavits."),
            ]
        elif form_type.startswith("I-485"):
            items = [
                ("Form I-485", "Application to Register Permanent Residence or Adjust Status."),
                ("Two Passport Photos", "2x2 inches, white background."),
                ("I-693 (Medical)", "In sealed envelope from civil surgeon (if required)."),
                ("I-864 (Affidavit of Support)", "If needed based on category."),
            ]
        elif form_type.startswith("I-129F"):
            items = [
                ("Form I-129F", "Petition for Alien Fiancé(e)."),
                ("Proof of Meeting", "Evidence you met in person within 2 years (itineraries, photos, receipts)."),
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

        # Save preview into session so we can show + email later
        st.session_state["preview_items"] = base + items
        st.session_state["full_name"] = full_name.strip()
        st.session_state["email"] = email.strip()
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
            # You can swap this log for a webhook or email service call.
            st.session_state["email"] = email_now.strip()
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
# PAYWALL SECTION
# Only fires GA4 begin_checkout when the actual button is clicked.
# ──────────────────────────────────────────────────────────────
st.divider()
st.markdown("### 🔒 Unlock Your Full Checklist PDF")
st.write("Choose your plan to receive your professionally formatted checklist PDF and email delivery.")

# TODO: replace with your real Stripe links
STRIPE_19 = "https://buy.stripe.com/dRmfZiccndJ52px6sR4wM01"
STRIPE_49 = "https://buy.stripe.com/cNi28sccn34rggn2cB4wM02"

col1, col2 = st.columns(2)
with col1:
    go19 = st.button("💳 Get Checklist — $19", use_container_width=True)
    if go19:
        send_ga4_event(
            "begin_checkout",
            {
                "currency": "USD",
                "value": 19.0,
                "items": [
                    {"item_id": "single_checklist", "item_name": "Single Checklist", "price": 19.0, "quantity": 1}
                ],
            },
            client_id=GA_CLIENT_ID,
        )
        st.markdown(f'<meta http-equiv="refresh" content="0; url={STRIPE_19}">', unsafe_allow_html=True)

with col2:
    go49 = st.button("📦 Checklist + PDF — $49", use_container_width=True)
    if go49:
        send_ga4_event(
            "begin_checkout",
            {
                "currency": "USD",
                "value": 49.0,
                "items": [
                    {"item_id": "unlimited_30_days", "item_name": "Unlimited 30 Days", "price": 49.0, "quantity": 1}
                ],
            },
            client_id=GA_CLIENT_ID,
        )
        st.markdown(f'<meta http-equiv="refresh" content="0; url={STRIPE_49}">', unsafe_allow_html=True)

st.markdown("---")
st.caption(
    "ImmigrAI is not a law firm and does not provide legal advice. "
    "This service offers informational checklists based on publicly available USCIS guidance."
)
