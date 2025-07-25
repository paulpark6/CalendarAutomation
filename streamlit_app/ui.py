# UI rendering functions for the Streamlit CalendarProject app.

# This module defines the main page components (Home, Bulk Upload, Chat Parser, Settings),
# using Streamlit to display and interact with Google Calendar data. All functions access
# user/session state via Streamlit's st.session_state.

import streamlit as st
from project_code.creating_calendar import get_or_create_calendar
from project_code.creating_calendar import load_recent_keys, load_user_input, create_schedule, save_recent_keys
import pandas as pd
from project_code.auth import get_user_service
import streamlit_app.calendar_utils as calendar_utils
import streamlit as st
from datetime import datetime, timedelta, timezone
from project_code.calendar_methods import create_event
from project_code.auth import get_default_calendar_timezone

def show_create_event(service):
    st.header("📅 Create a Calendar event")

    # --- basic input widgets ---
    title       = st.text_input("Title", "")
    description = st.text_area("Description", "")
    date        = st.date_input("Date", datetime.now().date())
    start_time  = st.time_input("Start time", datetime.now().time().replace(second=0, microsecond=0))
    end_time    = st.time_input("End time", (datetime.now() + timedelta(hours=1)).time().replace(second=0, microsecond=0))
    tz_default  = get_default_calendar_timezone(service)           # helper from timezone_helper.py
    timezone_id = st.text_input("Time-zone", tz_default)

    if_exists   = st.selectbox("If event already exists", ("skip", "update", "error"))
    notify      = st.selectbox("Send updates to guests", ("none", "externalOnly", "all"))

    # --- JIT build RFC-3339 strings ---
    start_iso = datetime.combine(date, start_time, tzinfo=timezone.utc).isoformat()
    end_iso   = datetime.combine(date, end_time,   tzinfo=timezone.utc).isoformat()

    if st.button("Create / Update"):
        try:
            event, status = create_event(
                service,
                calendar_id="primary",
                email=st.session_state["user"]["email"],
                title=title or "Untitled event",
                description=description,
                start_iso=start_iso,
                end_iso=end_iso,
                timezone_id=timezone_id,
                send_updates=notify,
                if_exists=if_exists,
            )

            link = event.get("htmlLink", "#")
            if status == "inserted":
                st.success(f"✅ Event created — [open]({link})")
            elif status == "duplicate_updated":
                st.success(f"♻️ Existing event updated — [open]({link})")
            else:
                st.info(f"ℹ️ Event already existed — [open]({link})")
        except ValueError as err:
            st.warning(str(err))
        except Exception as err:
            st.error(f"Google Calendar error: {err}")

# this function is used to get the service object from the session state
def get_service():
    """
    Retrieves the Google Calendar API service object from Streamlit's session state.

    Returns:
        service: The Google Calendar API service object stored in st.session_state["service"].
    Side Effects:
        Reads from st.session_state.
    """
    return st.session_state["service"]

def show_home(service, calendar_id):
    """
    Renders the Home page of the app, welcoming the user and displaying their calendar events.

    Parameters:
        None (uses session state for user and service).
    Side Effects:
        Reads 'user' from st.session_state.
        Calls list_events(user) to fetch events.
        Displays a dataframe of events in the UI.
    """
    st.header("🏠 Home")
    user = st.session_state.user
    st.write(f"Welcome, **{user['name']}**!")
    # Fetch user email and store in session state
    st.dataframe(calendar_utils.show_calendar(service, calendar_id))
    # TODO: Implement event listing using project_code logic
    st.info("Event listing coming soon.")


def show_bulk():
    """
    Renders the Bulk Upload page, allowing users to paste multiple events, parse them, preview, and create them in their calendar.

    Parameters:
        None (uses session state for user and service).
    Side Effects:
        Reads/writes to st.session_state.
        Displays text area, dataframes, and success messages in the UI.
        Calls parse_bulk and create_event for event creation.
    """
    st.header("📋 Bulk Upload")
    option = st.radio("Choose input method:", ["Paste dictionary", "Upload .txt file"])
    proceed = False
    if option == "Paste dictionary":
        text = st.text_area("Paste your event dictionary here (Python dict or JSON):")
        if st.button("Save and Create Events"):
            # Save the pasted text to user_input.txt
            with open("UserData/user_input.txt", "w") as f:
                f.write(text)
            st.success("Input saved to user_input.txt!")
            proceed = True
    elif option == "Upload .txt file":
        file = st.file_uploader("Upload a .txt file", type=["txt"])
        if file and st.button("Parse file and Create Events"):
            with open("UserData/user_input.txt", "wb") as f:
                f.write(file.read())
            st.success("File saved to user_input.txt!")
            proceed = True
    if proceed:
        # Use project_code logic to load, parse, and create events
        recent_keys_stack = load_recent_keys()
        service = st.session_state["service"]
        calendar_id = get_or_create_calendar(service)
        user_response = load_user_input()  # returns dict
        df_calendar = pd.DataFrame(user_response)
        recent_keys_stack = create_schedule(
            service,
            calendar_id,
            df_calendar,
            recent_keys_stack
        )
        save_recent_keys(recent_keys_stack)
        st.success("Events created and saved!")
        st.dataframe(df_calendar)

def show_chat():
    """
    Renders the Chat Parser page, allowing users to describe events in natural language and add them to their calendar via LLM parsing.

    Parameters:
        None (uses session state for user and service).
    Side Effects:
        Reads/writes to st.session_state.
        Displays chat input, JSON, and success messages in the UI.
        Calls parse_chat and create_event for event creation.
    """
    st.header("💬 Chat Parser")
    st.info("Chat-based event parsing coming soon.")

def show_settings():
    """
    Renders the Settings page, where users can configure app preferences and view/export session logs.

    Parameters:
        None (uses session state for user and service).
    Side Effects:
        Displays settings UI components in the Streamlit app.
    """
    service = get_service()
    st.header("⚙️ Settings")
    st.write("…your settings UI here…")
