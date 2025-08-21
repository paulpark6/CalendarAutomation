# streamlit_app/main.py
import streamlit as st
from project_code.auth import get_user_service, get_authenticated_email
import streamlit_app.ui as ui

def main():
    st.set_page_config(page_title="Calendar Automation", page_icon="📅", layout="wide")

    # ── Session defaults ────────────────────────────────────────────────────
    if "service" not in st.session_state:
        st.session_state.service = None
    if "user_email" not in st.session_state:
        st.session_state.user_email = None
    if "nav" not in st.session_state:
        st.session_state.nav = "Home"

    # ── Login gate ─────────────────────────────────────────────────────────
    if st.session_state.service is None:
        def on_login():
            service = get_user_service()
            st.session_state.service = service
            st.session_state.credentials = getattr(getattr(service, "_http", None), "credentials", None)
            # record the email once we have a service
            try:
                email = get_authenticated_email(service)
            except Exception:
                email = None
            st.session_state.user_email = email

        ui.show_login_page(on_login=on_login)
        return

    # ── Authenticated: show sidebar + pages ────────────────────────────────
    service = st.session_state.service
    if not st.session_state.user_email:
        # Backfill email if missing
        try:
            st.session_state.user_email = get_authenticated_email(service)
        except Exception:
            pass

    with st.sidebar:
        st.markdown("### 📚 Navigation")
        page = st.radio(
            label="",
            options=["Home", "Event Builder", "Settings"],
            index=["Home", "Event Builder", "Settings"].index(st.session_state.get("nav", "Home")),
        )
        st.session_state.nav = page

    if page == "Home":
        ui.show_home(service)
    elif page == "Event Builder":
        ui.show_event_builder(service)
    else:
        ui.show_settings(service)

if __name__ == "__main__":
    main()
