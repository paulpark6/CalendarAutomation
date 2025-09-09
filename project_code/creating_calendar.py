# project_code/creating_calendar_methods.py
from __future__ import annotations

import datetime as dt
from typing import Any, List, Dict, Optional, Union

from google.auth.transport.requests import AuthorizedSession
from google.oauth2.credentials import Credentials


def _credentials_from_service(service) -> Optional[Credentials]:
    """
    Pull google.oauth2.credentials.Credentials off a discovery 'service'.
    """
    http = getattr(service, "_http", None)
    return getattr(http, "credentials", None)


def _authed_session(service, creds: Optional[Credentials] = None) -> AuthorizedSession:
    """
    Build an AuthorizedSession from provided creds or from the service object.
    """
    c = creds or _credentials_from_service(service)
    if c is None:
        raise RuntimeError("No Google credentials available. Sign in again.")
    return AuthorizedSession(c)


def list_calendars(service, creds: Optional[Credentials] = None) -> List[Dict[str, Any]]:
    """
    Return the user's calendars: id, summary, accessRole, primary, timeZone.
    """
    sess = _authed_session(service, creds)
    url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"

    results: List[Dict[str, Any]] = []
    token: Optional[str] = None

    while True:
        params = {"maxResults": 250}
        if token:
            params["pageToken"] = token

        r = sess.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json() or {}

        for it in data.get("items", []):
            results.append({
                "id": it["id"],
                "summary": it.get("summary", it["id"]),
                "accessRole": it.get("accessRole"),
                "primary": it.get("primary", False),
                "timeZone": it.get("timeZone"),
            })

        token = data.get("nextPageToken")
        if not token:
            break

    return results

# ---------- Low-level HTTP session (internal helper) ----------
def _session(creds: Credentials) -> AuthorizedSession:
    if not isinstance(creds, Credentials):
        raise ValueError("Valid google.oauth2.credentials.Credentials required.")
    return AuthorizedSession(creds)


# ---------- Calendar CRUD (public) ----------
def list_calendars(creds: Credentials) -> List[Dict[str, Any]]:
    """
    Return list of calendars with: id, summary, accessRole, primary, timeZone.
    """
    sess = _session(creds)
    url = "https://www.googleapis.com/calendar/v3/users/me/calendarList"
    out: List[Dict[str, Any]] = []
    token: Optional[str] = None
    while True:
        params = {"maxResults": 250}
        if token:
            params["pageToken"] = token
        r = sess.get(url, params=params, timeout=30)
        r.raise_for_status()
        data = r.json() or {}
        for it in data.get("items", []):
            out.append({
                "id": it["id"],
                "summary": it.get("summary", it["id"]),
                "accessRole": it.get("accessRole"),
                "primary": it.get("primary", False),
                "timeZone": it.get("timeZone"),
            })
        token = data.get("nextPageToken")
        if not token:
            break
    return out


def get_user_default_timezone(creds: Credentials) -> str:
    """
    User's default time zone from Google Calendar settings.
    Falls back to UTC on failure.
    """
    sess = _session(creds)
    try:
        r = sess.get(
            "https://www.googleapis.com/calendar/v3/users/me/settings/timezone",
            timeout=15,
        )
        r.raise_for_status()
        tz = (r.json() or {}).get("value")
        if tz:
            return tz
    except Exception:
        pass
    return "UTC"


def create_calendar(creds: Credentials, name: str, time_zone: Optional[str] = None) -> str:
    """
    Create a calendar with summary=name and explicit timeZone; return its ID.
    Also sets calendar-level default reminders so events using useDefault=True
    will get popup alerts at 2h, 1d, 3d, and 1w before start.
    """
    sess = _session(creds)
    tz = time_zone or get_user_default_timezone(creds)

    # 1) Create the calendar
    r = sess.post(
        "https://www.googleapis.com/calendar/v3/calendars",
        json={"summary": name, "timeZone": tz},
        timeout=30,
    )
    r.raise_for_status()
    cal_id = (r.json() or {}).get("id")
    if not cal_id:
        raise RuntimeError("Calendar create returned no id.")

    # 2) Set default reminders on the user's CalendarList entry
    #    (affects events with reminders.useDefault = true)
    default_reminders = [
        {"method": "popup", "minutes": 120},     # 2 hours
        {"method": "popup", "minutes": 1440},    # 1 day
        {"method": "popup", "minutes": 4320},    # 3 days
        {"method": "popup", "minutes": 10080},   # 1 week
    ]
    try:
        pr = sess.patch(
            f"https://www.googleapis.com/calendar/v3/users/me/calendarList/{cal_id}",
            json={"defaultReminders": default_reminders},
            timeout=30,
        )
        pr.raise_for_status()
    except Exception as e:
        # Don’t fail calendar creation if setting defaults hiccups; surface a soft warning if you want.
        # st.warning(f"Calendar created, but default reminders not set: {e}")
        pass

    return cal_id



def unsubscribe_calendar(creds: Credentials, calendar_id: str) -> None:
    """
    Remove a calendar from the user's list (does not delete the calendar).
    """
    sess = _session(creds)
    r = sess.delete(
        f"https://www.googleapis.com/calendar/v3/users/me/calendarList/{calendar_id}",
        timeout=15,
    )
    r.raise_for_status()


def delete_calendar(creds: Credentials, calendar_id: str) -> None:
    """
    Delete the calendar itself (owner only). Permanently deletes all events.
    """
    sess = _session(creds)
    r = sess.delete(
        f"https://www.googleapis.com/calendar/v3/calendars/{calendar_id}",
        timeout=20,
    )
    r.raise_for_status()

def _assert_creds(service):
    http = getattr(service, "_http", None)
    creds = getattr(http, "credentials", None)
    assert creds is not None, "No credentials on service._http"
    # If expired, try refreshing (only works if refresh_token exists)
    if creds.expired and creds.refresh_token:
        from google.auth.transport.requests import Request
        creds.refresh(Request())
    # Show who we are (useful log)
    me = AuthorizedSession(creds).get("https://www.googleapis.com/oauth2/v2/userinfo", timeout=8).json()
    print("Authenticated as:", me.get("email"))



# ---------- Event creation (public, used by UI) ----------
def create_single_event(
    *,
    service,                         # discovery client from googleapiclient.discovery.build
    calendar_id: str,
    title: str,
    description: str,
    event_date: str,                 # 'YYYY-MM-DD'
    event_time: str,                 # '' for all-day
    end_time: str,                   # optional for timed; '' allowed
    end_date: str,                   # for all-day; if timed, can equal event_date
    timezone: str,                   # tz name for timed (e.g., 'America/Toronto'); '' for all-day
    notifications: List[Any],
    invitees: List[str],
    location: str,
    recurrence: Union[None, str, List[str], Dict[str, Any]],  # <-- accept more shapes
    user_email: str,
    send_updates: str = "none",
) -> Dict[str, Any]:
    """
    Create a single event on calendar_id.
    - All-day: event_time == ''  -> use 'date' fields
    - Timed:   event_time != ''  -> use 'dateTime' + 'timeZone'
      If end_time is blank, default to +60 minutes.
    - notifications: if a list of ints -> popup overrides; if dicts -> pass as-is.
    """

    # -- attendees
    attendees = [{"email": a} for a in (invitees or []) if isinstance(a, str) and a.strip()]

    # -- reminders
    overrides: List[Dict[str, Any]] = []
    if notifications:
        for n in notifications:
            if isinstance(n, int):
                overrides.append({"method": "popup", "minutes": int(n)})
            elif isinstance(n, dict):
                overrides.append(n)
    reminders = {"useDefault": False, "overrides": overrides} if overrides else {"useDefault": True}

    body: Dict[str, Any] = {
        "summary": title or "Untitled",
        "description": description or "",
        "location": location or "",
        "reminders": reminders,
        "attendees": attendees or [],
    }

    # ------ NEW: recurrence normalizer ------
    def _to_rrule_list(rec: Union[None, str, List[str], Dict[str, Any]], *, is_all_day: bool) -> Optional[List[str]]:
        if not rec:
            return None
        if isinstance(rec, list) and all(isinstance(x, str) for x in rec):
            return rec  # already correct shape
        if isinstance(rec, str):
            r = rec.strip()
            if not r:
                return None
            return [r if r.upper().startswith("RRULE:") else f"RRULE:{r}"]
        if isinstance(rec, dict):
            parts: List[str] = []
            freq = rec.get("freq")
            if not freq:
                return None
            parts.append(f"FREQ={freq.upper()}")

            interval = rec.get("interval")
            if interval:
                parts.append(f"INTERVAL={int(interval)}")

            byday = rec.get("byDay") or rec.get("byday")
            if byday:
                parts.append(f"BYDAY={','.join(byday)}")

            if rec.get("byMonth"):
                parts.append(f"BYMONTH={','.join(str(m) for m in rec['byMonth'])}")
            if rec.get("byMonthDay"):
                parts.append(f"BYMONTHDAY={','.join(str(d) for d in rec['byMonthDay'])}")
            if rec.get("bySetPos"):
                parts.append(f"BYSETPOS={','.join(str(p) for p in rec['bySetPos'])}")

            if rec.get("count"):
                parts.append(f"COUNT={int(rec['count'])}")
            else:
                u = rec.get("until")
                if u:
                    # accept YYYY-MM-DD; normalize to RFC 5545, matching DTSTART type
                    if isinstance(u, str) and len(u) == 10 and u[4] == "-" and u[7] == "-":
                        y, m, d = u.split("-")
                        parts.append(f"UNTIL={y}{m}{d}" if is_all_day else f"UNTIL={y}{m}{d}T235959Z")
                    else:
                        # fallback: strip separators if someone passed an RFC-ish stamp
                        us = str(u).replace("-", "").replace(":", "")
                        parts.append(f"UNTIL={us}")
            return [f"RRULE:{';'.join(parts)}"]
        return None
    # ---------------------------------------

    # -- all-day vs timed
    is_all_day = not (event_time or "").strip()
    if is_all_day:
        body["start"] = {"date": event_date}
        body["end"] = {"date": end_date or event_date}
    else:
        def _hhmm_to_dt(d: str, t: str) -> dt.datetime:
            hh, mm = (t.split(":") + ["0"])[:2]
            return dt.datetime.strptime(f"{d} {hh}:{mm}", "%Y-%m-%d %H:%M")
        start_dt = _hhmm_to_dt(event_date, event_time)
        if (end_time or "").strip():
            end_dt = _hhmm_to_dt(end_date or event_date, end_time)
        else:
            end_dt = start_dt + dt.timedelta(minutes=60)
        body["start"] = {"dateTime": start_dt.isoformat(), "timeZone": timezone or "UTC"}
        body["end"]   = {"dateTime": end_dt.isoformat(),   "timeZone": timezone or "UTC"}

    # ------ CHANGED: set recurrence using the normalizer ------
    rlist = _to_rrule_list(recurrence, is_all_day=is_all_day)
    if rlist:
        body["recurrence"] = rlist
    # ----------------------------------------------------------
    _assert_creds(service)
    created = service.events().insert(
        calendarId=calendar_id,
        body=body,
        sendUpdates=send_updates,
    ).execute()
    return created