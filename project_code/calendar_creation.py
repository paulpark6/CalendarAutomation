from __future__ import annotations
from typing import Any, Dict, List, Optional
from googleapiclient.discovery import Resource

def get_user_default_timezone(service: Resource) -> str:
    """
    Fetch the user's default time zone from their Google Calendar settings.
    Falls back to "UTC" on failure.
    """
    try:
        settings = service.settings().get(setting="timezone").execute()
        tz = settings.get("value")
        if tz:
            return tz
    except Exception:
        pass
    
    # Fallback: try primary calendar
    try:
        cal = service.calendars().get(calendarId="primary").execute()
        return cal.get("timeZone", "UTC")
    except Exception:
        return "UTC"

def list_calendars(service: Resource) -> List[Dict[str, Any]]:
    """
    Return a list of the user's calendars.
    Returns: List of calendar list entries (summary, id, timeZone, primary, etc.)
    """
    calendars = []
    page_token = None
    while True:
        events = service.calendarList().list(pageToken=page_token).execute()
        for cal in events.get("items", []):
            calendars.append(cal)
        page_token = events.get("nextPageToken")
        if not page_token:
            break
    return calendars

def create_calendar(
    service: Resource, 
    summary: str, 
    time_zone: Optional[str] = None,
    default_reminders: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Create a new secondary calendar.
    
    Args:
        service: Google Calendar API service.
        summary: Name of the calendar.
        time_zone: Timezone ID (e.g., "America/New_York"). 
                   CRITICAL: If None, defaults to user's primary calendar timezone.
        default_reminders: List of default reminders (e.g., [{"method": "popup", "minutes": 10}]).
    
    Returns:
        The created calendar resource.
    """
    if not time_zone:
        time_zone = get_user_default_timezone(service)

    # 1. Create the calendar
    calendar_body = {
        "summary": summary,
        "timeZone": time_zone
    }
    created_calendar = service.calendars().insert(body=calendar_body).execute()
    calendar_id = created_calendar["id"]

    # 2. Set default reminders (requires patching the CalendarList entry)
    if default_reminders is not None:
        try:
            service.calendarList().patch(
                calendarId=calendar_id,
                body={"defaultReminders": default_reminders}
            ).execute()
        except Exception:
            # Warn silent/logging if setting defaults fails, but return created calendar
            pass
            
    return created_calendar

def update_calendar(
    service: Resource,
    calendar_id: str,
    summary: Optional[str] = None,
    description: Optional[str] = None,
    time_zone: Optional[str] = None,
    default_reminders: Optional[List[Dict[str, Any]]] = None
) -> Dict[str, Any]:
    """
    Update a calendar's metadata.
    
    Args:
        service: Google Calendar API service.
        calendar_id: ID of the calendar to update.
        summary: New name.
        description: New description.
        time_zone: New timezone.
        default_reminders: New default reminders list.
    
    Returns:
        The updated calendar resource.
    """
    # Calendar properties (Calendars resource)
    cal_patch = {}
    if summary is not None:
        cal_patch["summary"] = summary
    if description is not None:
        cal_patch["description"] = description
    if time_zone is not None:
        cal_patch["timeZone"] = time_zone
    
    updated_cal = {}
    if cal_patch:
        updated_cal = service.calendars().patch(calendarId=calendar_id, body=cal_patch).execute()

    # CalendarList properties (Reminders are per-user, on CalendarList resource)
    if default_reminders is not None:
        service.calendarList().patch(
            calendarId=calendar_id,
            body={"defaultReminders": default_reminders}
        ).execute()
        
    # Return the latest state (re-fetch if we only patched list)
    if not updated_cal:
        updated_cal = service.calendars().get(calendarId=calendar_id).execute()
        
    return updated_cal

def delete_calendar(service: Resource, calendar_id: str) -> Dict[str, str]:
    """
    Delete a calendar.
    If the user owns it -> Deletes permanently.
    If the user does not own it -> Unsubscribes.
    
    Returns:
        {"calendar_id": str, "action": "deleted" | "unsubscribed"}
    """
    try:
        # Check permissions first
        cal_list_entry = service.calendarList().get(calendarId=calendar_id).execute()
        role = cal_list_entry.get("accessRole")
        
        if role == "owner":
            service.calendars().delete(calendarId=calendar_id).execute()
            return {"calendar_id": calendar_id, "action": "deleted"}
        else:
            return unsubscribe_calendar(service, calendar_id)
            
    except Exception:
        # If we can't check role (e.g. already deleted or not in list), try delete anyway
        # or fallback to unsubscribe if delete fails.
        try:
            service.calendars().delete(calendarId=calendar_id).execute()
            return {"calendar_id": calendar_id, "action": "deleted"}
        except Exception:
            return unsubscribe_calendar(service, calendar_id)

def unsubscribe_calendar(service: Resource, calendar_id: str) -> Dict[str, str]:
    """
    Remove a calendar from the user's list (unsubscribe).
    """
    service.calendarList().delete(calendarId=calendar_id).execute()
    return {"calendar_id": calendar_id, "action": "unsubscribed"}
