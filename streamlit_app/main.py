import streamlit as st
from project_code.auth import get_user_service
import streamlit_app.ui as ui  # your new UI layer

def main():
# ─── 1) Initialize session keys ─────────────────────────────────────────────
    if "service" not in st.session_state:
        st.session_state.service = None

    # ─── 2) Show login page if we don't yet have a service ─────────────────────
    if st.session_state.service is None:
        st.title("🔐 Please sign in with Google")
        st.write("This app uses your Google Calendar. Click below to authenticate.")
        if st.button("Continue with Google"):
            # This will open the local-server flow in your browser
            service = get_user_service()
            st.session_state.service = service
            st.rerun()
        st.stop()
    
    # ─── 3) At this point, we have `service` in session_state ───────────────────
    service = st.session_state.service

    # ─── 4) Sidebar navigation ──────────────────────────────────────────────────
    st.sidebar.title("Navigate")
    page = st.sidebar.radio("Go to", ["Home", "Bulk Upload", "Chat Parser", "Settings"])

    # ─── 5) Page dispatch ───────────────────────────────────────────────────────
    if page == "Home":
        ui.show_home()
    elif page == "Bulk Upload":
        ui.show_bulk()
    elif page == "Chat Parser":
        ui.show_chat()
    else:
        ui.show_settings()