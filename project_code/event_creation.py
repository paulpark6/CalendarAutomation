from __future__ import annotations
import hashlib
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import Resource
from googleapiclient.errors import HttpError
from project_code.calendar_creation import get_user_default_timezone, list_calendars

# ============================================================================
# HELPERS
# ============================================================================

def _sha1(s: str) -> str:
    """Compute SHA-1 hash of a string."""
    return hashlib.sha1(s.encode("utf-8")).hexdigest()


def _normalize_recurrence(recurrence: Optional[str]) -> str:
    """
    Normalize recurrence rules for consistent hashing.
    Sorts recurrence rules alphabetically to ensure order-independence.
    
    Args:
        recurrence: Comma-separated recurrence rules or empty string
        
    Returns:
        Sorted, comma-separated recurrence string
        
    Example:
        "EXRULE:NEVER,RRULE:FREQ=DAILY" → "EXRULE:NEVER,RRULE:FREQ=DAILY"
        "RRULE:FREQ=DAILY,EXRULE:NEVER" → "EXRULE:NEVER,RRULE:FREQ=DAILY"
    """
    if not recurrence:
        return ""
    
    # Split, sort, rejoin
    rules = recurrence.split(",")
    rules_sorted = sorted([r.strip() for r in rules])
    return ",".join(rules_sorted)


def _is_valid_timezone(tz: str) -> bool:
    """
    Validate timezone string is in IANA format.
    Basic validation: checks format, not exhaustive list.
    
    Args:
        tz: Timezone string (e.g., "America/New_York", "UTC")
        
    Returns:
        True if valid format, False otherwise
    """
    # Known invalid patterns
    if not tz or not isinstance(tz, str):
        return False
    
    # Basic IANA format: should contain only alphanumeric, _, and /
    import re
    if not re.match(r'^[A-Za-z0-9/_+-]+$', tz):
        return False
    
    # Must not be empty
    if tz == "":
        return False
    
    return True


def generate_unique_key(
    title: str,
    start_iso: str,
    end_iso: Optional[str] = "",
    location: Optional[str] = "",
    recurrence: Optional[str] = ""
) -> str:
    """
    Generate a deterministic SHA-1 hash for event deduplication.
    
    Hashes: title, start datetime, end datetime, location, and recurrence rules.
    Recurrence rules are NORMALIZED (sorted) to ensure order-independent hashing.
    
    Args:
        title: Event title (required)
        start_iso: Start datetime in ISO format (required)
        end_iso: End datetime in ISO format (optional)
        location: Event location (optional)
        recurrence: Comma-separated recurrence rules (optional)
        
    Returns:
        SHA-1 hex hash (40 characters)
        
    Example:
        >>> generate_unique_key("Meeting", "2026-03-15T10:00:00")
        "a1b2c3d4e5f6..."
        
        >>> # Order-independent:
        >>> key1 = generate_unique_key(..., recurrence="RRULE:FREQ=DAILY,EXRULE:NEVER")
        >>> key2 = generate_unique_key(..., recurrence="EXRULE:NEVER,RRULE:FREQ=DAILY")
        >>> key1 == key2  # True (both normalize to "EXRULE:NEVER,RRULE:FREQ=DAILY")
    """
    # Normalize recurrence rules (sort for consistency)
    recurrence_normalized = _normalize_recurrence(recurrence)
    
    # Build raw string with | separator
    raw = f"{title}|{start_iso}|{end_iso or ''}|{location or ''}|{recurrence_normalized}"
    return _sha1(raw)


def find_event_by_dedupe_key(
    service: Resource,
    calendar_id: str,
    dedupe_key: str
) -> Optional[Dict[str, Any]]:
    """
    Search for an event with the given deduplication key in a single calendar.
    
    Args:
        service: Google Calendar API service
        calendar_id: Calendar ID to search in
        dedupe_key: The SHA-1 hash key from generate_unique_key()
        
    Returns:
        Event dict if found, None otherwise
    """
    try:
        response = service.events().list(
            calendarId=calendar_id,
            privateExtendedProperty=f"appCreatedKey={dedupe_key}",
            maxResults=1,
            singleEvents=False  # Get master recurring event if it exists
        ).execute()
        items = response.get("items", [])
        if items:
            return items[0]
    except Exception:
        pass  # Silently fail - calendar might not exist or be inaccessible
    return None


def find_event_by_dedupe_key_cross_calendar(
    service: Resource,
    dedupe_key: str,
    exclude_calendar_id: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    Search for an event across all user's calendars using deduplication key.
    
    IMPORTANT: This makes multiple API calls (one per calendar).
    Use sparingly or cache results.
    
    Args:
        service: Google Calendar API service
        dedupe_key: The SHA-1 hash key from generate_unique_key()
        exclude_calendar_id: Optional calendar to skip in search
        
    Returns:
        Dict with keys: event_id, calendar_id, event (full object), or None
    """
    try:
        # Get all calendars
        calendars = list_calendars(service, exclude_primary=False)  # Include all
        
        # Search each calendar
        for cal in calendars:
            cal_id = cal.get("id")
            
            # Skip if excluded
            if exclude_calendar_id and cal_id == exclude_calendar_id:
                continue
            
            # Search this calendar
            event = find_event_by_dedupe_key(service, cal_id, dedupe_key)
            if event:
                return {
                    "calendar_id": cal_id,
                    "event_id": event.get("id"),
                    "event": event
                }
    except Exception:
        pass  # Silently fail
    
    return None

# ============================================================================
# EVENT CRUD
# ============================================================================

def create_event(
    service: Resource,
    calendar_id: str,
    event: Dict[str, Any],
    *,
    dedupe: bool = True,
    dedupe_strategy: str = "extendedProperties",
    dedupe_scope: str = "single_calendar",  # NEW: "single_calendar" or "all_calendars"
    if_exists: str = "skip"  # "skip" | "update"
) -> Dict[str, Any]:
    """
    Create an event on the specified calendar with optional deduplication.
    
    Args:
        service: Google Calendar API service
        calendar_id: Target calendar ID (required)
        event: Event dict in Google Calendar API format
               Must contain 'summary' and 'start'/'end'
        dedupe: Whether to check for duplicates (default True)
        dedupe_strategy: Strategy for deduplication (currently only "extendedProperties")
        dedupe_scope: Search scope for duplicates:
                      - "single_calendar": Only check target calendar (default, faster)
                      - "all_calendars": Search all user calendars (slower, more thorough)
        if_exists: Action if duplicate found:
                   - "skip": Don't create, return existing event
                   - "update": Update existing event with new data
    
    Returns:
        Dict with keys:
        - calendar_id: Target calendar ID
        - event_id: Event ID (created or existing)
        - iCalUID: Google-assigned unique ID
        - htmlLink: Link to event in Google Calendar
        - created: Boolean (True if new, False if skipped/updated)
        - status: "inserted" | "skipped" | "updated"
        
    Raises:
        ValueError: If timezone invalid or event missing required fields
        HttpError: If API call fails
    """
    # ─────────────────────────────────────────────────────────────
    # 1. VALIDATE & NORMALIZE TIMEZONE
    # ─────────────────────────────────────────────────────────────
    
    user_tz = None  # Lazy load only if needed
    
    for time_field in ["start", "end"]:
        if time_field in event and "dateTime" in event[time_field]:
            # Only for non-all-day events
            if "timeZone" not in event[time_field]:
                if not user_tz:
                    user_tz = get_user_default_timezone(service)
                
                # VALIDATE timezone before adding
                if not _is_valid_timezone(user_tz):
                    raise ValueError(
                        f"Invalid timezone: {user_tz}. "
                        f"Expected IANA format (e.g., 'America/New_York', 'UTC')"
                    )
                
                event[time_field]["timeZone"] = user_tz

    # ─────────────────────────────────────────────────────────────
    # 2. DEDUPLICATION LOGIC
    # ─────────────────────────────────────────────────────────────
    
    dedupe_key = None
    if dedupe:
        # Extract fields for key generation
        title = event.get("summary", "").strip()
        start = event.get("start", {}).get("dateTime") or event.get("start", {}).get("date")
        end = event.get("end", {}).get("dateTime") or event.get("end", {}).get("date")
        location = event.get("location", "").strip()
        
        # Normalize recurrence (handles order-independence)
        recurrence_raw = event.get("recurrence", [])
        recurrence_str = ",".join(recurrence_raw) if isinstance(recurrence_raw, list) else str(recurrence_raw)

        if title and start:
            # Generate dedupe key with NORMALIZED recurrence
            dedupe_key = generate_unique_key(
                title,
                str(start),
                str(end) if end else "",
                location,
                recurrence_str
            )
            
            # Inject key into private extended properties
            extended_props = event.get("extendedProperties", {})
            private_props = extended_props.get("private", {})
            private_props["appCreatedKey"] = dedupe_key
            extended_props["private"] = private_props
            event["extendedProperties"] = extended_props

            # Check for existing event
            if dedupe_scope == "single_calendar":
                # Fast: only check target calendar
                existing_event = find_event_by_dedupe_key(service, calendar_id, dedupe_key)
            elif dedupe_scope == "all_calendars":
                # Slow but thorough: search all calendars
                result = find_event_by_dedupe_key_cross_calendar(
                    service,
                    dedupe_key,
                    exclude_calendar_id=calendar_id  # Don't search target twice
                )
                existing_event = result.get("event") if result else None
                # Update calendar_id if event found elsewhere
                if result and if_exists in ["skip", "update"]:
                    calendar_id = result["calendar_id"]
            else:
                raise ValueError(f"Invalid dedupe_scope: {dedupe_scope}")
            
            # Handle existing event
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

    # ─────────────────────────────────────────────────────────────
    # 3. INSERT EVENT (if not skipped)
    # ─────────────────────────────────────────────────────────────
    
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
        raise e


def update_event(
    service: Resource,
    calendar_id: str,
    event_id: str,
    patch: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Update an existing event with patch (partial update).
    
    Args:
        service: Google Calendar API service
        calendar_id: Calendar ID
        event_id: Event ID to update
        patch: Dict of fields to update (Google API format)
        
    Returns:
        Dict with: calendar_id, event_id, iCalUID, htmlLink, created=False, status="updated"
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
    Gracefully handles 404 (not found) and 410 (gone) errors.
    
    Args:
        service: Google Calendar API service
        calendar_id: Calendar ID
        event_id: Event ID to delete
    """
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
    except HttpError as e:
        if e.resp.status == 410:  # Already deleted (Gone)
            pass
        elif e.resp.status == 404:  # Not found
            pass
        else:
            raise


def get_event(service: Resource, calendar_id: str, event_id: str) -> Dict[str, Any]:
    """
    Fetch a single event's full details.
    
    Args:
        service: Google Calendar API service
        calendar_id: Calendar ID
        event_id: Event ID
        
    Returns:
        Full Event resource dict
    """
    return service.events().get(calendarId=calendar_id, eventId=event_id).execute()