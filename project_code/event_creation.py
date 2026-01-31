from __future__ import annotations
import hashlib
from typing import Any, Dict, List, Optional, Union
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from project_code.calendar_creation import get_user_default_timezone

# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _sha1(s: str) -> str:
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def generate_unique_key(
    title: str,
    start_iso: str,
    end_iso: Optional[str] = "",
    location: Optional[str] = "",
    recurrence: Optional[str] = ""
) -> str:
    """
    Generate a deterministic SHA-1 hash for deduplication.
    Fields used: title, start, end, location, recurrence.
    """
    raw = f"{title}|{start_iso}|{end_iso or ''}|{location or ''}|{recurrence or ''}"
    return _sha1(raw)

def find_event_by_dedupe_key(service: Resource, calendar_id: str, dedupe_key: str) -> Optional[Dict[str, Any]]:
    """
    Search for an event with the given dedupe key in extendedProperties.private.appCreatedKey.
    """
    try:
        response = service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty=f"appCreatedKey={dedupe_key}",
            maxResults=1,
            singleEvents=False # We want the master recurring event if it exists
        ).execute()
        items = response.get("items", [])
        if items:
            return items[0]
    except Exception:
        pass
    return None

# ---------------------------------------------------------------------
# Event CRUD
# ---------------------------------------------------------------------

def create_event(
    service: Resource,
    calendar_id: str,
    event: Dict[str, Any],
    *,
    dedupe: bool = True,
    dedupe_strategy: str = "extendedProperties",
    if_exists: str = "skip"  # "skip" | "update"
) -> Dict[str, Any]:
    """
    Create an event on the specified calendar.
    
    Args:
        service: Google Calendar API service.
        calendar_id: Target calendar ID.
        event: Dictionary representing the event resource (Google API format).
               Must contain 'summary' and 'start'/'end'.
        dedupe: Whether to check for duplicates.
        if_exists: Strategy if duplicate found ('skip' or 'update').
    
    Returns:
        Dict with keys: {calendar_id, event_id, iCalUID, htmlLink, created}
        'created' is Boolean (True if new, False if skipped/updated).
    """
    # 1. Validate / Normalize Timezone
    # If timeZone is missing in start/end for non-all-day events, fill valid default
    user_tz = None # lazy load
    
    for time_field in ["start", "end"]:
        if time_field in event and "dateTime" in event[time_field]:
            if "timeZone" not in event[time_field]:
                if not user_tz:
                    user_tz = get_user_default_timezone(service)
                event[time_field]["timeZone"] = user_tz

    # 2. Deduplication Logic
    dedupe_key = None
    if dedupe:
        # Extract fields for key generation
        title = event.get("summary", "")
        start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        end = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
        location = event.get("location", "")
        
        # Recurrence normalization (simple stringification for key)
        recurrence_raw = event.get("recurrence", [])
        recurrence_str = ",".join(recurrence_raw) if isinstance(recurrence_raw, list) else str(recurrence_raw)

        if title and start:
            dedupe_key = generate_unique_key(title, str(start), str(end), location, recurrence_str)
            
            # Inject key into private extended properties
            extended_props = event.get("extendedProperties", {})
            private_props = extended_props.get("private", {})
            private_props["appCreatedKey"] = dedupe_key
            extended_props["private"] = private_props
            event["extendedProperties"] = extended_props

            # Check existing
            existing_event = find_event_by_dedupe_key(service, calendar_id, dedupe_key)
            
            if existing_event:
                if if_exists == "skip":
                    return {
                        "calendar_id": calendar_id,
                        "event_id": existing_event["id"],
                        "iCalUID": existing_event.get("iCalUID"),
                        "htmlLink": existing_event.get("htmlLink"),
                        "created": False,
                        "status": "skipped"
                    }
                elif if_exists == "update":
                    return update_event(service, calendar_id, existing_event["id"], event)

    # 3. Insert Event (if not skipped)
    try:
        created_event = service.events().insert(
            calendarId=calendar_id,
            body=event
        ).execute()
        
        return {
            "calendar_id": calendar_id,
            "event_id": created_event["id"],
            "iCalUID": created_event.get("iCalUID"),
            "htmlLink": created_event.get("htmlLink"),
            "created": True,
            "status": "inserted"
        }
    except HttpError as e:
        # If we failed but it might be because we tried to set an ID that exists (rare here as we let Google assign IDs)
        raise e

def update_event(
    service: Resource,
    calendar_id: str,
    event_id: str,
    patch: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing event.
    
    Args:
        service: Google Calendar API service.
        calendar_id: Calendar ID.
        event_id: Event ID to update.
        patch: Dictionary of fields to update (patch semantics).
    """
    updated_event = service.events().patch(
        calendarId=calendar_id,
        eventId=event_id,
        body=patch
    ).execute()
    
    return {
        "calendar_id": calendar_id,
        "event_id": updated_event["id"],
        "iCalUID": updated_event.get("iCalUID"),
        "htmlLink": updated_event.get("htmlLink"),
        "created": False,
        "status": "updated"
    }

def delete_event(service: Resource, calendar_id: str, event_id: str) -> None:
    """
    Delete an event by ID.
    """
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as e:
        if e.resp.status == 410: # Already deleted (Gone)
            pass
        elif e.resp.status == 404: # Not found
            pass
        else:
            raise

def get_event(service: Resource, calendar_id: str, event_id: str) -> Dict[str, Any]:
    """
    Get a single event resource.
    """
    return service.events().get(calendarId=calendar_id, eventId=event_id).execute()
