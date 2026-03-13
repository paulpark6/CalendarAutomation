# streamlit_app/ui.py
"""
Simplified Calendar Agent UI

PURPOSE: Provide a clean 2-step flow for calendar automation:
1. Select/Create/Edit calendar
2. Create events from pasted schedule

MAIN FUNCTIONS:
- show_login_page() -> Display Google Sign-In button
- step1_calendar_management() -> Calendar CRUD interface
- step2_event_creation() -> Event creation from text/paste
- render_app() -> Main app layout with both steps
"""

import streamlit as st
import datetime as dt
from project_code import calendar_creation, event_creation


# ============================================================================
# STEP 1: CALENDAR MANAGEMENT (Select/Create/Edit/Delete Calendar)
# ============================================================================

def show_login_page():
    """Display login page with Google Sign-In button only."""
    st.title("😪 LazyCal 🗓️")
    st.write("🔐 Sign in to connect your Google Calendar.")

    try:
        from project_code.auth import web_authorization_url
        
        cfg = st.secrets["google_oauth"]
        client_id = cfg["client_id"]
        client_secret = cfg["client_secret"]

        app_cfg = st.secrets["app"]
        redirect_uri = (
            app_cfg["local_redirect_uri"]
            if app_cfg.get("mode") == "local"
            else app_cfg["cloud_redirect_uri"]
        )

        auth_url, state = web_authorization_url(client_id, client_secret, redirect_uri)
        st.session_state["oauth_state"] = state

        st.link_button("Continue with Google", auth_url)
        st.caption("You will be redirected to Google to authorize access.")

    except Exception as e:
        st.error(f"Login config error: {e}")


def step1_calendar_management(service):
    """
    STEP 1: Calendar CRUD Interface
    Allow user to select, create, edit, or delete calendars.
    """
    st.header("Step 1: Select Your Calendar")
    
    # Show logged-in email
    user_email = st.session_state.get("user_email", "Unknown")
    st.caption(f"📧 Logged in as: **{user_email}**")
    
    # Get list of non-primary calendars
    if "calendars_cache" not in st.session_state:
        st.session_state["calendars_cache"] = calendar_creation.list_calendars(service, exclude_primary=True)
    
    calendars = st.session_state.get("calendars_cache", [])
    
    # Tabs for different operations
    tab1, tab2, tab3 = st.tabs(["📋 Select Calendar", "➕ Create New", "✏️ Edit/Delete"])
    
    # ─────────────────────────────────────────────────────────────
    # TAB 1: Select existing calendar
    # ─────────────────────────────────────────────────────────────
    with tab1:
        if not calendars:
            st.info("No calendars found. Create one in the '➕ Create New' tab.")
        else:
            cal_options = {c["id"]: c.get("summary", "Untitled") for c in calendars}
            
            selected_cal_id = st.selectbox(
                "Choose calendar for events",
                options=list(cal_options.keys()),
                format_func=lambda x: cal_options[x],
                key="calendar_selector"
            )
            
            st.session_state["target_calendar_id"] = selected_cal_id
            
            # Show selected calendar details
            selected_cal = next((c for c in calendars if c["id"] == selected_cal_id), None)
            if selected_cal:
                st.write("**Calendar Details:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**Summary:** {selected_cal.get('summary')}")
                    st.write(f"**Timezone:** {selected_cal.get('timeZone', 'UTC')}")
                with col2:
                    st.write(f"**Description:** {selected_cal.get('description', '(none)')}")
                    st.write(f"**Location:** {selected_cal.get('location', '(none)')}")
    
    # ─────────────────────────────────────────────────────────────
    # TAB 2: Create new calendar
    # ─────────────────────────────────────────────────────────────
    with tab2:
        st.subheader("Create New Calendar")
        
        with st.form("create_calendar_form"):
            cal_summary = st.text_input(
                "Calendar Title",
                placeholder="e.g., Work, Personal, Projects",
                help="Required. This is the name of your calendar."
            )
            
            cal_description = st.text_area(
                "Description",
                placeholder="What is this calendar for?",
                help="Optional. Describe the purpose of this calendar.",
                height=80
            )
            
            cal_location = st.text_input(
                "Location",
                placeholder="e.g., Office, Home",
                help="Optional. Geographic location associated with this calendar."
            )
            
            # Timezone selector (default to user's timezone)
            default_tz = calendar_creation.get_user_default_timezone(service)
            cal_timezone = st.text_input(
                "Timezone",
                value=default_tz,
                help=f"Default: {default_tz}. Use IANA timezone format (e.g., America/New_York)"
            )
            
            submitted = st.form_submit_button("✅ Create Calendar")
        
        if submitted:
            if not cal_summary.strip():
                st.error("Calendar title is required!")
            else:
                try:
                    created_cal = calendar_creation.create_calendar(
                        service,
                        summary=cal_summary,
                        description=cal_description,
                        time_zone=cal_timezone,
                        location=cal_location
                    )
                    
                    st.success(f"✅ Calendar '{cal_summary}' created!")
                    st.balloons()
                    
                    # Refresh cache
                    del st.session_state["calendars_cache"]
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Failed to create calendar: {e}")
    
    # ─────────────────────────────────────────────────────────────
    # TAB 3: Edit or Delete calendar
    # ─────────────────────────────────────────────────────────────
    with tab3:
        if not calendars:
            st.info("No calendars to edit. Create one first.")
        else:
            cal_options = {c["id"]: c.get("summary", "Untitled") for c in calendars}
            
            selected_for_edit = st.selectbox(
                "Select calendar to edit/delete",
                options=list(cal_options.keys()),
                format_func=lambda x: cal_options[x],
                key="edit_selector"
            )
            
            selected_cal_obj = next((c for c in calendars if c["id"] == selected_for_edit), None)
            
            if selected_cal_obj:
                st.write("**Current Values:**")
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"Summary: {selected_cal_obj.get('summary')}")
                    st.write(f"Timezone: {selected_cal_obj.get('timeZone')}")
                with col2:
                    st.write(f"Description: {selected_cal_obj.get('description', '(none)')}")
                    st.write(f"Location: {selected_cal_obj.get('location', '(none)')}")
            
            # Edit form
            st.subheader("Edit Calendar")
            with st.form("edit_calendar_form"):
                new_summary = st.text_input(
                    "Calendar Title",
                    value=selected_cal_obj.get("summary", ""),
                    key="edit_summary"
                )
                
                new_description = st.text_area(
                    "Description",
                    value=selected_cal_obj.get("description", ""),
                    key="edit_description",
                    height=80
                )
                
                new_location = st.text_input(
                    "Location",
                    value=selected_cal_obj.get("location", ""),
                    key="edit_location"
                )
                
                new_timezone = st.text_input(
                    "Timezone",
                    value=selected_cal_obj.get("timeZone", "UTC"),
                    key="edit_timezone"
                )
                
                edit_submitted = st.form_submit_button("💾 Save Changes")
            
            if edit_submitted:
                try:
                    calendar_creation.update_calendar(
                        service,
                        selected_for_edit,
                        summary=new_summary,
                        description=new_description,
                        time_zone=new_timezone,
                        location=new_location
                    )
                    st.success("✅ Calendar updated!")
                    del st.session_state["calendars_cache"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to update calendar: {e}")
            
            # Delete button (danger zone)
            st.divider()
            st.subheader("⚠️ Danger Zone")
            if st.button("🗑️ Delete This Calendar", type="secondary"):
                try:
                    result = calendar_creation.delete_calendar(service, selected_for_edit)
                    st.success(f"✅ Calendar {result['action']}!")
                    del st.session_state["calendars_cache"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to delete calendar: {e}")


# ============================================================================
# STEP 2: EVENT CREATION (Paste schedule, verify, apply)
# ============================================================================

def step2_event_creation(service):
    """
    STEP 2: Create events from pasted schedule text.
    User pastes output from Gemini/ChatGPT, verifies in table, then applies.
    """
    st.header("Step 2: Create Events")
    
    target_cal_id = st.session_state.get("target_calendar_id")
    if not target_cal_id:
        st.warning("⚠️ Please select a calendar in Step 1 first!")
        return
    
    st.write("Paste the schedule from Gemini or ChatGPT below:")
    
    # Instructions (collapsible)
    with st.expander("📖 How to prepare your schedule"):
        st.markdown("""
        1. Go to [Gemini Model](https://gemini.google.com/gem/18-IbkHbrqKkymmHJmirEUGfulE2BujaF?usp=sharing) or [ChatGPT Model](https://chatgpt.com/g/g-68b888b9f56481919ecd05f8c647130d-event-parser-assistant)
        2. Ask it to parse your schedule (e.g., email, document, text)
        3. Ask it to output as **JSON format** with fields: summary, start, end, description
        4. Copy the JSON output and paste it below
        5. Review the table and click "Apply Events"
        """)
    
    # Paste area
    schedule_text = st.text_area(
        "Paste JSON schedule here",
        placeholder='[{"summary": "Meeting", "start": "2026-03-15T10:00:00", "end": "2026-03-15T11:00:00", "description": ""}]',
        height=200
    )
    
    if schedule_text.strip():
        try:
            import json
            events = json.loads(schedule_text)
            
            # Ensure it's a list
            if not isinstance(events, list):
                events = [events]
            
            st.write(f"**Found {len(events)} event(s)**")
            
            # Show verification table
            st.subheader("Verify Events")
            for i, event in enumerate(events):
                with st.expander(f"Event {i+1}: {event.get('summary', 'No title')}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Title:** {event.get('summary', '')}")
                        st.write(f"**Start:** {event.get('start', '')}")
                    with col2:
                        st.write(f"**End:** {event.get('end', '')}")
                        st.write(f"**Description:** {event.get('description', '')}")
            
            # Apply button
            if st.button("✅ Apply All Events", type="primary"):
                progress = st.progress(0)
                success_count = 0
                
                for i, event in enumerate(events):
                    try:
                        result = event_creation.create_event(
                            service,
                            target_cal_id,
                            event,
                            dedupe=True
                        )
                        success_count += 1
                    except Exception as e:
                        st.warning(f"Failed to create '{event.get('summary')}': {e}")
                    
                    progress.progress((i + 1) / len(events))
                
                st.success(f"✅ Created {success_count}/{len(events)} events!")
                st.balloons()
        
        except json.JSONDecodeError:
            st.error("❌ Invalid JSON. Please paste valid JSON format.")
        except Exception as e:
            st.error(f"Error: {e}")


# ============================================================================
# MAIN APP LAYOUT
# ============================================================================

def render_app(service):
    """Main app layout with Step 1 and Step 2."""
    #st.set_page_config(page_title="LazyCal - Calendar Agent", page_icon="📅", layout="wide")
    
    # Header with logout
    col1, col2 = st.columns([0.85, 0.15])
    with col1:
        st.title("📅 Calendar Agent")
    with col2:
        if st.button("Log out"):
            from project_code.auth import logout_and_delete_token
            logout_and_delete_token(st.session_state.get("credentials"))
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()
    
    st.divider()
    
    # Two steps in columns
    col1, col2 = st.columns([0.5, 0.5], gap="large")
    
    with col1:
        step1_calendar_management(service)
    
    with col2:
        step2_event_creation(service)