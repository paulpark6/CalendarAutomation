import streamlit as st
import datetime as dt
import pandas as pd
import json
import concurrent.futures
from streamlit_calendar import calendar
from project_code import calendar_creation
from project_code import event_creation
from project_code import auth

# --- Constants & Types ---
MODE_DAY = "timeGridDay"
MODE_WEEK = "timeGridWeek"
MODE_MONTH = "dayGridMonth"

# --- 1. State Management ---

def init_session_state(service):
    """Initialize all session state variables required by the spec."""
    # Backend Caches
    if "calendars_cache" not in st.session_state:
        st.session_state["calendars_cache"] = calendar_creation.list_calendars(service)
    
    # Selection State
    if "target_calendar_id" not in st.session_state:
        cals = st.session_state["calendars_cache"]
        primary = next((c['id'] for c in cals if c.get('primary')), cals[0]['id'] if cals else 'primary')
        st.session_state["target_calendar_id"] = primary
        
    if "visible_calendars" not in st.session_state:
        # Default: All Calendars
        st.session_state["visible_calendars"] = [c['id'] for c in st.session_state["calendars_cache"]]

    # Event Lifecycle State
    if "draft_events" not in st.session_state:
        st.session_state["draft_events"] = []  # List[Dict] (Parsed but not saved)

    if "draft_history" not in st.session_state:
        st.session_state["draft_history"] = [] # List[List[Dict]] (History of draft_events versions)
        
    if "created_events_log" not in st.session_state:
        st.session_state["created_events_log"] = [] # Log of successful creations for current session
        
    if "undo_stack" not in st.session_state:
        st.session_state["undo_stack"] = [] # List[List[str]] (Batches of event IDs)

    # View State
    if "calendar_view_mode" not in st.session_state:
        st.session_state["calendar_view_mode"] = MODE_WEEK
    
    if "calendar_focus_date" not in st.session_state:
        st.session_state["calendar_focus_date"] = dt.date.today().isoformat()

# --- 2. Helper Functions ---

def _get_calendar_by_id(cal_id):
    for c in st.session_state.get("calendars_cache", []):
        if c['id'] == cal_id:
            return c
    return {"id": cal_id, "summary": "Unknown"}

def _save_draft_checkpoint():
    """Save current state of drafts to history before modification."""
    import copy
    current = st.session_state.get("draft_events", [])
    # Limit history to 20 items
    history = st.session_state.get("draft_history", [])
    history.append(copy.deepcopy(current))
    if len(history) > 20:
        history.pop(0)
    st.session_state["draft_history"] = history

def _undo_last_draft_import():
    """Restore draft_events from last checkpoint."""
    history = st.session_state.get("draft_history", [])
    if history:
        previous = history.pop()
        st.session_state["draft_events"] = previous
        st.session_state["draft_history"] = history
        st.toast("↩️ Undid last import!")
        st.rerun()
    else:
        st.warning("Nothing to undo.")

def _parse_drafts_dummy(text):
    """Mock LLM Parser for now."""
    # Try to parse as JSON first (User might paste LLM output)
    try:
        data = json.loads(text)
        
        # Helper to map fields
        def map_event(item):
            # Start with a copy of everything (Pass-through)
            event = item.copy()
            
            # 1. Title/Summary Normalization
            if "summary" not in event:
                event["summary"] = event.get("title", "New Event")
            
            # 2. Description Normalization
            if "description" not in event:
                event["description"] = ""

            # 3. Time Logic
            # Start/End logic
            start_dt = None
            end_dt = None
            
            # A. Standard Google API format
            if "start" in item and "dateTime" in item["start"]:
                start_dt = item["start"]["dateTime"]
                end_dt = item["end"]["dateTime"]
            # B. Flattened format (event_date + event_time)
            elif "event_date" in item and "event_time" in item:
                # Naive combine
                s_str = f"{item['event_date']}T{item['event_time']}:00"
                # Default duration 1h
                start_obj = dt.datetime.fromisoformat(s_str)
                end_obj = start_obj + dt.timedelta(hours=1)
                
                # Check for explicit end time/date
                if "end_time" in item:
                     # Same date, specific time
                     # Assuming end_date is same if not provided
                     e_date = item.get("end_date", item["event_date"])
                     e_str = f"{e_date}T{item['end_time']}:00"
                     end_obj = dt.datetime.fromisoformat(e_str)
                elif "end_date" in item:
                     # All day or specific logic? 
                     # For now just default 1h if time not match
                     pass

                start_dt = start_obj.isoformat()
                end_dt = end_obj.isoformat()
            else:
                # Fallback to now
                start_obj = dt.datetime.now().replace(minute=0, second=0) + dt.timedelta(hours=1)
                start_dt = start_obj.isoformat()
                end_dt = (start_obj + dt.timedelta(hours=1)).isoformat()

            # Set standard start/end
            event["start"] = {"dateTime": start_dt}
            event["end"] = {"dateTime": end_dt}
            
            # 4. Cleanup Helper Fields (Don't send these to Google)
            details_keys = ["title", "event_date", "event_time", "end_date", "end_time", "invitees"]
            for k in details_keys:
                if k in event:
                    del event[k]
            
            return event

        if isinstance(data, list):
            return [map_event(x) for x in data]
        elif isinstance(data, dict):
            return [map_event(data)]
            
    except Exception:
        pass # Not JSON, fall back to simple text

    # Fallback and Manual Entry logic
    start_dt = dt.datetime.now().replace(minute=0, second=0, microsecond=0) + dt.timedelta(hours=1)
    end_dt = start_dt + dt.timedelta(hours=1)
    
    return [{
        "summary": text, 
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
        "description": "" 
    }]

@st.cache_data(ttl=600, show_spinner=False)
def _fetch_events_for_calendar(_creds, calendar_id, t_min, t_max):
    """Cached helper to fetch events. Rebuilds service for thread safety."""
    # Note: We do NOT use try-except here. If it fails (Rate Limit), we want it to RAISE
    # so that Streamlit does NOT cache the failure as an empty list.
    service = auth.build_calendar_service(_creds)
    
    resp = service.events().list(
        calendarId=calendar_id, timeMin=t_min, timeMax=t_max, 
        singleEvents=True, maxResults=100
    ).execute()
    return resp.get("items", [])

def _apply_drafts(service):
    """Commit drafts to Google Calendar."""
    drafts = st.session_state["draft_events"]
    target_id = st.session_state["target_calendar_id"]
    
    new_ids = []
    
    progress = st.progress(0)
    for i, event in enumerate(drafts):
        try:
            # Create
            res = event_creation.create_event(service, target_id, event, dedupe=True)
            if res.get('created') or res.get('status') == 'updated':
                new_ids.append(res['event_id'])
                # Log to session
                st.session_state["created_events_log"].append({
                    "id": res['event_id'], 
                    "summary": event.get("summary"), 
                    "status": "success",
                    "timestamp": dt.datetime.now().isoformat()
                })
        except Exception as e:
            st.error(f"Failed to create {event.get('summary')}: {e}")
        progress.progress((i + 1) / len(drafts))
        
    # Push batch to undo stack
    if new_ids:
        st.session_state["undo_stack"].append({"calendar_id": target_id, "event_ids": new_ids})
        st.toast(f"✅ Applied {len(new_ids)} events!")
    
    # Clear drafts
    st.session_state["draft_events"] = []
    st.rerun()

def _undo_last_batch(service):
    if not st.session_state["undo_stack"]:
        st.warning("Nothing to undo.")
        return
        
    batch = st.session_state["undo_stack"].pop()
    cal_id = batch["calendar_id"]
    ids = batch["event_ids"]
    
    count = 0
    for eid in ids:
        try:
            event_creation.delete_event(service, cal_id, eid)
            count += 1
        except Exception:
            pass
            
    st.toast(f"Refreshed! Undid {count} events.")
    st.rerun()


def show_login_page():
    """Renders the login page content (without logic)."""
    st.title("😪 LazyCal 🗓️")
    st.write("🔐 Sign in to connect your Google Calendar.")
    
    # The actual Auth URL generation and Button logic was in main.py
    # But now main.py expects this function to do IT.
    # We need client_id/secret to generate the link.
    try:
        cfg = st.secrets["google_oauth"]
        client_id = cfg["client_id"]
        client_secret = cfg["client_secret"]
        
        # Dynamic redirect URI based on mode
        app_cfg = st.secrets.get("app", {})
        redirect_uri = (
            app_cfg.get("local_redirect_uri", "http://localhost:8501/")
            if app_cfg.get("mode", "local") == "local"
            else app_cfg.get("cloud_redirect_uri", "https://lazycal.streamlit.app/")
        )
        
        auth_url, state = auth.web_authorization_url(client_id, client_secret, redirect_uri)
    
        st.markdown(
            f'''
            <a href="{auth_url}" target="_self" style="
                display: inline-block;
                background-color: #ff4b4b;
                color: white;
                padding: 0.5rem 1rem;
                text-decoration: none;
                border-radius: 0.5rem;
                font-weight: 600;
            ">
            Continue with Google
            </a>
            ''',
            unsafe_allow_html=True
        )
        st.caption("You will be redirected to Google to authorize access.")
        
    except Exception as e:
        st.error(f"Missing secrets configuration: {e}")

# --- 3. Panel Components ---

def render_chat_column(service):
    """Left Panel: Agent Interaction & Sidebar Management"""
    # 1. Sidebar
    # render_calendar_management(service) # Moved to Center
    
    # 2. Main Area
    st.subheader("Agent Control")
    
    # A. Input Modes
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📋 Paste", "TB Upload"])
    
    with tab1:
        prompt = st.chat_input("Schedule a meeting with...")
        if prompt:
            # Checkpoint
            _save_draft_checkpoint()
            # Mock Parsing Logic
            drafts = _parse_drafts_dummy(prompt)
            st.session_state["draft_events"].extend(drafts)
            st.toast(f"Parsed {len(drafts)} events!")
            
    with tab2:
        text = st.text_area("Paste schedule text")
        
        st.markdown("""
        **Prompt-Engineered Models:**
        You can use either Gemini or ChatGPT to generate the schedule text!
        For more information, you can ask the models "How do I use you?"
        - [Gemini Model](https://gemini.google.com/gem/18-IbkHbrqKkymmHJmirEUGfulE2BujaF?usp=sharing)
        - [ChatGPT Model](https://chatgpt.com/g/g-68b888b9f56481919ecd05f8c647130d-event-parser-assistant)
        """)

        if st.button("Parse Text"):
            # Checkpoint
            _save_draft_checkpoint()
            drafts = _parse_drafts_dummy(text)
            st.session_state["draft_events"].extend(drafts)
            
    with tab3:
        st.info("File upload coming soon.")

    st.divider()
    st.caption("Drafts will appear below after parsing.\nYou can check the events before applying by scrolling down!")

    # 3. Manage Calendars (Moved from Center)
    st.divider()
    st.subheader("Manage Projects")
    
    if "calendars_cache" not in st.session_state:
        st.session_state["calendars_cache"] = calendar_creation.list_calendars(service)
    cals = st.session_state["calendars_cache"]
    
    # A. Create
    with st.expander("Create New Calendar"):
        new_cal_name = st.text_input("Name", placeholder="e.g. Work Project")
        if st.button("Create Calendar"):
            if new_cal_name:
                try:
                    calendar_creation.create_calendar(service, summary=new_cal_name)
                    st.toast(f"✅ Created: {new_cal_name}")
                    # Force refresh
                    del st.session_state["calendars_cache"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
            else:
                st.warning("Please enter a name.")

    # B. Edit / Delete
    with st.expander("Edit / Delete"):
        # Filter out primary/readonly for safety
        editable_cals = [c for c in cals if not c.get('primary')]
        if not editable_cals:
            st.info("No editable calendars found.")
        else:
            cal_map = {c['id']: c.get('summary', 'Untitled') for c in editable_cals}
            selected_edit_id = st.selectbox(
                "Select Calendar", 
                options=list(cal_map.keys()),
                format_func=lambda x: cal_map[x]
            )
            
            # Rename
            current_name = cal_map.get(selected_edit_id, "")
            new_name = st.text_input("Rename to", value=current_name)
            if st.button("Save Name"):
                if new_name and new_name != current_name:
                    try:
                        calendar_creation.update_calendar(service, selected_edit_id, summary=new_name)
                        st.toast(f"✅ Renamed to {new_name}")
                         # Force refresh
                        del st.session_state["calendars_cache"]
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
            
            st.write("---")
            # Delete
            st.warning("Danger Zone")
            if st.button("Delete Calendar", type="primary", key="del_cal_btn"):
                try:
                    calendar_creation.delete_calendar(service, selected_edit_id)
                    st.toast(f"🗑️ Deleted {current_name}")
                     # Force refresh
                    del st.session_state["calendars_cache"]
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

def render_event_loader_section(service):
    """Bottom Section: Draft Editing & Loader"""
    
    # Drafts Table (Editable)
    st.markdown("### Drafts (Review before applying)")
    
    col_add, _ = st.columns([0.2, 0.8])
    with col_add:
        if st.button("➕ Add Empty Draft"):
            start_dt = dt.datetime.now().replace(minute=0, second=0) + dt.timedelta(hours=1)
            st.session_state["draft_events"].append({
                "summary": "New Event",
                "start": {"dateTime": start_dt.isoformat()},
                "end": {"dateTime": (start_dt + dt.timedelta(hours=1)).isoformat()},
                "description": ""
            })
            st.rerun()
    
    drafts = st.session_state["draft_events"]
    if not drafts:
        st.caption("No pending drafts. Chat or paste to begin, or click Add.")
        return

    # Convert to Dataframe for editing
    # We allow editing: Summary, Start, End
    df = pd.DataFrame(drafts)
    
    # Rename 'summary' -> 'title' for UI consistency with user's JSON
    df = df.rename(columns={"summary": "title"})
    
    # Ensure columns exist
    # Determine all potential keys from drafts
    all_keys = set()
    for d in drafts:
        all_keys.update(d.keys())
        
    # Standard keys management
    if "summary" in all_keys: all_keys.remove("summary")
    if "start" in all_keys: all_keys.remove("start")
    if "end" in all_keys: all_keys.remove("end")
    if "description" in all_keys: all_keys.remove("description")
    
    # Base columns
    cols = ["title", "start", "end", "description"]
    # Sorting extra keys
    extra_keys = sorted(list(all_keys))
    
    # Ensure all exist in DF
    for c in cols + extra_keys:
        if c not in df.columns:
            df[c] = None
            
    # Flatten start/end for table (just datetime strings)
    # handle dicts if they exist
    def get_dt(x):
        if isinstance(x, dict): return x.get("dateTime", "")
        return x
    
    df["start"] = df["start"].apply(get_dt)
    df["end"] = df["end"].apply(get_dt)

    # Determine which columns to show
    # Always show basic ones
    show_cols = ["title", "start", "end", "description"]
    
    # Add extra columns ONLY if non-empty
    for k in extra_keys:
        # Check if column has any truthy value (and not all None/NaN)
        if df[k].notna().any() and df[k].astype(str).str.strip().ne("").any():
             show_cols.append(k)
    
    edited_df = st.data_editor(
        df[show_cols],
        num_rows="dynamic",
        use_container_width=True,
        key="draft_editor"
    )
    
    # Actions
    c1, c2, c3 = st.columns([0.4, 0.3, 0.3])
    with c1:
        if st.button("✅ Apply Changes", type="primary"):
            # Update drafts from editor
            updated_drafts = []
            for _, row in edited_df.iterrows():
                # Base Object
                evt = {
                    "summary": row["title"], # Map back
                    "start": {"dateTime": row["start"]},
                    "end": {"dateTime": row["end"]},
                    "description": row["description"]
                }
                # Add back extra fields
                for k in extra_keys:
                    if k in row and row[k]: # Only if value exists
                        evt[k] = row[k]
                
                updated_drafts.append(evt)

            # Checkpoint before applying? 
            # Actually, applying CLEARS drafts, so we might want to checkpoint to restore if needed?
            # But the user logic is 'Apply' moves to Calendar. 
            # The 'Undo Apply' handles the calendar side.
            # So here we just proceed.
            st.session_state["draft_events"] = updated_drafts
            _apply_drafts(service)
            st.rerun()
            
    with c2:
        # Undo Import (Draft Level)
        # Show if history exists
        if st.session_state.get("draft_history"):
            if st.button("↩️ Undo Import"):
                _undo_last_draft_import()
        else:
            st.button("↩️ Undo Import", disabled=True)

    with c3:
        if st.button("🗑️ Discard All"):
            # Checkpoint before clear? Yes.
            _save_draft_checkpoint()
            st.session_state["draft_events"] = []
            st.rerun()
        
    # C. Undo / History (Calendar Level)
    st.divider()
    
    # Always show, disabled if empty
    has_undo = bool(st.session_state.get("undo_stack"))
    if st.button("↩️ Undo Last Apply (Calendar)", disabled=not has_undo):
        _undo_last_batch(service)


# --- 3b. Unified Calendar Manager ---

def _handle_calendar_changes(service, editor_state):
    """Sync changes from data_editor to Google Calendar API."""
    if "calendars_cache" not in st.session_state:
        st.session_state["calendars_cache"] = calendar_creation.list_calendars(service)
    cache = st.session_state["calendars_cache"]
    
    edited_rows = editor_state["edited_rows"]
    deleted_rows = editor_state["deleted_rows"]
    added_rows = editor_state["added_rows"]
    
    refresh_needed = False
    
    # 1. Handle Creates (added_rows)
    for new_row in added_rows:
        summary = new_row.get("summary", "New Calendar")
        try:
            # Create new calendar
            calendar_creation.create_calendar(service, summary=summary)
            st.toast(f"✅ Created calendar: {summary}")
            refresh_needed = True
        except Exception as e:
            st.error(f"Create failed: {e}")

    # 2. Handle Deletes
    # Map deletions to IDs before cache might change? 
    # Actually checking cache[idx] is safe as long as we don't mutate cache in-loop.
    for idx in deleted_rows:
        if idx >= len(cache): continue # Safety for added rows interactions
        
        cal = cache[idx]
        if cal.get('primary'):
            st.toast("⚠️ Cannot delete Primary calendar!", icon="❌")
            continue
        # Also protect holiday/readonly calendars if possible? 
        # Usually checking 'accessRole' is better, but for now we trust 'primary' check.
            
        try:
            calendar_creation.delete_calendar(service, cal['id'])
            st.toast(f"🗑️ Deleted {cal.get('summary')}")
            refresh_needed = True
        except Exception as e:
            st.error(f"Delete failed: {e}")

    # 3. Handle Edits (Renames / Visibility)
    for idx, changes in edited_rows.items():
        if idx >= len(cache): continue
        
        cal = cache[idx]
        
        # A. Rename
        if "summary" in changes:
            new_summ = changes["summary"]
            # Protect Primary from Rename? User request: "dont let user edit default calendars"
            if cal.get('primary') or "holiday" in cal.get('id', '').lower():
                st.toast(f"⚠️ Cannot rename default/primary calendar: {cal.get('summary')}", icon="XY")
            elif new_summ != cal["summary"]:
                try:
                    calendar_creation.update_calendar(service, cal['id'], summary=new_summ)
                    st.toast(f"✏️ Renamed to {new_summ}")
                    refresh_needed = True
                except Exception as e:
                    st.error(f"Rename failed: {e}")
        
        # B. Visibility (State only)
        if "visible" in changes:
            is_vis = changes["visible"]
            current_vis = st.session_state["visible_calendars"]
            cid = cal['id']
            
            if is_vis and cid not in current_vis:
                current_vis.append(cid)
            elif not is_vis and cid in current_vis:
                st.session_state["visible_calendars"] = [c for c in current_vis if c != cid]
            
    if refresh_needed:
        st.session_state["calendars_cache"] = calendar_creation.list_calendars(service)
        st.rerun()

def render_unified_calendar_controls(service):
    """Combined: Target Selection, Visibility, Edit, Delete"""
    if "calendars_cache" not in st.session_state:
        st.session_state["calendars_cache"] = calendar_creation.list_calendars(service)
    cals = st.session_state.get("calendars_cache", [])
    
    # 1. Target Selector
    cal_options = {c['id']: c.get('summary', 'Untitled') for c in cals}
    current_target = st.session_state.get("target_calendar_id")
    if current_target not in cal_options and cal_options:
        current_target = next(iter(cal_options))
        
    new_target = st.selectbox(
        "🖊️ Write Target (Where new events go)", 
        options=list(cal_options.keys()),
        format_func=lambda x: cal_options[x],
        key="target_cal_input",
        index=list(cal_options.keys()).index(current_target) if current_target in cal_options else 0
    )
    st.session_state["target_calendar_id"] = new_target
    
    # Warning if default calendar
    selected_cal_obj = next((c for c in cals if c['id'] == new_target), None)
    if selected_cal_obj and selected_cal_obj.get('primary'):
        st.warning("⚠️ You are adding events to your main default calendar.")

    # Refresh Button
    if st.button("🔄 Refresh Calendar"):
        # Clearing cache forces a re-fetch
        if "calendars_cache" in st.session_state:
            del st.session_state["calendars_cache"]
        st.rerun()

    # 2. Manager Grid (Removed)
    # Moved to Left Column under 'Manage Projects'


def render_calendar_column(service):
    """Center Panel: Calendar Visualization"""
    
    # A. Unified Controls
    render_unified_calendar_controls(service)
    
    # B. Calendar Grid
    # Define 'target' (fix NameError)
    target = st.session_state.get("target_calendar_id")
    
    # 1. Fetch Real Events (Aggregated + Parallelized)
    calendar_events = []
    
    # Time window
    days_window = 180 
 

    now = dt.datetime.utcnow()
    t_min = (now - dt.timedelta(days=days_window)).isoformat() + "Z"
    t_max = (now + dt.timedelta(days=days_window)).isoformat() + "Z"
    
    visible_cals = st.session_state["visible_calendars"]
    
    if visible_cals:
        creds = st.session_state.get("credentials")
        if creds:
            try:
                # Thread-safe Parallel Fetching
                with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                    # We pass 'creds' (thread-safe copy usually) instead of 'service'
                    future_to_cid = {
                        executor.submit(_fetch_events_for_calendar, creds, cid, t_min, t_max): cid 
                        for cid in visible_cals
                    }
                    
                    for future in concurrent.futures.as_completed(future_to_cid):
                        cid = future_to_cid[future]
                        try:
                            items = future.result()
                            color = "#3788d8" if cid == target else "#999999"
                            
                            for item in items:
                                calendar_events.append({
                                    "title": item.get("summary", "(No Title)"),
                                    "start": item.get("start").get("dateTime") or item.get("start").get("date"),
                                    "end": item.get("end").get("dateTime") or item.get("end").get("date"),
                                    "backgroundColor": color,
                                    "borderColor": color,
                                    "id": item.get("id"),
                                    "extendedProps": {"calendarId": cid}
                                })
                        except Exception as e:
                            # Catch invalid_grant (Token Revoked)
                            err_str = str(e)
                            if "invalid_grant" in err_str or "Token has been expired" in err_str:
                                st.error(f"Access Token Expired for {cid}. Please Log out and Log in again.")
                                if st.button("Re-login Now", key=f"relogin_{cid}"):
                                    # Force logout
                                    for k in list(st.session_state.keys()):
                                        del st.session_state[k]
                                    st.rerun()
                            # Rate limits
                            elif "Quota exceeded" in err_str:
                                st.toast(f"Rate limit hit for {cid}. Slowing down...", icon="⚠️")
                            elif "Not Found" in err_str or "404" in err_str:
                                st.toast(f"Calendar check failed: {cid} not found. removing...", icon="🧹")
                                # Remove from visible
                                if cid in st.session_state["visible_calendars"]:
                                    st.session_state["visible_calendars"].remove(cid)
                                # Remove from cache
                                if "calendars_cache" in st.session_state:
                                    st.session_state["calendars_cache"] = [c for c in st.session_state["calendars_cache"] if c['id'] != cid]
                                st.rerun()
                            else:
                                print(f"Error fetching {cid}: {e}")
            except Exception as e:
                st.error(f"Fetch error: {e}")
            
    # 2. Add Draft Events (Ghost State)
    for draft in st.session_state["draft_events"]:
        calendar_events.append({
            "title": f"[DRAFT] {draft.get('summary')}",
            "start": draft.get("start").get("dateTime"),
            "end": draft.get("end").get("dateTime"),
            "backgroundColor": "#ffbd45", # Orange for drafts
            "borderColor": "#ffbd45",
            "className": "fc-event-draft" # CSS hook?
        })

    # Render
    calendar_options = {
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": "dayGridMonth,timeGridWeek,timeGridDay,listYear"
        },
        "initialView": "dayGridMonth",
        "navLinks": True,
        "selectable": True,
        "editable": False, # Just view for now
    }
    
    st.markdown("### Calendar View")
    calendar(events=calendar_events, options=calendar_options, key="main_calendar")


def render_right_column(service):
    """Right Panel: List View"""
    st.subheader("Upcoming Events")
    
    # 1. View Toggles
    view_mode = st.radio(
        "Time Range", 
        ["Next 2 Weeks", "This Month"], 
        horizontal=True, 
        label_visibility="collapsed"
    )
    
    # 2. Filters
    with st.expander("Filter & Sort", expanded=True):
        f_col1, f_col2 = st.columns(2)
        with f_col1:
             # Calendar Filter
             if "calendars_cache" not in st.session_state:
                st.session_state["calendars_cache"] = calendar_creation.list_calendars(service)
             cals = st.session_state["calendars_cache"]
             # Visible ones only? or logic all?
             # User said: "By default select calendar to all"
             cal_opts = {"all": "All Calendars"}
             visible_ids = st.session_state.get("visible_calendars", [])
             for c in cals:
                 if c['id'] in visible_ids:
                     cal_opts[c['id']] = c.get('summary', 'Untitled')
             
             selected_cal_filter = st.selectbox(
                 "Calendar", 
                 options=list(cal_opts.keys()), 
                 format_func=lambda x: cal_opts[x]
             )
        
        with f_col2:
            # Sort
            sort_opt = st.selectbox(
                "Sort by",
                ["Start Time (Earliest)", "Start Time (Latest)", "Title (A-Z)"]
            )

        # Date Filter & Text Search
        c1, c2 = st.columns([0.4, 0.6])
        with c1:
             filter_date = st.date_input("Specific Date", value=None)
        with c2:
             search_term = st.text_input("Search", placeholder="Title or Description...", help="Press Enter")
    
    # 3. Calculate Date Range
    now = dt.datetime.now()
    if view_mode == "Next 2 Weeks":
        t_max = now + dt.timedelta(days=14)
    else:
        # End of current month
        # Logic: First day of next month - 1 day
        next_month = now.replace(day=28) + dt.timedelta(days=4)
        t_max = next_month - dt.timedelta(days=next_month.day - 1)
        # If we are already at end of month, maybe show next month? 
        # User asked "current months onwards", usually implies "remainder of this month".
        # If today is Jan 30, "This Month" is just 1 day. 
        # Let's handle edge case: if near end of month (days < 7), extend to next month?
        # For simplicity/strictness: End of current month. 
        # Actually user said "all events in current months onwards from today". 
        # Let's stick to strict "End of this month" for now as requested.
        
    t_min_iso = now.isoformat() + "Z"
    t_max_iso = t_max.replace(hour=23, minute=59, second=59).isoformat() + "Z"
    
    # 4. Fetch Events (Visible Calendars)
    # We can reuse the cached fetch logic, but we need to collate them.
    visible_cals = st.session_state.get("visible_calendars", [])
    if "calendars_cache" not in st.session_state:
        st.session_state["calendars_cache"] = calendar_creation.list_calendars(service)
    
    # Map ID to Name/Color/Primary
    cal_meta = {c['id']: c for c in st.session_state["calendars_cache"]}
    
    all_events = []
    
    if visible_cals:
        # Reuse the cached fetcher? 
        # _fetch_events_for_calendar is cached.
        # But we need to call it.
        creds = st.session_state.get("credentials")
        if creds:
             with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
                future_to_cid = {
                    executor.submit(_fetch_events_for_calendar, creds, cid, t_min_iso, t_max_iso): cid 
                    for cid in visible_cals
                }
                for future in concurrent.futures.as_completed(future_to_cid):
                    cid = future_to_cid[future]
                    try:
                        items = future.result()
                        for item in items:
                            # Parse Start
                            start = item.get("start", {})
                            dt_str = start.get("dateTime") or start.get("date")
                            if not dt_str: continue
                            
                            # Flatten for display
                            all_events.append({
                                "id": item.get("id"),
                                "summary": item.get("summary", "(No Title)"),
                                "start_raw": dt_str,
                                "calendar_id": cid,
                                "htmlLine": item.get("htmlLink")
                            })
                    except Exception:
                        pass

    # 5. Filter & Sort
    
    # A. Search (Title OR Description)
    if search_term:
        term = search_term.lower()
        all_events = [
            e for e in all_events 
            if term in e["summary"].lower() or term in e.get("description", "").lower()
        ]
    
    # B. Calendar Filter
    if selected_cal_filter != "all":
        all_events = [e for e in all_events if e["calendar_id"] == selected_cal_filter]
        
    # C. Date Filter
    if filter_date:
        # Filter by start date
        # start_raw can be ISO datetime string OR date string (YYYY-MM-DD)
        filtered_by_date = []
        for e in all_events:
            raw = e["start_raw"]
            try:
                if "T" in raw:
                    e_date = dt.datetime.fromisoformat(raw).date()
                else:
                    e_date = dt.date.fromisoformat(raw)
                
                if e_date == filter_date:
                    filtered_by_date.append(e)
            except:
                pass
        all_events = filtered_by_date

    # D. Sort
    if sort_opt == "Start Time (Earliest)":
        all_events.sort(key=lambda x: x["start_raw"])
    elif sort_opt == "Start Time (Latest)":
        all_events.sort(key=lambda x: x["start_raw"], reverse=True)
    elif sort_opt == "Title (A-Z)":
        all_events.sort(key=lambda x: x["summary"].lower())
    
    # 6. Display
    if not all_events:
        st.info("No upcoming events found.")
    else:
        # Fixed height for scrollable area (matching calendar ~600px)
        with st.container(height=600):
            for e in all_events:
                # Format Time
                raw = e["start_raw"]
                try:
                    if "T" in raw:
                        dt_obj = dt.datetime.fromisoformat(raw)
                        date_str = dt_obj.strftime("%a, %b %d")
                        time_str = dt_obj.strftime("%I:%M %p")
                    else:
                        # All day
                        dt_obj = dt.date.fromisoformat(raw) 
                        date_str = dt_obj.strftime("%a, %b %d")
                        time_str = "All Day"
                except:
                    date_str = raw
                    time_str = ""
                
                cal_obj = cal_meta.get(e["calendar_id"], {})
                cal_name = cal_obj.get("summary", "Unknown")
                # Try to distinguish calendars visually (e.g. bold name)
                
                with st.container(border=True):
                    # Row 1: Title
                    st.markdown(f"**{e['summary']}**")
                    # Row 2: Date
                    st.caption(f"📅 {date_str} • {time_str}")
                    # Row 3: Calendar Badge
                    st.markdown(f"Correction: *from* **`{cal_name}`**")

    st.divider()
    st.write("#### Session Activity")
    log = st.session_state.get("created_events_log", [])
    if log:
        for entry in reversed(log[-10:]): # Last 10
            icon = "✅" if entry['status'] == 'success' else "❌"
            st.caption(f"{icon} {entry['summary']}")
    else:
        st.caption("No events created this session.")


# --- 3b. Management Components ---

def render_calendar_management(service):
    """Deprecated: Replaced by render_unified_calendar_controls in Center Column."""
    pass

# --- 4. Main Render ---

# --- 4. Main Render (Obsolete) ---
# render_app removed as main.py handles layout directly.
