# project_code/calendar_creation.py
"""
Google Calendar Management Module

PURPOSE: Handle calendar CRUD operations (Create, Read, Update, Delete)
Used in Step 1 of the app: selecting/creating/editing calendars before event creation.

FUNCTIONS:
- get_user_default_timezone() -> Get user's default timezone
- list_calendars() -> List all non-primary calendars user owns/subscribes to
- create_calendar() -> Create new secondary calendar with summary, description, timeZone, location
- update_calendar() -> Update calendar metadata (summary, description, timeZone, location)
- delete_calendar() -> Delete or unsubscribe from a calendar
"""

from typing import Any, Dict, List, Optional
from googleapiclient.discovery import Resource


def get_user_default_timezone(service: Resource) -> str:
    """
    Get the user's default timezone from Google Calendar settings.
    Falls back to UTC if unavailable.
    
    Returns: str (timezone string like "America/New_York" or "UTC")
    """
    try:
        settings = service.settings().get(setting="timezone").execute()
        tz = settings.get("value")
        if tz:
            return tz
    except Exception:
        pass
    
    # Fallback: check primary calendar's timezone
    try:
        cal = service.calendars().get(calendarId="primary").execute()
        return cal.get("timeZone", "UTC")
    except Exception:
        return "UTC"


def list_calendars(service: Resource, exclude_primary: bool = True) -> List[Dict[str, Any]]:
    """
    Get all calendars the user has access to.
    
    Args:
        service: Google Calendar API service
        exclude_primary: If True, filters out the primary calendar (user's main calendar)
    
    Returns: List of calendar dicts with keys: id, summary, description, timeZone, primary, etc.
    """
    calendars = []
    page_token = None
    
    while True:
        result = service.calendarList().list(pageToken=page_token).execute()
        
        for cal in result.get("items", []):
            # Skip primary calendar if requested
            if exclude_primary and cal.get("primary"):
                continue
            calendars.append(cal)
        
        page_token = result.get("nextPageToken")
        if not page_token:
            break
    
    return calendars


def create_calendar(
    service: Resource,
    summary: str,
    description: str = "",
    time_zone: Optional[str] = None,
    location: str = ""
) -> Dict[str, Any]:
    """
    Create a new secondary calendar.
    
    Args:
        service: Google Calendar API service
        summary: Calendar title/name (required)
        description: What this calendar is for (optional)
        time_zone: Timezone (e.g. "America/New_York"). If None, uses user's default.
        location: Geographic location (optional)
    
    Returns: Created calendar object with fields: id, summary, description, timeZone, location
    """
    if not time_zone:
        time_zone = get_user_default_timezone(service)

    calendar_body = {
        "summary": summary,
        "description": description,
        "timeZone": time_zone,
    }
    
    if location:
        calendar_body["location"] = location

    created_calendar = service.calendars().insert(body=calendar_body).execute()
    return created_calendar


def update_calendar(
    service: Resource,
    calendar_id: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    time_zone: Optional[str] = None,
    location: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update an existing calendar's metadata.
    
    Args:
        service: Google Calendar API service
        calendar_id: ID of calendar to update
        summary: New calendar title (optional)
        description: New calendar description (optional)
        time_zone: New timezone (optional)
        location: New location (optional)
    
    Returns: Updated calendar object
    """
    update_body = {}
    
    if summary is not None:
        update_body["summary"] = summary
    if description is not None:
        update_body["description"] = description
    if time_zone is not None:
        update_body["timeZone"] = time_zone
    if location is not None:
        update_body["location"] = location
    
    if not update_body:
        # Nothing to update, return current state
        return service.calendars().get(calendarId=calendar_id).execute()
    
    updated_cal = service.calendars().patch(calendarId=calendar_id, body=update_body).execute()
    return updated_cal


def delete_calendar(service: Resource, calendar_id: str) -> Dict[str, str]:
    """
    Delete a calendar (if owner) or unsubscribe (if not owner).
    
    Args:
        service: Google Calendar API service
        calendar_id: ID of calendar to delete
    
    Returns: Dict with calendar_id and action ("deleted" or "unsubscribed")
    """
    try:
        # Check if user owns this calendar
        cal_entry = service.calendarList().get(calendarId=calendar_id).execute()
        role = cal_entry.get("accessRole", "reader")
        
        if role == "owner":
            # User owns it - delete permanently
            service.calendars().delete(calendarId=calendar_id).execute()
            return {"calendar_id": calendar_id, "action": "deleted"}
        else:
            # User doesn't own it - just unsubscribe
            service.calendarList().delete(calendarId=calendar_id).execute()
            return {"calendar_id": calendar_id, "action": "unsubscribed"}
    
    except Exception as e:
        # If we can't determine role, try delete first, then unsubscribe as fallback
        try:
            service.calendars().delete(calendarId=calendar_id).execute()
            return {"calendar_id": calendar_id, "action": "deleted"}
        except Exception:
            try:
                service.calendarList().delete(calendarId=calendar_id).execute()
                return {"calendar_id": calendar_id, "action": "unsubscribed"}
            except Exception:
                raise Exception(f"Failed to delete/unsubscribe calendar: {e}")