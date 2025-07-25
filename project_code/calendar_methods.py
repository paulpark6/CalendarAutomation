# method.py
"""
Utility functions for Google Calendar integration **plus** a minimal local cache.

Key features
============
* Custom IDs (`appCreated_<hash>`) to distinguish app‑created events.
* Duplicate handling (`if_exists`: "skip" | "update" | "error").
* Automatic notice appended to the description.
* Minimal local JSON cache (title / start / end / unique_key).
* Human‑readable search & deletion helpers.
"""

from __future__ import annotations
from project_code.auth import get_authenticated_email, get_user_default_timezone
import hashlib
import json
import os
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Union
from googleapiclient.errors import HttpError


# ── Constants ──────────────────────────────────────────────────────────────
APP_ID_PREFIX = "appcreated"
APP_NOTICE_LINE = "\n\n— This event was created automatically"
DEFAULT_OVERRIDES = [
    {"method": "popup", "minutes": 7 * 24 * 60},
    {"method": "email", "minutes": 1 * 24 * 60},
    {"method": "popup", "minutes": 1 * 24 * 60},
    {"method": "popup", "minutes": 2 * 24 * 60},
    {"method": "popup", "minutes": 3 * 24 * 60},
]
USER_DATA_DIR = "UserData"
os.makedirs(USER_DATA_DIR, exist_ok=True)

# ── Hash helpers ───────────────────────────────────────────────────────────

def _sha1(s: str) -> str:
    """
    Returns the SHA-1 hash of the input string as a hexadecimal string.

    Args:
        s (str): The input string to hash.

    Returns:
        str: The SHA-1 hash of the input string, in hexadecimal format.

    Example:
        >>> _sha1("hello")
        'f7ff9e8b7bb2b91af11b495e1eaca6c2843e7fef'
    """
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def generate_unique_key(
    title: str,
    start_iso: str,
    end_iso: Optional[str] = "",
    tz: Optional[str] = "",
) -> str:
    """
    Generate a deterministic unique key for an event based on its core identifying fields.

    This function creates a SHA-1 hash from the concatenation of the event's title,
    start time (ISO format), end time (ISO format), and timezone. The resulting key
    is used for duplicate detection and identification of events created by the app.

    Args:
        title (str): The title of the event.
        start_iso (str): The event's start time in ISO 8601 format.
        end_iso (Optional[str], optional): The event's end time in ISO 8601 format. Defaults to "".
        tz (Optional[str], optional): The timezone identifier (e.g., "America/Toronto"). Defaults to "".

    Returns:
        str: A SHA-1 hash string uniquely representing the event's identity.

    Example:
        >>> generate_unique_key("Meeting", "2024-06-10T10:00:00", "2024-06-10T11:00:00", "America/Toronto")
        'e3b0c44298fc1c149afbf4c8996fb92427ae41e4'
    """
    return _sha1("\x1f".join([title, start_iso, end_iso, tz]))

# ── Local cache helpers ────────────────────────────────────────────────────

def _cache_path(email: str) -> str:
    """
    Returns the file path for the local cache file that stores calendar events for a given user.

    The function constructs a path by joining the application's user data directory (USER_DATA_DIR)
    with a filename based on the user's email address. The resulting file is named
    "<email>_events.json" and is intended to store the user's event data in JSON format.

    Args:
        email (str): The user's email address.

    Returns:
        str: The full file path to the user's local event cache.
    """
    return os.path.join(USER_DATA_DIR, f"{email}_events.json")


def _load_cache(email: str) -> List[Dict[str, Any]]:
    """
    Load the local event cache for a specific user.

    Parameters:
        email (str): The user's email address. This is used to determine the path
            to the user's local cache file, which is expected to be named
            "<email>_events.json" and located in the application's user data directory.

    Purpose:
        This function retrieves the list of calendar events previously saved locally
        for the given user. It is used to access cached event data for operations
        such as duplicate detection, local event management, or offline access.

    Mutation:
        This function does not modify any files or data; it is a read-only operation.

    Returns:
        List[Dict[str, Any]]:
            - If the cache file for the user does not exist, returns an empty list ([]).
            - If the cache file exists and contains valid JSON data (a list of event records),
              returns that list.
            - If the cache file exists but is empty or contains invalid JSON, returns an empty list ([]).

    Behavior:
        - The function first determines the cache file path using the provided email.
        - If the file does not exist, it immediately returns an empty list.
        - If the file exists, it attempts to open and parse the file as JSON.
            - If parsing succeeds and the file contains a list, that list is returned.
            - If the file is empty, contains invalid JSON, or an OS error occurs during reading,
              the function returns an empty list.

    Example:
        >>> _load_cache("alice@example.com")
        [{'title': 'Meeting', 'start': '2024-06-10T10:00:00', ...}, ...]
        >>> _load_cache("nonexistent@example.com")
        []
    """
    path = _cache_path(email)
    if not os.path.exists(path):
        return []
    # if the file exists, load the file and return the events
    try:
        # open the file and load the events
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f) or [] # return the events in the file or an empty list if the file does not exist
    except (json.JSONDecodeError, OSError):
        # if the file is not valid JSON, return an empty list
        return []


def _save_cache(email: str, records: List[Dict[str, Any]]) -> None:
    """
    Low-level **persistence helper** - _blindly_ writes *records* to the user's
    JSON cache.

    Parameters
    ----------
    email : str
        Identifies the file path; the file is stored as
        ``UserData/<email>_events.json``.
    records : list[dict[str, Any]]
        The **entire** list of cached events that should appear in the file after
        the call returns.  Each dict follows the schema
        ``{"title", "start", "end", "unique_key"}``.

    Notes
    -----
    * This function **never merges or deduplicates**; it simply serialises the
      *records* list with ``json.dump`` (pretty-printed, UTF-8).
    * Callers are expected to prepare the list exactly as they want it
      persisted.  In normal usage you won't call this directly—see
      :func:`_store_minimal_local`, which handles dedup then delegates here.
    """
    with open(_cache_path(email), "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, ensure_ascii=False)


def _store_minimal_local(
    email: str,
    title: str,
    start_iso: str,
    end_iso: str,
    unique_key: str,
) -> None:
    """
    **Convenience wrapper** that keeps the local cache *deduplicated* and then
    persists it via :func:`_save_cache`.

    Workflow
    --------
    1.  Load the current cache with :func:`_load_cache`.
    2.  Remove any record that already has the same *unique_key*.
    3.  Append the new minimal record (``title``, ``start``, ``end``, ``unique_key``).
    4.  Call :func:`_save_cache` to overwrite the JSON file.

    By centralising the *merge → dedup → save* steps, every part of the code
    base can simply call ``_store_minimal_local(...)`` after creating or
    patching an event and be confident that the local cache stays in sync and
    free of duplicates.
    """
    records = _load_cache(email)
    records = [r for r in records if r["unique_key"] != unique_key]
    records.append(
        {
            "title": title,
            "start": start_iso,
            "end": end_iso,
            "unique_key": unique_key,
        }
    )
    _save_cache(email, records)


# ── Core creation ──────────────────────────────────────────────────────────
def ensure_calendar(service, name_or_id: str, tz: str = "UTC") -> str:
    """
    Ensures a calendar with the given name or ID exists and returns its calendarId.

    Parameters
    ----------
    service : googleapiclient.discovery.Resource
        Authenticated Google Calendar API service instance.
    name_or_id : str
        Either a calendarId (e.g., "primary" or an email address) or a calendar name (summary).
    tz : str, optional
        Timezone for the calendar if it needs to be created (default is "UTC").

    Returns
    -------
    str
        The calendarId of the found or newly created calendar.

    Behavior
    --------
    - If `name_or_id` is "primary" (case-insensitive) or looks like an email address (contains "@"),
      it is assumed to be a valid calendarId and is returned as-is.
    - Otherwise, treats `name_or_id` as a calendar name (summary):
        1. Searches the user's calendar list for a calendar whose summary matches (case-insensitive).
        2. If found, returns its calendarId.
        3. If not found, creates a new calendar with that summary and timezone, adds it to the user's
           calendar list, and returns its calendarId.
    """
    # If it's "primary" or looks like an email address, treat as ID
    if name_or_id.strip().lower() == "primary" or "@" in name_or_id:
        return name_or_id

    # Search for a calendar with matching summary (case-insensitive)
    page_token = None
    while True:
        cl = service.calendarList().list(pageToken=page_token).execute()
        for cal in cl.get("items", []):
            if cal.get("summary", "").strip().lower() == name_or_id.strip().lower():
                return cal["id"]
        page_token = cl.get("nextPageToken")
        if not page_token:
            break

    # Not found: create a new secondary calendar
    new_cal = service.calendars().insert(body={
        "summary": name_or_id,
        "timeZone": tz
    }).execute()
    # Add it to the user's calendar list so it appears in the UI
    try:
        service.calendarList().insert(body={"id": new_cal["id"]}).execute()
    except Exception:
        # If already in the list, ignore error
        pass
    return new_cal["id"]

def create_calendar_events(
    service,
    email: str,
    events: List[Dict[str, Any]],
    *,
    calendar_id: str = "primary",
    if_exists: str = "skip",          # pass‑through to create_event
    send_updates: str = "none",
    default_timezone: Optional[str] = None,
) -> List[Tuple[Dict[str, Any], str]]:
    """Create multiple events with one call.

    Parameters
    ----------
    service : googleapiclient.discovery.Resource
        Authorised Calendar service.
    email : str
        Current user's e-mail; forwarded to :pyfunc:`create_event` for caching.
    events : list[dict]
        Each dict may contain any subset of the keyword args accepted by
        :pyfunc:`create_event` (``title``, ``description``, ``start_iso`` …).
        Missing keys are filled with sensible defaults.
    calendar_id : str, default "primary"
        Target calendar. If not "primary" you may pre-create it outside or call
        a helper such as ``ensure_calendar`` first.
    if_exists : {"skip", "update", "error"}
        Duplicate-handling strategy forwarded to :pyfunc:`create_event`.
    send_updates : {"none", "externalOnly", "all"}
        Forwarded to :pyfunc:`create_event`.
    default_timezone : str | None
        If provided, used when an entry omits ``timezone_id``.  If *None*, falls
        back to ``get_user_default_timezone(service)``.

    Returns
    -------
    list[tuple]
        One ``(event_dict, status)`` tuple per input item, in the same order.

    Example
    -------
    >>> batch = [
    ...     {"title": "Daily stand-up", "start_iso": "2025-09-01T09:00:00Z"},
    ...     {"title": "Review", "description": "Quarterly review", ...},
    ... ]
    >>> create_calendar_events(service, "alice@example.com", batch)
    [(<event>, "inserted"), (<event>, "duplicate_skipped")]
    """

    tz_fallback = default_timezone or get_user_default_timezone(service)
    results: List[Tuple[Dict[str, Any], str]] = []

    for item in events:
        title = item.get("title") or "Untitled Event"
        start_iso = item.get("start_iso")
        if start_iso is None:
            # default to *today* at 09:00 UTC
            today = datetime.now(timezone.utc).date()
            start_iso = f"{today}T09:00:00Z"
        end_iso = item.get("end_iso") or start_iso  # default: 1‑hour not assumed; caller can adjust
        timezone_id = item.get("timezone_id") or tz_fallback

        # Pass through optional fields directly
        ev_dict, status = create_event(
            service,
            calendar_id=calendar_id,
            email=email,
            title=title,
            description=item.get("description", ""),
            start_iso=start_iso,
            end_iso=end_iso,
            timezone_id=timezone_id,
            invitees=item.get("invitees"),
            reminder_overrides=item.get("reminder_overrides"),
            send_updates=send_updates,
            if_exists=if_exists,
        )
        results.append((ev_dict, status))

    return results

def create_event(
        service,
        calendar_id: str,
        email: str,
        title: str,
        description: str,
        start_iso: str,
        end_iso: str,
        timezone_id: str,
        invitees: Optional[List[str]] = None,
        reminder_overrides: Optional[List[Dict[str, Any]]] = None,
        send_updates: str = "none",
        if_exists: str = "skip",  # "skip" | "update" | "error"
    ) -> Tuple[Dict[str, Any], str]:
    """Insert or update a Google Calendar event **with duplicate handling**.

    Returns
    -------
    (event_dict, status)
        * ``status == "inserted"``           - new event created.
        * ``status == "duplicate_skipped"`` - duplicate found, returned as is.
        * ``status == "duplicate_updated"`` - duplicate patched.

    Raises
    ------
    ValueError
        If a duplicate is found and ``if_exists == "error"``.
    HttpError
        For any unexpected Google API error (auth, quota, etc.).
    """
    end_iso = end_iso or start_iso
    invitees = invitees or []
    reminder_overrides = reminder_overrides or DEFAULT_OVERRIDES

    raw_key = generate_unique_key(title, start_iso, end_iso, timezone_id)
    custom_event_id = APP_ID_PREFIX + raw_key[:40]

    # ── Duplicate detection ────────────────────────────────────────────
    try:
        existing = service.events().get(calendarId=calendar_id, eventId=custom_event_id).execute()
        if if_exists == "skip":
            return existing, "duplicate_skipped"
        if if_exists == "error":
            raise ValueError(f"Duplicate event detected: {custom_event_id}")
    except HttpError as e:
        if e.resp.status != 404:
            raise
        existing = None  # safe to insert

    # ── Build request body ─────────────────────────────────────────────
    full_description = (description or "") + APP_NOTICE_LINE
    body: Dict[str, Any] = {
        "summary": title,
        "description": full_description,
        "start": {"dateTime": start_iso, "timeZone": timezone_id},
        "end": {"dateTime": end_iso, "timeZone": timezone_id},
        "reminders": {"useDefault": False, "overrides": reminder_overrides},
        "attendees": [{"email": addr} for addr in invitees],
        "source": {"title": "Scheduled via MyApp", "url": "https://myapp.example.com"},
    }

    if existing and if_exists == "update":
        event = service.events().patch(
            calendarId=calendar_id,
            eventId=custom_event_id,
            body=body,
            sendUpdates=send_updates,
        ).execute()
        status = "duplicate_updated"
    else:
        body["id"] = custom_event_id
        event = service.events().insert(
            calendarId=calendar_id,
            body=body,
            sendUpdates=send_updates,
        ).execute()
        status = "inserted"

    _store_minimal_local(email, title, start_iso, end_iso, raw_key)
    return event, status

# ── Search helpers ─────────────────────────────────────────────────────────

def find_events(
    service,
    calendar_id: str,
    title: Optional[str] = None,
    event_date: Optional[str] = None,  # YYYY-MM-DD
) -> List[Dict[str, Any]]:
    """Return events whose summary contains *title* and/or fall on *event_date*."""

    params: Dict[str, Any] = {
        "calendarId": calendar_id,
        "singleEvents": True,
        "showDeleted": False,
        "maxResults": 2500,
        "fields": "items(id,summary,start,end,description)",
    }
    if event_date:
        params.update({
            "timeMin": f"{event_date}T00:00:00Z",
            "timeMax": f"{event_date}T23:59:59Z",
        })

    matches: List[Dict[str, Any]] = []
    token: Optional[str] = None
    while True:
        if token:
            params["pageToken"] = token
        page = service.events().list(**params).execute()
        for ev in page.get("items", []):
            if title and title.lower() not in (ev.get("summary") or "").lower():
                continue
            matches.append(ev)
        token = page.get("nextPageToken")
        if not token:
            break
    return matches

# ── Deletion helpers ───────────────────────────────────────────────────────

def _delete_by_id(service, calendar_id: str, event_id: str, send_updates: str = "none") -> None:
    if not event_id.startswith(APP_ID_PREFIX):
        print("[Warn] Deleting an event without app prefix:", event_id)
    service.events().delete(calendarId=calendar_id, eventId=event_id, sendUpdates=send_updates).execute()


def delete_event_by_fields(
    service,
    calendar_id: str,
    email: str,
    title: Optional[str] = None,
    event_date: Optional[str] = None,
    send_updates: str = "none",
) -> Union[List[Dict[str, Any]], Dict[str, Any]]:
    """Delete using human‑readable fields and return what happened.

    * 0 matches → `[]`
    * 1 match   → event dict (deleted)
    * >1 match  → list of matches (caller must disambiguate)
    """

    matches = find_events(service, calendar_id, title=title, event_date=event_date)

    if not matches:
        return []
    if len(matches) == 1:
        ev = matches[0]
        _delete_by_id(service, calendar_id, ev["id"], send_updates)
        # Remove from cache
        records = _load_cache(email)
        records = [r for r in records if r["title"].lower() != (ev.get("summary") or "").lower()]
        _save_cache(email, records)
        return ev
    return matches

# ── Local cache inspection ────────────────────────────────────────────────

def list_local_records(email: str) -> List[Dict[str, Any]]:
    """Return minimal cached records for *email*."""
    return _load_cache(email)

