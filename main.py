import os
import uuid
import requests
import streamlit as st

# ──────────────────────────────────────────────────────────────
# GA4 CONFIG (Measurement Protocol)
# Provide via Streamlit secrets or environment variables.
#   st.secrets["GA4_MEASUREMENT_ID"]
#   st.secrets["GA4_API_SECRET"]
#   -or-
#   os.environ["GA4_MEASUREMENT_ID"], os.environ["GA4_API_SECRET"]
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
    """Fire a GA4 event via Measurement Protocol."""
    if not GA4_ENDPOINT:
        # GA not configured; silently skip to avoid breaking UX
        return

    if client_id is None:
        client_id = str(uuid.uuid4())

    payload = {
        "client_id": client_id,
        "events": [
            {
                "name": name,
                "params": params or {},
            }
        ],
    }
    try:
        # MP returns 204 No Content on success
        requests.post(GA4_ENDPOINT, json=payload, timeout=3)
    except Exception:
        # Don't let analytics failures break the flow
        pass


# ──────────────────────────────────────────────────────────────
# PAGE SETUP
# ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="ImmigrAI – USCIS Checklist Generator", page_icon="🧾", layout="centered")

# HEADLINE (escape $ so Streamlit Markdown doesn't treat it as LaTeX)
st.markdown(
    """
# ImmigrAI: Smart USCIS Checklist Generator

Get your personalized immigration checklist in seconds. Free preview; **\\$19** for a single checklist or **\\$49** for unlimited 30 days.
"""
)

st.markdown("---")

# Example: your app logic for checklist generation goes here…
# st.subheader("Start here")
# ... gather inputs, generate preview, etc.

# ──────────────────────────────────────────────────────────────
# PAYWALL SECTION
# Replaces link buttons with real buttons so we reliably fire GA4 begin_checkout,
#   then immediately redirect to Stripe via meta refresh.
# ──────────────────────────────────────────────────────────────

# Stripe links (UPDATE THESE to your live links)
STRIPE_19 = "https://buy.stripe.com/your_live_link_for_19"
STRIPE_49 = "https://buy.stripe.com/your_live_link_for_49"

# stable client_id for GA across this Streamlit session
if "ga_client_id" not in st.session_state:
    st.session_state["ga_client_id"] = str(uuid.uuid4())
ga_client_id = st.session_state["ga_client_id"]

st.divider()
st.markdown("### 🔒 Unlock Your Full Checklist PDF")
st.write(
    "Choose your plan below to get your professionally formatted checklist PDF and email delivery."
)

col1, col2 = st.columns(2)

with col1:
    clicked_19 = st.button("💳 Get Checklist — $19", use_container_width=True)
    if clicked_19:
        send_ga4_event(
            "begin_checkout",
            {
                "currency": "USD",
                "value": 19.0,
                "items": [
                    {
                        "item_id": "single_checklist",
                        "item_name": "Single Checklist",
                        "price": 19.0,
                        "quantity": 1,
                    }
                ],
            },
            client_id=ga_client_id,
        )
        # Redirect to Stripe
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={STRIPE_19}">', unsafe_allow_html=True
        )

with col2:
    clicked_49 = st.button("📦 Checklist + PDF — $49", use_container_width=True)
    if clicked_49:
        send_ga4_event(
            "begin_checkout",
            {
                "currency": "USD",
                "value": 49.0,
                "items": [
                    {
                        "item_id": "unlimited_30_days",
                        "item_name": "Unlimited 30 Days",
                        "price": 49.0,
                        "quantity": 1,
                    }
                ],
            },
            client_id=ga_client_id,
        )
        # Redirect to Stripe
        st.markdown(
            f'<meta http-equiv="refresh" content="0; url={STRIPE_49}">', unsafe_allow_html=True
        )

st.markdown("---")
st.caption(
    "ImmigrAI is not a law firm and does not provide legal advice. "
    "This service offers informational checklists based on publicly available USCIS guidance."
)
