# streamlit_app/ui.py
import json
import datetime as dt
from typing import List, Dict, Any

import math
import pandas as pd
import streamlit as st

# External helpers you said exist in project_code/*
from project_code import calendar_methods as cal
from project_code import creating_calendar as create_mod
from google.auth.transport.requests import AuthorizedSession
from pathlib import Path
from google.oauth2.credentials import Credentials


def _patch_calendar_timezone(service, calendar_id: str, tz: str) -> None:
    sess = _authed_session_from_service(service)
    sess.patch(f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}",
               json={"timeZone": tz}, timeout=15).raise_for_status()



def _authed_session_from_service(service):
    # 1) Preferred: creds we saved at login
    creds = st.session_state.get("credentials")

    # 2) Fallback: creds attached to the discovery client's HTTP adapter
    if creds is None:
        creds = getattr(getattr(service, "_http", None), "credentials", None)

    # 3) Last-chance fallback: load token file (same path as auth.py)
    if creds is None:
        token_path = Path("UserData/token.json")
        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), ["https://www.googleapis.com/auth/calendar"])
            st.session_state.credentials = creds  # cache for the rest of the session

    # 4) If still nothing, fail with a clear error
    if creds is None:
        raise RuntimeError("Google credentials not found in session. Please sign in again.")

    return AuthorizedSession(creds)

def _user_default_timezone(service) -> str:
    """Return the user's default Google Calendar timezone (fallbacks to primary cal tz, then UTC)."""
    sess = _authed_session_from_service(service)

    # Preferred: settings API (works with calendar scope)
    try:
        r = sess.get("https://www.googleapis.com/calendar/v3/users/me/settings/timezone", timeout=15)
        r.raise_for_status()
        tz = (r.json() or {}).get("value")
        if tz:
            return tz
    except Exception:
        pass

    # Fallback: timeZone of the primary calendar from the calendarList
    try:
        for c in _get_calendars_cached(service):
            if c.get("primary") and c.get("timeZone"):
                return c["timeZone"]
    except Exception:
        pass

    return "UTC"

def _create_calendar_safe(service, name: str, time_zone: str | None = None) -> str:
    """Create a calendar with `summary=name` and the given (or user default) time zone; return its ID."""
    sess = _authed_session_from_service(service)
    tz = time_zone or _user_default_timezone(service)
    payload = {"summary": name, "timeZone": tz}
    r = sess.post("https://www.googleapis.com/calendar/v3/calendars", json=payload, timeout=30)
    r.raise_for_status()
    return r.json()["id"]

def _calendar_label(cal: dict) -> str:
    return f"{cal.get('summary', cal['id'])} · {cal['id']}"


def _refresh_calendars(service):
    """
    Fetches the list of calendars for the current user from Google Calendar,
    updates the Streamlit session state with the latest list, and ensures
    that the currently 'active' calendar is still valid.

    Purpose:
    - To keep the user's calendar list in sync with Google and maintain a valid active calendar selection.
    """

    # Call a helper function to retrieve the list of calendars from Google Calendar API.
    # This function uses a requests-based approach for robustness.
    cals = _list_calendars_safe(service)

    # Store the fetched list of calendars in Streamlit's session state under the key "calendars".
    # This allows other parts of the app to access the up-to-date calendar list without refetching.
    st.session_state["calendars"] = cals

    # Check if the currently selected "active_calendar" is still present in the new list.
    # If not (for example, if it was deleted), reset "active_calendar" to the first calendar in the list.
    if cals and not any(c["id"] == st.session_state.get("active_calendar") for c in cals):
        st.session_state["active_calendar"] = cals[0]["id"]

    # Return the list of calendars so the caller can use it immediately if needed.
    return cals

def _get_calendars_cached(service):
    """Return cached calendars if present, otherwise load."""
    if "calendars" not in st.session_state:
        return _refresh_calendars(service)
    return st.session_state["calendars"]

def _calendar_name_for_id(cal_id: str) -> str:
    cals = st.session_state.get("calendars", [])
    for c in cals:
        if c["id"] == cal_id:
            return c.get("summary", cal_id)
    return cal_id


def _init_session_defaults():
    st.session_state.setdefault("undo_stack", [])
    st.session_state.setdefault("usage_stats", {"events_added": 0, "last_action": "—"})
    st.session_state.setdefault("parsed_events_df", pd.DataFrame())
    st.session_state.setdefault("active_calendar", "primary")
    st.session_state.setdefault("llm_enabled", False)
    st.session_state.setdefault("billing_ok", False)

def _success(msg: str):
    # record last action
    st.session_state["usage_stats"]["last_action"] = msg
    # show this success only if it's different from the last one
    if st.session_state.get("_last_notice") == ("success", msg):
        return
    st.session_state["_last_notice"] = ("success", msg)
    st.success(msg)

def _error(msg: str):
    st.session_state["usage_stats"]["last_action"] = f"Error: {msg}"
    # show this error only if it's different from the last one
    if st.session_state.get("_last_notice") == ("error", msg):
        return
    st.session_state["_last_notice"] = ("error", msg)
    st.error(msg)

# ──────────────────────────────────────────────────────────────────────────────
# Login page

def show_login_page(on_login=None, error_message=None):
    st.title("🔐 Please sign in with Google")
    if error_message:
        st.error(error_message)
    if st.button("Continue with Google", type="primary"):
        if on_login:
            on_login()

# ──────────────────────────────────────────────────────────────────────────────
# Home


def _list_calendars_safe(service) -> list[dict]:
    """
    Retrieve a list of Google Calendars accessible to the user via the Google Calendar API.

    Returns:
        A list of dictionaries, each representing a calendar with the following keys:
            - id: The unique calendar ID.
            - summary: The display name of the calendar.
            - accessRole: The user's access level (e.g., owner, writer, reader).
            - primary: Boolean indicating if this is the user's primary calendar.

    How it works:
    -------------
    1. Uses the authenticated session from the provided Google API service object.
    2. Sets the API endpoint to the Google Calendar 'calendarList' endpoint.
    3. Initializes an empty output list (`out`) and a pagination token (`token`).
    4. Enters a loop to fetch all calendar pages (Google may paginate results).
        a. Sets request parameters, including a maximum of 250 results per page.
        b. If a pagination token exists, adds it to the request parameters to fetch the next page.
        c. Makes a GET request to the API endpoint with the current parameters.
        d. Raises an exception if the request fails (ensures errors are not silently ignored).
        e. Parses the JSON response.
        f. Iterates over each calendar item in the response:
            - Extracts the calendar's id, summary (name), accessRole, and primary status.
            - Appends a dictionary with these fields to the output list.
        g. Checks for a 'nextPageToken' in the response:
            - If present, sets `token` to this value to fetch the next page in the next loop iteration.
            - If not present, breaks the loop (all calendars have been fetched).
    5. Returns the complete list of calendar dictionaries.

    Notes:
        - This function uses direct HTTP requests (requests transport) instead of the Google API client library's built-in methods.
        - Handles pagination to ensure all calendars are retrieved, not just the first page.
        - Only includes selected fields for each calendar for simplicity and efficiency.
    """
    # Get an authenticated HTTP session from the Google API service.
    sess = _authed_session_from_service(service)
    # Google Calendar API endpoint for listing user's calendars.
    url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
    out = []    # List to accumulate calendar info dictionaries.
    token = None  # Pagination token for fetching additional pages.

    while True:
        # Prepare request parameters. maxResults=250 is the API's upper limit per page.
        params = {"maxResults": 250}
        if token:
            # If a nextPageToken exists, include it to fetch the next page.
            params["pageToken"] = token
        # Make the GET request to the API endpoint.
        r = sess.get(url, params=params, timeout=30)
        # Raise an exception if the request failed (e.g., network error, auth error).
        r.raise_for_status()
        # Parse the JSON response.
        data = r.json()
        # Iterate over each calendar in the response.
        for it in data.get("items", []):
            out.append({
                "id": it["id"],
                "summary": it.get("summary", it["id"]),
                "accessRole": it.get("accessRole"),
                "primary": it.get("primary", False),
                "timeZone": it.get("timeZone"),     # ← NEW
            })
        # Check if there is another page of results.
        token = data.get("nextPageToken")
        if not token:
            # No more pages; break the loop.
            break
    # Return the complete list of calendar info dictionaries.
    return out
def _calendar_timezone_for_id(cal_id: str) -> str:
    for c in st.session_state.get("calendars", []):
        if c["id"] == cal_id:
            return (c.get("timeZone") or "").strip()
    return ""

def _fetch_upcoming_events(service, calendar_id: str, max_count: int = 50) -> List[Dict[str, Any]]:
    now_iso = dt.datetime.utcnow().isoformat() + "Z"
    resp = service.events().list(
        calendarId=calendar_id,
        timeMin=now_iso,
        singleEvents=True,
        orderBy="startTime",
        maxResults=max_count,
        fields="items(id,summary,start,end,description,location)"
    ).execute()
    return resp.get("items", [])

def _events_to_df(items: List[Dict[str, Any]]) -> pd.DataFrame:
    rows = []
    for it in items:
        start = it.get("start", {})
        end = it.get("end", {})
        rows.append({
            "event_id": it.get("id"),
            "title": it.get("summary"),
            "start": start.get("dateTime") or start.get("date"),
            "end": end.get("dateTime") or end.get("date"),
            "location": it.get("location"),
            "description": it.get("description"),
        })
    return pd.DataFrame(rows)

def show_home(service):
    _init_session_defaults()

    user = st.session_state.get("user_email") or "Unknown user"
    st.title("📅 Calendar Automation")
    st.caption("Google Calendar • paste / upload • optional LLM parsing • undo batches")

    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            user = st.session_state.get("user_email") or "Unknown user"
            active_id = st.session_state.get("active_calendar", "primary")
            active_name = _calendar_name_for_id(active_id)

            st.markdown(
                f"**Signed in as:** `{user}`  \n"
                f"**Active calendar:** `{active_name}` · `{active_id}`"
            )
            st.markdown("### How it works")
            st.markdown(
                "- Choose an input mode: structured paste, `.txt` upload, or natural language (LLM).\n"
                "- Preview and edit events in a table before creating.\n"
                "- Create events in a single batch.\n"
                "- Undo the last batch if needed."
            )
        with c2:
            stats = st.session_state["usage_stats"]
            st.metric("Events added (this session)", stats["events_added"])
            st.caption(f"Last action: {stats['last_action']}")

    st.divider()
    st.subheader("Your calendars")
    calendars = _get_calendars_cached(service)
    if calendars:
        ids = [c["id"] for c in calendars]
        labels = [_calendar_label(c) for c in calendars]
        try:
            idx = ids.index(st.session_state["active_calendar"])
        except ValueError:
            idx = 0
        choice = st.selectbox(
            "Select a calendar",
            options=list(range(len(ids))),
            format_func=lambda i: labels[i],
            index=idx
        )
        st.session_state["active_calendar"] = ids[choice]
    else:
        st.info("No calendars found. Use Event Builder to create one.")

    with st.expander("Create a new calendar"):
        new_name = st.text_input("Calendar name", placeholder="My Automated Calendar")
        if st.button("Create / ensure", key="ensure_calendar_btn"):
            try:
                existing = _get_calendars_cached(service)
                match = next((c for c in existing if c.get("summary") == new_name), None)
                if match:
                    cal_id = match["id"]
                    want_tz = _user_default_timezone(service)
                    if match.get("timeZone") != want_tz:
                        try:
                            _patch_calendar_timezone(service, cal_id, want_tz)
                        except Exception:
                            # non-fatal; user may lack permission or Google may reject patch
                            pass
                else:
                    cal_id = _create_calendar_safe(service, new_name, time_zone=_user_default_timezone(service))
                _refresh_calendars(service)
                st.session_state["active_calendar"] = cal_id
                _success(f"Calendar ready: `{new_name}` · `{cal_id}`")
            except Exception as e:
                _error(f"Failed to create/ensure calendar: {e}")
    st.subheader("Upcoming events")
    try:
        items = _fetch_upcoming_events(service, st.session_state["active_calendar"], max_count=50)
        df = _events_to_df(items)
        if df.empty:
            st.caption("No upcoming events.")
        else:
            st.dataframe(df, use_container_width=True, height=360)
            st.caption("Tip: delete-on-hover will be added later.")
    except Exception as e:
        _error(f"Failed to load events: {e}")

    st.divider()
    if st.button("🧱 Open Event Builder", type="primary"):
        st.session_state["nav"] = "Event Builder"

# ──────────────────────────────────────────────────────────────────────────────
# Event Builder

def _coerce_root_to_list(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return [obj]
    raise ValueError("JSON must be a list of dicts or a single dict.")

def _load_json_into_preview(raw_text: str):
    """Lenient ingest: accept list or single dict; on any JSON error, just show an error banner."""
    if not raw_text or not raw_text.strip():
        _error("Paste JSON first.")
        return
    try:
        data = json.loads(raw_text)
        records = _coerce_root_to_list(data)
        df = pd.DataFrame(records)
        if df.empty:
            _error("No records found in JSON.")
            return
        st.session_state["parsed_events_df"] = df
        _success(f"Loaded {len(df)} record(s) into preview.")
    except Exception as e:
        _error(f"Invalid JSON: {e}")

def _undo_last_batch(service):
    if not st.session_state["undo_stack"]:
        _error("Nothing to undo.")
        return

    batch = st.session_state["undo_stack"].pop()
    ids = batch["ids"] if isinstance(batch, dict) else list(batch)  # backward-compat
    cal_id = batch.get("calendar_id", st.session_state.get("active_calendar", "primary")) if isinstance(batch, dict) else st.session_state.get("active_calendar", "primary")

    try:
        # Delete remote events
        for eid in ids:
            service.events().delete(calendarId=cal_id, eventId=eid, sendUpdates="none").execute()

        # Also pop the local mirror if present & decrement stats
        if st.session_state.get("created_batches"):
            st.session_state["created_batches"].pop()

        st.session_state["usage_stats"]["events_added"] = max(0, st.session_state["usage_stats"]["events_added"] - len(ids))
        _success(f"Deleted {len(ids)} event(s).")
    except Exception as e:
        _error(f"Undo failed: {e}")

# --- All-day normalizer helpers ---
def _plus_one(date_str: str) -> str:
    """Return YYYY-MM-DD + 1 day (Google all-day end is exclusive)."""
    try:
        return (dt.date.fromisoformat(date_str) + dt.timedelta(days=1)).isoformat()
    except Exception:
        return date_str

def _normalize_all_day_rows(rows: list[dict]) -> list[dict]:
    """
    If event_time is blank/missing ⇒ treat as all-day:
      - event_time = ""
      - timezone = ""  (backend ignores tz for date-only)
      - end_date defaults to event_date (backend will add +1 exclusive end)
    """
    out = []
    for r in rows:
        rr = dict(r)
        t = (rr.get("event_time") or "").strip()
        d = (rr.get("event_date") or "").strip()
        if not t and d:
            rr["event_time"] = ""
            rr["timezone"] = ""
            if not (rr.get("end_date") or "").strip():
                rr["end_date"] = d
        out.append(rr)
    return out


def _str_or_empty(x) -> str:
    """Return a trimmed string; '' for None/NaN."""
    if isinstance(x, str):
        return x.strip()
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    # keep lists/dicts as-is elsewhere; this helper is only used for string-like fields
    return str(x).strip()

def _sanitize_rows(rows: list[dict]) -> list[dict]:
    """Fix common issues from edited DataFrame rows."""
    out = []
    for r in rows:
        rr = dict(r)

        # 1) Fix the common typo key: 'location:' -> 'location'
        if "location:" in rr and "location" not in rr:
            rr["location"] = rr.pop("location:") or ""

        # 2) Coerce string-like fields to strings (avoid .strip() on NaN/None/float)
        for k in ["title", "description", "calendar_id", "event_date", "event_time",
                  "end_date", "timezone", "location", "recurrence"]:
            if k in rr:
                rr[k] = _str_or_empty(rr.get(k))

        # 3) Ensure list-typed fields are lists (avoid NaN there too)
        if not isinstance(rr.get("notifications"), list):
            rr["notifications"] = [] if rr.get("notifications") in (None, "", float("nan")) else rr.get("notifications") or []
        if not isinstance(rr.get("invitees"), list):
            rr["invitees"] = [] if rr.get("invitees") in (None, "", float("nan")) else rr.get("invitees") or []

        out.append(rr)
    return out

def _normalize_all_day_rows(rows: list[dict]) -> list[dict]:
    """
    If event_time is blank -> all-day:
      - event_time = ''
      - timezone   = '' (ignored by backend for date-only)
      - end_date defaults to event_date (backend will add +1 exclusive end)
    """
    out = []
    for r in rows:
        rr = dict(r)
        t = _str_or_empty(rr.get("event_time"))
        d = _str_or_empty(rr.get("event_date"))
        if not t and d:
            rr["event_time"] = ""
            rr["timezone"] = ""
            if not _str_or_empty(rr.get("end_date")):
                rr["end_date"] = d
        out.append(rr)
    return out

def _apply_default_tz_for_timed(rows: list[dict], cal_tz: str) -> list[dict]:
    """For rows with a time, default timezone to the selected calendar's tz when missing."""
    cal_tz = _str_or_empty(cal_tz)
    if not cal_tz:
        return rows
    out = []
    for r in rows:
        rr = dict(r)
        t = _str_or_empty(rr.get("event_time"))
        tz = _str_or_empty(rr.get("timezone"))
        if t and not tz:
            rr["timezone"] = cal_tz
        out.append(rr)
    return out

def _calendar_timezone_for_id(cal_id: str) -> str:
    for c in st.session_state.get("calendars", []):
        if c["id"] == cal_id:
            return _str_or_empty(c.get("timeZone"))
    return ""


def _create_events_batch(service, df: pd.DataFrame):
    if df is None or df.empty:
        _error("Load records first.")
        return

    email = st.session_state.get("user_email") or "unknown@example.com"
    target_cal = st.session_state.get("active_calendar") or "primary"

    rows = df.to_dict(orient="records")

    # 1) Sanitize (fix NaN/None, remap location:, coerce lists)
    rows = _sanitize_rows(rows)

    # 2) Normalize all-day rows (no tz, end_date defaults to event_date)
    rows = _normalize_all_day_rows(rows)

    # 3) Default tz for timed rows to the calendar tz
    cal_tz = _calendar_timezone_for_id(target_cal)
    rows = _apply_default_tz_for_timed(rows, cal_tz)

    created_ids: List[str] = []

    # If you still have a bulk path, you can keep it for fully timed rows;
    # otherwise route everything through the single creator for consistency.
    has_all_day = any(not _str_or_empty(r.get("event_time")) for r in rows) is False
    used_bulk = False
    if has_all_day:  # i.e., NO all-day rows present -> safe to try bulk first
        try:
            results = cal.create_calendar_events(
                service,
                email=email,
                events=rows,
                calendar_id=target_cal,
                if_exists="skip",
                send_updates="none"
            )
            for ev, _status in results:
                ev_id = ev.get("id")
                if ev_id:
                    created_ids.append(ev_id)
            used_bulk = True
        except Exception:
            used_bulk = False  # fall back to single-row path

    if not used_bulk:
        try:
            for r in rows:
                created = create_mod.create_single_event(
                    service=service,
                    calendar_id=r.get("google_calendar_id") or r.get("calendar_id") or target_cal,
                    title=r.get("title") or "Untitled",
                    description=r.get("description") or "",
                    event_date=r.get("event_date") or "",
                    event_time=r.get("event_time") or "",
                    end_date=r.get("end_date") or r.get("event_date") or "",
                    timezone=r.get("timezone") or "",
                    notifications=r.get("notifications") or [],
                    invitees=r.get("invitees") or [],
                    location=r.get("location", ""),
                    recurrence=r.get("recurrence"),
                    user_email=email,
                    send_updates="none",
                )
                ev_id = created.get("id")
                if ev_id:
                    created_ids.append(ev_id)
        except Exception as e_single:
            _error(f"Failed to create events: {e_single}")
            return

    if not created_ids:
        _error("No events were created.")
        return

    batch = {"ids": created_ids, "calendar_id": target_cal}
    st.session_state["undo_stack"].append(batch)
    st.session_state.setdefault("created_batches", [])
    st.session_state["created_batches"].append({"ids": created_ids, "calendar_id": target_cal, "rows": rows})
    st.session_state["usage_stats"]["events_added"] += len(created_ids)
    _success(f"Created {len(created_ids)} event(s) in `{target_cal}`.")


def _to_streamlit_editable(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """Convert list/dict cells to JSON strings so st.data_editor can edit/hash them safely."""
    editable = df.copy()
    json_cols: list[str] = []
    for c in editable.columns:
        if editable[c].map(lambda v: isinstance(v, (list, dict))).any():
            json_cols.append(c)
            editable[c] = editable[c].map(
                lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
            )
    return editable, json_cols

def _from_streamlit_editable(edited: pd.DataFrame, json_cols: list[str]) -> pd.DataFrame:
    """Parse JSON strings back to list/dict for the columns we serialized."""
    parsed = edited.copy()
    for c in json_cols:
        if c in parsed.columns:
            def _maybe_json(x):
                if isinstance(x, str):
                    s = x.strip()
                    if (s.startswith('[') and s.endswith(']')) or (s.startswith('{') and s.endswith('}')):
                        try:
                            return json.loads(s)
                        except Exception:
                            return x
                return x
            parsed[c] = parsed[c].map(_maybe_json)
    return parsed

def _init_session_defaults():
    st.session_state.setdefault("undo_stack", [])  # will hold dicts: {"ids":[...], "calendar_id": "..."}
    st.session_state.setdefault("created_batches", [])  # mirror of undo stack with source rows if you want to show later
    st.session_state.setdefault("usage_stats", {"events_added": 0, "last_action": "—"})
    st.session_state.setdefault("parsed_events_df", pd.DataFrame())
    st.session_state.setdefault("active_calendar", "primary")
    st.session_state.setdefault("llm_enabled", False)
    st.session_state.setdefault("billing_ok", False)


def show_event_builder(service):
    _init_session_defaults()
    st.title("🧱 Event Builder")
    st.caption("Paste, upload, or describe your events. Preview, edit, and create in one place.")

    # Calendar target + ensure
    with st.container(border=True):
        calendars = _get_calendars_cached(service)
        ids = [c["id"] for c in calendars] or ["primary"]
        labels = [_calendar_label(c) for c in calendars] or ["primary"]

        try:
            idx = ids.index(st.session_state["active_calendar"])
        except ValueError:
            idx = 0

        choice = st.selectbox(
            "Target calendar",
            options=list(range(len(ids))),
            format_func=lambda i: labels[i],
            index=idx,
            key="evb_cal_select",  # <-- make unique to Event Builder
        )
        st.session_state["active_calendar"] = ids[choice]

        new_name = st.text_input(
            "Create new calendar (optional)",
            placeholder="My Automated Calendar",
            key="evb_new_cal_name",  # <-- unique
        )
        if st.button("Create / ensure calendar", key="evb_create_cal_btn"):  # <-- unique
            try:
                existing = _get_calendars_cached(service)
                match = next((c for c in existing if c.get("summary") == new_name), None)
                if match:
                    cal_id = match["id"]
                else:
                    cal_id = _create_calendar_safe(service, new_name)

                _refresh_calendars(service)                 # refresh dropdown cache
                st.session_state["active_calendar"] = cal_id
                _success(f"Calendar ready: `{new_name}` · `{cal_id}`")
            except Exception as e:
                _error(f"Failed: {e}")

        st.toggle("Enable LLM parsing (billing applies)", key="evb_llm_enabled")  # <-- unique

    tab1, tab2, tab3 = st.tabs(["Structured paste", "Upload .txt", "Natural Language (LLM)"])

    with tab1:
        st.markdown("**Paste event records** as JSON (list of dicts or a single dict).")
        example = [{
            "title": "Sample Event",
            "event_date": dt.date.today().isoformat(),
            "description": "Optional",
            "calendar_id": "primary",
            "event_time": "10:00",
            "end_date": dt.date.today().isoformat(),
            "timezone": "",
            "notifications": [],
            "invitees": [],
            "location": "", # Optional
            "recurrence": "" # NEW (e.g., "RRULE:FREQ=WEEKLY;COUNT=8")
        }]
        st.caption("Tip: omit `event_time` to create an **all-day** event. Set `recurrence` like `RRULE:FREQ=WEEKLY;COUNT=8`.")
        st.code(json.dumps(example, indent=2), language="json")
        raw = st.text_area("Paste here", height=220, placeholder="[\n  {...}\n]", key="evb_paste")  # unique
        if st.button("Parse pasted JSON", key="evb_parse_paste"):  # unique
            _load_json_into_preview(raw)

    with tab2:
        up = st.file_uploader("Upload a .txt containing JSON", type=["txt"], key="evb_uploader")  # unique
        if up is not None and st.button("Parse uploaded file", key="evb_parse_upload"):  # unique
            try:
                raw = up.read().decode("utf-8")
                _load_json_into_preview(raw)
            except Exception as e:
                _error(f"Failed to read file: {e}")

    with tab3:
        st.markdown("Describe your events in plain English (stubbed for now).")
        st.info('Example: "Study group Monday 7–8pm at DC Library; Coffee with Maya Tue 9:30am."')
        nl = st.text_area("Your description", height=140, key="evb_nl")  # unique
        st.checkbox("I agree to pay for LLM parsing.", key="evb_billing_ok")  # unique
        if st.button("Generate structured events with LLM", key="evb_generate_llm"):  # unique
            if not st.session_state["evb_llm_enabled"]:
                _error("Enable LLM parsing first.")
            elif not st.session_state["evb_billing_ok"]:
                _error("Please agree to pay for LLM parsing.")
            elif not nl.strip():
                _error("Please enter a description.")
            else:
                _error("LLM parsing is not enabled yet. (Stub)")

    st.divider()
    st.subheader("Preview & edit")

    if st.session_state["parsed_events_df"].empty:
        st.caption("No records loaded yet.")
    else:
        # Build a display copy without internal columns
        display_df = st.session_state["parsed_events_df"].copy()
        for col in ["service", "google_calendar_id", "calendar_name", "user_email", "calendar_id"]:
            if col in display_df.columns:
                display_df = display_df.drop(columns=[col])

        selected_id = st.session_state.get("active_calendar", "primary")
        st.caption(f"Selected calendar: `{_calendar_name_for_id(selected_id)}` · `{selected_id}`")

        # Streamlit-only editable grid; JSON-safe for list/dict cells
        editable_df, json_cols = _to_streamlit_editable(display_df)
        edited = st.data_editor(
            editable_df,
            use_container_width=True,
            height=360,
            num_rows="dynamic",
            key="evb_editor"
        )
        edited = _from_streamlit_editable(edited, json_cols)

        # Sync back ONLY the editable columns
        base_df = st.session_state["parsed_events_df"]
        for col in edited.columns:
            if col == "target_calendar":
                continue
            if col in base_df.columns:
                base_df[col] = edited[col]
        st.session_state["parsed_events_df"] = base_df

        # Actions
        c1, c2 = st.columns(2)
        with c1:
            if st.button("🚀 Create events", key="evb_create_events"):
                df_to_create = st.session_state["parsed_events_df"].copy()
                if "calendar_id" not in df_to_create.columns:
                    df_to_create["calendar_id"] = selected_id
                else:
                    df_to_create["calendar_id"] = df_to_create["calendar_id"].fillna("").replace("", selected_id)
                _create_events_batch(service, df_to_create)
        with c2:
            if st.button("🗑️ Undo last import", key="evb_undo"):
                _undo_last_batch(service)


# ──────────────────────────────────────────────────────────────────────────────
# Settings (lightweight for now)

def show_settings(service):
    _init_session_defaults()
    st.title("⚙️ Settings")
    st.caption("Session info and export.")

    st.markdown("**Signed in as**: " + (st.session_state.get("user_email") or "Unknown"))
    active_id = st.session_state.get("active_calendar","primary")
    active_name = _calendar_name_for_id(active_id)
    st.markdown("**Active calendar**: " + f"`{active_name}` · `{active_id}`")


    with st.expander("Session usage"):
        st.json(st.session_state.get("usage_stats", {}))

    if not st.session_state["parsed_events_df"].empty:
        st.download_button(
            label="Download current preview as CSV",
            data=st.session_state["parsed_events_df"].to_csv(index=False),
            file_name="event_preview.csv",
            mime="text/csv"
        )
