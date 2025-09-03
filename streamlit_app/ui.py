# streamlit_app/ui.py
from __future__ import annotations

import json
import math
import datetime as dt
from typing import List, Dict, Any, Optional

import pandas as pd
import streamlit as st
from project_code import auth

# 🔁 Project code (no Streamlit) helpers for Calendar API CRUD + event creation
# Make sure these functions exist in project_code/creating_calendar.py
from project_code import creating_calendar as create_mod

DEFAULT_NAME = dt.date.today().strftime("My Calendar %Y-%m-%d")

# data preview

# ──────────────────────────────────────────────────────────────────────────────
# Data editor helpers (Streamlit-only)
# These helpers let st.data_editor handle list/dict cells by temporarily
# serializing them to JSON strings and then parsing them back after editing.

def _to_streamlit_editable(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str]]:
    """
    Return a copy of df where any list/dict cells are converted to JSON strings,
    plus a list of the columns we transformed so we can parse them back later.
    """
    editable = df.copy()
    json_cols: list[str] = []
    for col in editable.columns:
        # If *any* value in the column is a list/dict, treat the whole column as JSON-able
        if editable[col].map(lambda v: isinstance(v, (list, dict))).any():
            json_cols.append(col)
            editable[col] = editable[col].map(
                lambda v: json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict)) else v
            )
    return editable, json_cols


def _from_streamlit_editable(edited: pd.DataFrame, json_cols: list[str]) -> pd.DataFrame:
    """
    Parse back the JSON strings created by _to_streamlit_editable for the
    specified columns. Non-JSON strings are left as-is.
    """
    parsed = edited.copy()
    for col in json_cols:
        if col in parsed.columns:
            def _maybe_json(x):
                if isinstance(x, str):
                    s = x.strip()
                    # quick shape check: looks like a JSON list or dict
                    if (s.startswith('[') and s.endswith(']')) or (s.startswith('{') and s.endswith('}')):
                        try:
                            return json.loads(s)
                        except Exception:
                            return x
                return x
            parsed[col] = parsed[col].map(_maybe_json)
    return parsed



# ──────────────────────────────────────────────────────────────────────────────
# Small guard to enforce session credentials for every Google call

def _require_creds():
    """
    Require an OAuth Credentials object in session.
    This keeps behavior deterministic and supports your 2-hour auto-logout.
    """
    creds = st.session_state.get("credentials")
    if not creds:
        st.error("Please sign in again.")
        st.stop()
    return creds


# ──────────────────────────────────────────────────────────────────────────────
# Basic calendar helpers (pure UI/Session logic)

def _is_primary(cal_id: str) -> bool:
    for c in st.session_state.get("calendars", []):
        if c["id"] == cal_id:
            return bool(c.get("primary"))
    return cal_id == "primary"


def _calendar_label(cal: dict) -> str:
    return f"{cal.get('summary', cal['id'])} · {cal['id']}"


def _calendar_name_for_id(cal_id: str) -> str:
    for c in st.session_state.get("calendars", []):
        if c["id"] == cal_id:
            return c.get("summary", cal_id)
    return cal_id


def _calendar_timezone_for_id(cal_id: str) -> str:
    for c in st.session_state.get("calendars", []):
        if c["id"] == cal_id:
            return (c.get("timeZone") or "").strip()
    return ""


def _primary_calendar_id() -> str:
    for c in st.session_state.get("calendars", []):
        if c.get("primary"):
            return c["id"]
    return st.session_state.get("active_calendar", "primary")


# ──────────────────────────────────────────────────────────────────────────────
# UX banners / flows

def _primary_calendar_banner(service):
    """
    Warn if user is about to bulk-create on Primary calendar.
    Offer a one-click create+switch to a fresh calendar.
    """
    cal_id = st.session_state.get("active_calendar", "primary")
    if not cal_id:
        return

    if _is_primary(cal_id):
        st.warning(
            "You’re targeting your **Primary** calendar. For bulk/testing, create and use a separate calendar.",
            icon="⚠️",
        )
        c1, c2 = st.columns([0.7, 0.3])
        with c1:
            new_name = st.text_input("New calendar name", value=DEFAULT_NAME, key="warn_newcal_name")
        with c2:
            if st.button("Create & switch", key="warn_create_switch"):
                try:
                    creds = _require_creds()
                    tz = create_mod.get_user_default_timezone(creds)
                    new_id = create_mod.create_calendar(creds, new_name, time_zone=tz)
                    _refresh_calendars(service)
                    st.session_state["active_calendar"] = new_id
                    st.session_state["usage_stats"]["last_action"] = f"Created calendar {new_name}"
                    st.success(f"Created and selected `{_calendar_name_for_id(new_id)}`.")
                except Exception as e:
                    st.error(f"Failed to create calendar: {e}")
    else:
        st.info("Best practice: use a dedicated calendar for imports/bulk operations.", icon="💡")


def _role_for_calendar(cal_id: str) -> str:
    for c in st.session_state.get("calendars", []):
        if c["id"] == cal_id:
            return (c.get("accessRole") or "").lower()
    return ""


# sync calendar
def _sync_preview_to_active_calendar():
    """
    If the user switches the active calendar, keep the Preview rows consistent:
    - strip any row-level calendar hints so the selected calendar is used
    - for TIMED rows (have event_time) with a blank timezone, default to the
      newly selected calendar's timezone
    """
    active_id = st.session_state.get("active_calendar")
    if not active_id:
        return

    prev_id = st.session_state.get("_prev_active_calendar")
    if prev_id == active_id:
        return  # nothing changed

    df = st.session_state.get("parsed_events_df")
    if df is None or df.empty:
        st.session_state["_prev_active_calendar"] = active_id
        st.session_state["_prev_active_calendar_tz"] = _calendar_timezone_for_id(active_id)
        return

    # 1) remove any per-row calendar hints so bulk creation uses the selected calendar
    for col in ("calendar_id", "google_calendar_id", "calendar_name"):
        if col in df.columns:
            df = df.drop(columns=[col])

    # 2) for timed rows with no tz, default tz to the new calendar's tz
    cal_tz = _calendar_timezone_for_id(active_id)
    if cal_tz and "event_time" in df.columns:
        if "timezone" not in df.columns:
            df["timezone"] = ""
        timed_mask = df["event_time"].fillna("").astype(str).str.strip() != ""
        blank_tz   = df["timezone"].fillna("").astype(str).str.strip() == ""
        df.loc[timed_mask & blank_tz, "timezone"] = cal_tz  # all-day rows remain tz-blank

    st.session_state["parsed_events_df"] = df
    st.session_state["_prev_active_calendar"] = active_id
    st.session_state["_prev_active_calendar_tz"] = cal_tz



# ──────────────────────────────────────────────────────────────────────────────
# Session state + notifications

def _init_session_defaults():
    st.session_state.setdefault("undo_stack", [])              # list of batches (each may span multiple calendars)
    st.session_state.setdefault("created_batches", [])         # mirror for inspection/export
    st.session_state.setdefault("usage_stats", {"events_added": 0, "last_action": "—"})
    st.session_state.setdefault("parsed_events_df", pd.DataFrame())
    st.session_state.setdefault("active_calendar", "primary")
    st.session_state.setdefault("llm_enabled", False)
    st.session_state.setdefault("billing_ok", False)
    st.session_state.setdefault("calendars", [])               # cached calendars (with timeZone/accessRole)


def _success(msg: str):
    st.session_state["usage_stats"]["last_action"] = msg
    if st.session_state.get("_last_notice") == ("success", msg):
        return
    st.session_state["_last_notice"] = ("success", msg)
    st.success(msg)


def _error(msg: str):
    st.session_state["usage_stats"]["last_action"] = f"Error: {msg}"
    if st.session_state.get("_last_notice") == ("error", msg):
        return
    st.session_state["_last_notice"] = ("error", msg)
    st.error(msg)


# ──────────────────────────────────────────────────────────────────────────────
# Delete/unsubscribe confirmation UI

def _ask_confirm_delete(cal_id: str, mode: str):
    """mode: 'unsubscribe' or 'delete'"""
    st.session_state["_pending_cal_del"] = {"id": cal_id, "mode": mode}


def _maybe_render_delete_modal(service):
    data = st.session_state.get("_pending_cal_del")
    if not data:
        return
    cal_id, mode = data["id"], data["mode"]
    cal_name = _calendar_name_for_id(cal_id)

    with st.container(border=True):
        if mode == "delete":
            st.error(
                f"Delete calendar **{cal_name}**?\n\n"
                "This will permanently delete the calendar **and all events on it** for everyone. "
                "This cannot be undone."
            )
        else:
            st.warning(
                f"Remove **{cal_name}** from your list?\n\n"
                "This will unsubscribe it from your account (events remain for others)."
            )

        c1, c2 = st.columns(2)
        with c1:
            if st.button("Confirm", type="primary", key="confirm_cal_del"):
                try:
                    creds = _require_creds()
                    if mode == "delete":
                        create_mod.delete_calendar(creds, cal_id)
                        _success(f"Deleted calendar: `{cal_name}`")
                    else:
                        create_mod.unsubscribe_calendar(creds, cal_id)
                        _success(f"Removed from your list: `{cal_name}`")

                    # Refresh list & fix selection if needed
                    _refresh_calendars(service)
                    if st.session_state.get("active_calendar") == cal_id:
                        st.session_state["active_calendar"] = _primary_calendar_id()
                except Exception as e:
                    _error(f"Failed: {e}")
                finally:
                    st.session_state.pop("_pending_cal_del", None)

        with c2:
            if st.button("Cancel", key="cancel_cal_del"):
                st.session_state.pop("_pending_cal_del", None)


def _render_manage_calendars_ui(service):
    st.caption("Manage calendars")
    for cal in _get_calendars_cached(service):
        cal_id = cal["id"]
        name = cal.get("summary", cal_id)
        role = (cal.get("accessRole") or "").lower()
        tz = cal.get("timeZone") or "—"

        c1, c2, c3, c4 = st.columns([0.55, 0.2, 0.15, 0.10])
        with c1:
            st.write(f"**{name}**")
            st.caption(f"`{cal_id}`")
        with c2:
            st.caption(f"Role: `{role}`  ·  TZ: `{tz}`")
        with c3:
            # Decide which action is available
            can_delete = (role == "owner") and (not cal.get("primary", False))
            can_unsub  = (role in ("reader", "writer", "freebusyreader")) or (role == "owner" and not can_delete)

            if can_delete:
                st.button("🗑️ Delete calendar", key=f"del_{cal_id}",
                          on_click=_ask_confirm_delete, args=(cal_id, "delete"))
            elif can_unsub:
                st.button("Remove from my list", key=f"unsub_{cal_id}",
                          on_click=_ask_confirm_delete, args=(cal_id, "unsubscribe"))
            else:
                st.caption("—")
        with c4:
            # Optional: quick switch
            st.button("Use", key=f"use_{cal_id}",
                      on_click=lambda cid=cal_id: st.session_state.update({"active_calendar": cid}))

    _maybe_render_delete_modal(service)


# ──────────────────────────────────────────────────────────────────────────────
# Calendar caching (UI owns session cache, project_code does network)

def _refresh_calendars(service):
    """
    Pull the user's calendars using project_code (no Streamlit there),
    then cache them in session for UI use.
    """
    creds = _require_creds()
    cals = create_mod.list_calendars(creds)
    st.session_state["calendars"] = cals
    if cals and not any(c["id"] == st.session_state.get("active_calendar") for c in cals):
        st.session_state["active_calendar"] = cals[0]["id"]
    return cals


def _get_calendars_cached(service):
    if "calendars" not in st.session_state or not st.session_state["calendars"]:
        return _refresh_calendars(service)
    return st.session_state["calendars"]


# ──────────────────────────────────────────────────────────────────────────────
# Input sanitation & normalization

def _str_or_empty(x) -> str:
    """Return a trimmed string; '' for None/NaN; stringify other scalars safely."""
    if isinstance(x, str):
        return x.strip()
    if x is None:
        return ""
    if isinstance(x, float) and math.isnan(x):
        return ""
    return str(x).strip()


def _sanitize_rows(rows: list[dict]) -> list[dict]:
    """Fix common issues from pasted/uploaded/edited rows (NaN, key typos, types)."""
    out = []
    for r in rows:
        rr = dict(r)

        # Key typo commonly seen
        if "location:" in rr and "location" not in rr:
            rr["location"] = rr.pop("location:") or ""

        # String-ish fields
        for k in ["title", "description", "calendar_id", "calendar_name",
                  "google_calendar_id", "event_date", "event_time", "end_time",
                  "end_date", "timezone", "location", "recurrence", "user_email"]:
            if k in rr:
                rr[k] = _str_or_empty(rr.get(k))

        # List fields
        if not isinstance(rr.get("notifications"), list):
            rr["notifications"] = [] if rr.get("notifications") in (None, "") else rr.get("notifications") or []
        if not isinstance(rr.get("invitees"), list):
            rr["invitees"] = [] if rr.get("invitees") in (None, "") else rr.get("invitees") or []

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
            rr["end_time"] = ""      # clear end_time for all-day
            rr["timezone"] = ""
            if not _str_or_empty(rr.get("end_date")):
                rr["end_date"] = d
        out.append(rr)
    return out


def _apply_default_tz_for_timed(rows: list[dict], cal_tz: str) -> list[dict]:
    """For rows with a time, default timezone to the calendar's tz when missing."""
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


# ──────────────────────────────────────────────────────────────────────────────
# Calendar resolution (per-row) & grouping

def _looks_like_calendar_id(val: str) -> bool:
    v = (val or "").lower()
    return "@group.calendar.google.com" in v or v.endswith("@gmail.com") or v.endswith("@google.com")


def _resolve_calendar_id_for_row(row: dict, selected_id: str, calendars: list[dict]) -> tuple[Optional[str], Optional[str]]:
    """
    Resolve the row's calendar to a real calendarId.
    Returns (calendar_id, error_message). If no calendar fields present, default to selected_id.
    No silent overrides: if a name cannot be resolved, returns (None, 'why').
    """
    raw = _str_or_empty(row.get("google_calendar_id")) or _str_or_empty(row.get("calendar_id")) or _str_or_empty(row.get("calendar_name"))
    if not raw:
        return selected_id, None

    if raw.lower() == "primary":
        return _primary_calendar_id(), None

    if _looks_like_calendar_id(raw):
        match = next((c for c in calendars if c["id"] == raw), None)
        if not match:
            return None, f"Unknown calendar id '{raw}'"
        if (match.get("accessRole") or "") not in ("owner", "writer"):
            return None, f"No write access to '{_calendar_label(match)}'"
        return raw, None

    matches = [c for c in calendars if _str_or_empty(c.get("summary")) == raw]
    if not matches:
        return None, f"Calendar named '{raw}' not found"
    writable = [c for c in matches if (c.get("accessRole") or "") in ("owner", "writer")]
    chosen = (writable or matches)[0]
    return chosen["id"], None


def _group_rows_by_calendar(rows: list[dict], selected_id: str, calendars: list[dict]):
    """
    Group rows by resolved calendar id, collecting errors for unresolved/unauthorized names/ids.
    """
    groups: Dict[str, List[dict]] = {}
    errors: List[str] = []
    info_counts: Dict[str, int] = {}
    for r in rows:
        cal_id, err = _resolve_calendar_id_for_row(r, selected_id, calendars)
        if err:
            errors.append(err)
            continue
        rr = dict(r)
        rr.pop("google_calendar_id", None)
        rr.pop("calendar_id", None)
        rr.pop("calendar_name", None)
        groups.setdefault(cal_id, []).append(rr)
    for cid, lst in groups.items():
        info_counts[cid] = len(lst)
    return groups, errors, info_counts


# ──────────────────────────────────────────────────────────────────────────────
# Auth screen (Cloud flow)

def show_login_page():
    """
    Cloud OAuth flow using streamlit-free helpers in project_code.auth.
    - If a code is present in the URL, exchange it for credentials (same tab).
    - Else, render exactly one "Continue with Google" link (same tab).
    """
    st.title("😪 LazyCal 🗓️")
    st.write("🔐 Sign in to connect your Google Calendar.")

    cfg = st.secrets["google_oauth"]
    client_id = cfg["client_id"]
    client_secret = cfg["client_secret"]
    redirect_uri = cfg["redirect_uri"]

    # Already signed in?
    creds = st.session_state.get("credentials")
    if creds:
        try:
            creds = auth.refresh_if_needed(creds)  # harmless if still valid
        except Exception:
            pass
        st.session_state["credentials"] = creds
        st.session_state["service"] = auth.build_calendar_service(creds)
        st.session_state["user_email"] = auth.get_authenticated_email(st.session_state["service"], creds)
        st.rerun()

    # Handle redirect (code) first
    q = st.query_params
    code = q.get("code")
    code = code[0] if isinstance(code, list) else code
    if code:
        try:
            creds = auth.web_exchange_code(client_id, client_secret, redirect_uri, code)
            st.session_state["credentials"] = creds
            st.session_state["service"] = auth.build_calendar_service(creds)
            st.session_state["user_email"] = auth.get_authenticated_email(st.session_state["service"], creds)
            try:
                st.query_params.clear()
            except Exception:
                pass
            st.rerun()
        except Exception:
            st.error("Sign-in failed. Please click Continue with Google again.")

    # No code yet — create the auth URL once and render exactly ONE link (same tab)
    if "oauth_auth_url" not in st.session_state or "oauth_state" not in st.session_state:
        auth_url, state = auth.web_authorization_url(client_id, client_secret, redirect_uri)
        st.session_state["oauth_auth_url"] = auth_url
        st.session_state["oauth_state"] = state

    auth_url = st.session_state["oauth_auth_url"]

    st.link_button("Continue with Google", auth_url, use_container_width=True, type="primary")
    st.caption("You will be redirected to Google to authorize access.")

# ──────────────────────────────────────────────────────────────────────────────
# Home

def show_home(service):
    _init_session_defaults()

    user = st.session_state.get("user_email") or "Unknown user"
    st.title("📅 Calendar Automation")
    st.caption("Google Calendar • paste / upload • optional LLM parsing • undo batches")

    with st.container(border=True):
        c1, c2 = st.columns([2, 1])
        with c1:
            active_id = st.session_state.get("active_calendar", "primary")
            active_name = _calendar_name_for_id(active_id)
            active_tz = _calendar_timezone_for_id(active_id) or "—"
            st.markdown(
                f"**Signed in as:** `{user}`  \n"
                f"**Active calendar:** `{active_name}` · `{active_id}`  \n"
                f"**Time zone:** `{active_tz}`"
            )
            st.markdown("### How it works")
            st.markdown(
                "- Choose an input mode: natural language (LLM), `.txt` upload, or structured paste.\n"
                "- Preview and edit events in a table before creating.\n"
                "- Create events in groups (by calendar) with one click.\n"
                "- Undo the last batch if needed."
            )
        with c2:
            stats = st.session_state["usage_stats"]
            st.metric("Events added (this session)", stats["events_added"])
            st.caption(f"Last action: {stats['last_action']}")

    st.divider()
    st.subheader("Your calendars")
    _sync_preview_to_active_calendar()
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
        _primary_calendar_banner(service)
    else:
        st.info("No calendars found. Use Event Builder to create one.")

    with st.expander("Create a new calendar"):
        new_name = st.text_input("Calendar name", placeholder=DEFAULT_NAME)
        if st.button("Create / ensure", key="ensure_calendar_btn"):
            try:
                creds = _require_creds()
                existing = _get_calendars_cached(service)
                match = next((c for c in existing if c.get("summary") == new_name), None)
                if match:
                    cal_id = match["id"]
                else:
                    tz = create_mod.get_user_default_timezone(creds)
                    cal_id = create_mod.create_calendar(creds, new_name, time_zone=tz)
                _refresh_calendars(service)
                _sync_preview_to_active_calendar()
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


# ──────────────────────────────────────────────────────────────────────────────
# Event Builder

def _coerce_root_to_list(obj: Any) -> List[Dict[str, Any]]:
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict):
        return [obj]
    raise ValueError("JSON must be a list of dicts or a single dict.")


def _load_json_into_preview(raw_text: str):
    """Lenient ingest: accept list or single dict; on JSON error, show banner."""
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

        # Autofill timezone for TIMED rows using the currently selected calendar
        cal_id = st.session_state.get("active_calendar") or "primary"
        cal_tz = _calendar_timezone_for_id(cal_id) or ""   # preview mirrors selection
        if "event_time" in df.columns:
            if "timezone" not in df.columns:
                df["timezone"] = ""
            timed = df["event_time"].fillna("").astype(str).str.strip() != ""
            blank_tz = df["timezone"].fillna("").astype(str).str.strip() == ""
            if cal_tz:
                df.loc[timed & blank_tz, "timezone"] = cal_tz  # keep all-day rows tz-blank

        st.session_state["parsed_events_df"] = df
        _success(f"Loaded {len(df)} record(s) into preview.")
    except Exception as e:
        _error(f"Invalid JSON: {e}")


def show_event_builder(service):
    _init_session_defaults()
    st.title("🧱 Event Builder")
    st.caption("Paste, upload, or describe your events. Preview, edit, and create by calendar groups.")

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
            "Target calendar (used when a row doesn't specify one)",
            options=list(range(len(ids))),
            format_func=lambda i: labels[i],
            index=idx,
            key="evb_cal_select",
        )
        st.session_state["active_calendar"] = ids[choice]
        _sync_preview_to_active_calendar()
        _primary_calendar_banner(service)
        _render_manage_calendars_ui(service)

        new_name = st.text_input(
            "Create new calendar (optional)",
            placeholder=DEFAULT_NAME,
            key="evb_new_cal_name",
        )
        if st.button("Create / ensure calendar", key="evb_create_cal_btn"):
            try:
                creds = _require_creds()
                existing = _get_calendars_cached(service)
                match = next((c for c in existing if c.get("summary") == new_name), None)
                if match:
                    cal_id = match["id"]
                else:
                    tz = create_mod.get_user_default_timezone(creds)
                    cal_id = create_mod.create_calendar(creds, new_name, time_zone=tz)
                _refresh_calendars(service)
                st.session_state["active_calendar"] = cal_id
                _success(f"Calendar ready: `{new_name}` · `{cal_id}`")
            except Exception as e:
                _error(f"Failed: {e}")

        st.toggle("Enable LLM parsing (billing applies)", key="evb_llm_enabled")

    # Input tabs
    tab1, tab2, tab3 = st.tabs(["Natural Language (LLM)", "Upload .txt", "Structured paste"])

    with tab1:
        st.markdown("Describe your events in plain English (stubbed for now).")
        st.info('Example: "Study group Monday 7-8pm at DC Library; Coffee with Maya Tue 9:30am."')
        nl = st.text_area("Your description", height=140, key="evb_nl")
        st.checkbox("I agree to pay for LLM parsing.", key="evb_billing_ok")
        if st.button("Generate structured events with LLM", key="evb_generate_llm"):
            if not st.session_state["evb_llm_enabled"]:
                _error("Enable LLM parsing first.")
            elif not st.session_state["evb_billing_ok"]:
                _error("Please agree to pay for LLM parsing.")
            elif not nl.strip():
                _error("Please enter a description.")
            else:
                _error("LLM parsing is not enabled yet. (Stub)")

    with tab2:
        up = st.file_uploader("Upload a .txt containing JSON", type=["txt"], key="evb_uploader")
        if up is not None and st.button("Parse uploaded file", key="evb_parse_upload"):
            try:
                raw = up.read().decode("utf-8")
                _load_json_into_preview(raw)
            except Exception as e:
                _error(f"Failed to read file: {e}")

    with tab3:
        st.markdown("**Paste event records** as JSON (list of dicts or a single dict).")
        example = [{
            "title": "Sample Event",
            "event_date": dt.date.today().isoformat(),
            "description": "Optional",
            "event_time": "10:00",        # omit for all-day
            "end_time": "10:45",          # optional; default applied if missing
            "end_date": dt.date.today().isoformat(),
            "notifications": [],
            "invitees": [],
            "location": "",
            "recurrence": ""              # e.g., "RRULE:FREQ=WEEKLY;COUNT=8"
        }]
        st.caption("Tip: leave `event_time` blank for an **all-day** event. If you provide `event_time` without `end_time`, a default duration is applied.")
        st.code(json.dumps(example, indent=2), language="json")
        raw = st.text_area("Paste here", height=220, placeholder="[\n  {...}\n]", key="evb_paste")
        if st.button("Parse pasted JSON", key="evb_parse_paste"):
            _load_json_into_preview(raw)

    # Preview & edit (outside tabs)
    st.divider()
    st.subheader("Preview & edit")

    # --- Preview & edit (outside tabs) ---
    # 1) Keep calendar_id/timezone in the DF; hide only true internals
    display_df = st.session_state["parsed_events_df"].copy()
    for col in ["service", "google_calendar_id", "calendar_name", "user_email"]:  # CHANGED: removed 'timezone', 'calendar_id'
        if col in display_df.columns:
            display_df = display_df.drop(columns=[col])

    selected_id = st.session_state.get("active_calendar", "primary")
    st.caption(
        f"Selected calendar: `{_calendar_name_for_id(selected_id)}` · `{selected_id}`  \n"
        f"Time zone: `{_calendar_timezone_for_id(selected_id) or '—'}`"
    )

    # Optional: show a read-only label so users see where blanks will go
    display_df.insert(0, "target_calendar", f"{_calendar_name_for_id(selected_id)}")

    editable_df, json_cols = _to_streamlit_editable(display_df)
    edited = st.data_editor(
        editable_df,
        use_container_width=True,
        height=360,
        num_rows="dynamic",
        key="evb_editor",
        column_config={
            "target_calendar": st.column_config.TextColumn(disabled=True),
            "calendar_id":     st.column_config.TextColumn(disabled=True),  # CHANGED
            "timezone":        st.column_config.TextColumn(disabled=True),  # CHANGED
        },
    )
    edited = _from_streamlit_editable(edited, json_cols)

    # Sync back ONLY editable columns (unchanged)
    base_df = st.session_state["parsed_events_df"]
    for col in edited.columns:
        if col in base_df.columns:
            base_df[col] = edited[col]
    st.session_state["parsed_events_df"] = base_df

    # --- Actions ---
    c1, c2 = st.columns(2)
    with c1:
        if st.button("🚀 Create events", key="evb_create_events"):
            df_to_create = st.session_state["parsed_events_df"].copy()

            # 2) (Optional) coalesce blank calendar_id to the active selection
            if "calendar_id" not in df_to_create.columns:
                df_to_create["calendar_id"] = ""
            mask_cal = df_to_create["calendar_id"].isna() | (df_to_create["calendar_id"].astype(str).str.strip() == "")
            df_to_create.loc[mask_cal, "calendar_id"] = selected_id

            # 3) DO NOT fill timezone here; let _create_events_batch apply defaults per calendar   # CHANGED
            # (Your _create_events_batch uses _apply_default_tz_for_timed + cal_tz)

            # (Optional) name for logs/UX
            df_to_create["calendar_name"] = _calendar_name_for_id(selected_id)

            # If downstream expects google_calendar_id, set it explicitly
            if "google_calendar_id" not in df_to_create.columns:
                df_to_create["google_calendar_id"] = df_to_create["calendar_id"]

            _create_events_batch(service, df_to_create)

    with c2:
        if st.button("🗑️ Undo last import", key="evb_undo"):
            _undo_last_batch(service)



# ──────────────────────────────────────────────────────────────────────────────
# Create / Undo logic

def _create_events_batch(service, df: pd.DataFrame):
    """
    Create events in groups (by calendar). Validates calendars, normalizes rows,
    and records created ids for undo.
    """
    if df is None or df.empty:
        _error("Load records first.")
        return

    email = st.session_state.get("user_email") or "unknown@example.com"
    selected_cal = st.session_state.get("active_calendar") or "primary"
    calendars = _get_calendars_cached(service)

    # Prep rows
    rows = df.to_dict(orient="records")
    rows = _sanitize_rows(rows)
    rows = _normalize_all_day_rows(rows)

    # Resolve calendars per row
    groups, errors, info_counts = _group_rows_by_calendar(rows, selected_cal, calendars)
    if errors:
        msg = " • " + "\n • ".join(sorted(set(errors)))
        _error(f"Some rows reference calendars that can't be used:\n{msg}")
        return
    if len(info_counts) > 1:
        summaries = [f"{_calendar_name_for_id(cid)} ({cnt})" for cid, cnt in info_counts.items()]
        st.info("Creating by calendar: " + ", ".join(summaries))

    creds = _require_creds()

    total_created = 0
    batch_groups = []

    for cal_id, rows_for_cal in groups.items():
        # Default TZ for TIMED rows to THIS calendar's tz (prevents UTC fallback)
        cal_tz = _calendar_timezone_for_id(cal_id) or create_mod.get_user_default_timezone(creds)
        rows_for_cal = _apply_default_tz_for_timed(rows_for_cal, cal_tz)

        created_refs: List[Dict[str, Any]] = []

        for r in rows_for_cal:
            try:
                is_timed = bool(_str_or_empty(r.get("event_time")))
                tz_to_use = (r.get("timezone") or cal_tz) if is_timed else ""  # no tz for all-day
                created = create_mod.create_single_event(
                    service=service,
                    calendar_id=cal_id,
                    title=r.get("title") or "Untitled",
                    description=r.get("description") or "",
                    event_date=r.get("event_date") or "",
                    event_time=r.get("event_time") or "",
                    end_time=r.get("end_time") or "",
                    end_date=r.get("end_date") or r.get("event_date") or "",
                    timezone=tz_to_use,
                    notifications=r.get("notifications") or [],
                    invitees=r.get("invitees") or [],
                    location=r.get("location", ""),
                    recurrence=r.get("recurrence"),
                    user_email=email,
                    send_updates="none",
                )

                ev_id = (created or {}).get("id")
                if ev_id:
                    created_refs.append({"id": ev_id, "iCalUID": (created or {}).get("iCalUID")})
            except Exception as e_single:
                _error(f"Failed to create an event on `{_calendar_name_for_id(cal_id)}`: {e_single}")
                # continue with other rows

        total_created += len(created_refs)
        if created_refs:
            batch_groups.append({"calendar_id": cal_id, "refs": created_refs})

    if total_created == 0:
        _error("No events were created.")
        return

    # Record batch for undo
    batch = {"groups": batch_groups}
    st.session_state["undo_stack"].append(batch)
    st.session_state["created_batches"].append(batch)
    st.session_state["usage_stats"]["events_added"] += total_created
    _success(f"Created {total_created} event(s) across {len(batch_groups)} calendar(s).")


def _undo_last_batch(service):
    """
    Delete the most recently created batch (across one or more calendars).
    Resilient to 404 via iCalUID lookup.
    """
    if not st.session_state.get("undo_stack"):
        _error("Nothing to undo.")
        return

    batch = st.session_state["undo_stack"].pop()
    groups = batch.get("groups") or []

    from googleapiclient.errors import HttpError  # type: ignore
    deleted = 0
    not_found_total = 0
    remainder_groups = []

    for g in groups:
        cal_id = g.get("calendar_id")
        refs = g.get("refs") or []
        unfound_refs = []
        for ref in refs:
            eid = ref.get("id")
            iuid = ref.get("iCalUID")
            try:
                service.events().delete(calendarId=cal_id, eventId=eid, sendUpdates="none").execute()
                deleted += 1
                continue
            except HttpError as he:
                try:
                    if he.resp.status == 404 and iuid:
                        resp = service.events().list(calendarId=cal_id, iCalUID=iuid, maxResults=5, singleEvents=True).execute()
                        items = resp.get("items", [])
                        if items:
                            for it in items:
                                service.events().delete(calendarId=cal_id, eventId=it["id"], sendUpdates="none").execute()
                                deleted += 1
                            continue
                except Exception:
                    pass
                not_found_total += 1
                unfound_refs.append(ref)
            except Exception:
                not_found_total += 1
                unfound_refs.append(ref)
        if unfound_refs:
            remainder_groups.append({"calendar_id": cal_id, "refs": unfound_refs})

    if remainder_groups:
        st.session_state["undo_stack"].append({"groups": remainder_groups})

    st.session_state["usage_stats"]["events_added"] = max(0, st.session_state["usage_stats"]["events_added"] - deleted)

    if deleted and not remainder_groups:
        _success(f"Deleted {deleted} event(s).")
    elif deleted and remainder_groups:
        _error(f"Deleted {deleted} event(s), but {not_found_total} could not be found for undo.")
    else:
        _error("Undo failed: no matching events were found to delete.")
