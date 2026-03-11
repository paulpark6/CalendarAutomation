# Google Calendar Integration Modules

This directory contains refactored modules for interacting with the Google Calendar API.

**Core Principle**: Separation of concerns.
- `calendar_creation.py` — Manages Calendar containers (create, update, delete, list calendars)
- `event_creation.py` — Manages Event items (create, update, delete, deduplication)

---

## 1. `calendar_creation.py`

**Purpose**: Manage Calendar resources (containers).

### Functions

#### `get_user_default_timezone(service: Resource) -> str`
- **Description**: Fetches the authenticated user's default timezone from Google Calendar settings.
- **Parameters**: `service` - Google Calendar API service
- **Returns**: Timezone string (e.g., "America/New_York") or "UTC" as fallback
- **Strategy**:
  1. First tries `settings().get(setting="timezone")`
  2. Falls back to primary calendar's timeZone
  3. Final fallback: "UTC"
- **Use Case**: Used when creating calendars or events if no explicit timezone is provided

#### `list_calendars(service: Resource) -> List[Dict[str, Any]]`
- **Description**: Returns all calendars in the user's calendar list.
- **Parameters**: `service` - Google Calendar API service
- **Returns**: List of calendar dictionaries with keys: `id`, `summary`, `timeZone`, `primary`, `description`, etc.
- **Implementation**: 
  - Handles pagination with `nextPageToken`
  - Returns all calendars, including subscribed ones

#### `create_calendar(service, summary, time_zone=None, default_reminders=None) -> Dict[str, Any]`
- **Description**: Creates a new secondary calendar.
- **Parameters**:
  - `service`: Google Calendar API service
  - `summary`: Name of the calendar (required)
  - `time_zone`: (Optional) Timezone ID (e.g., "America/New_York"). **Defaults to user's primary timezone** if None
  - `default_reminders`: (Optional) List of default reminders, e.g., `[{'method': 'popup', 'minutes': 10}]`
- **Returns**: Full Calendar resource dictionary with `id`, `summary`, `timeZone`, etc.
- **Implementation**:
  1. If `time_zone` is None, calls `get_user_default_timezone()` to fetch user's default
  2. Creates calendar body with summary + timeZone
  3. Calls `calendars().insert()` to create
  4. If `default_reminders` provided, patches `calendarList` with reminders
  5. Returns the created calendar
- **Side Effects**: May make 2 API calls (create + optional patch for reminders)

#### `update_calendar(service, calendar_id, summary=None, description=None, time_zone=None, default_reminders=None) -> Dict[str, Any]`
- **Description**: Updates metadata and settings of an existing calendar.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: ID of calendar to update
  - `summary`: (Optional) New calendar name
  - `description`: (Optional) New description
  - `time_zone`: (Optional) New timezone
  - `default_reminders`: (Optional) New default reminders list
- **Returns**: Updated Calendar resource dictionary
- **Implementation**:
  1. Builds patch body with provided fields (skips None values)
  2. Calls `calendars().patch()` for calendar properties (summary, description, timeZone)
  3. Calls `calendarList().patch()` for reminder properties
  4. Re-fetches calendar if only reminders were updated

#### `delete_calendar(service: Resource, calendar_id: str) -> Dict[str, str]`
- **Description**: Safely removes a calendar with smart role-based handling.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: ID of calendar to delete
- **Returns**: `{'calendar_id': '...', 'action': 'deleted' | 'unsubscribed'}`
- **Behavior**:
  - **If user owns calendar**: Permanently deletes it (calls `calendars().delete()`)
  - **If user doesn't own it**: Unsubscribes only (calls `calendarList().delete()`)
- **Implementation**:
  1. Checks `accessRole` from `calendarList().get()`
  2. If role is "owner" → deletes via `calendars().delete()`
  3. Else → unsubscribes via `calendarList().delete()`
  4. If role check fails, tries delete first, falls back to unsubscribe
- **Error Handling**: Graceful fallback if calendar already deleted

#### `unsubscribe_calendar(service: Resource, calendar_id: str) -> Dict[str, str]`
- **Description**: Removes a calendar from the user's list (unsubscribe, not delete).
- **Parameters**: `service`, `calendar_id`
- **Returns**: `{'calendar_id': '...', 'action': 'unsubscribed'}`
- **Use Case**: When user wants to stop viewing a shared calendar but not delete it

---

## 2. `event_creation.py`

**Purpose**: Manage Event resources (items) with built-in deduplication.

### Deduplication Strategy

We prevent duplicate events by generating a **deterministic SHA-1 hash key** based on event's core fields:
- `title` (summary)
- `start` (ISO datetime)
- `end` (ISO datetime)
- `location`
- `recurrence` (comma-separated list)

This key is stored in `extendedProperties.private.appCreatedKey`. When creating an event, we check if a matching key exists; if so, we skip or update based on strategy.

### Functions

#### `_sha1(s: str) -> str`
- **Description**: Helper to compute SHA-1 hash of a string.
- **Returns**: Hex string (e.g., "a1b2c3d4...")

#### `generate_unique_key(title, start_iso, end_iso="", location="", recurrence="") -> str`
- **Description**: Generate a deterministic SHA-1 hash for event deduplication.
- **Parameters**:
  - `title`: Event title (required)
  - `start_iso`: Start datetime in ISO format (required)
  - `end_iso`: End datetime in ISO format
  - `location`: Event location
  - `recurrence`: Recurrence rule (e.g., "RRULE:FREQ=DAILY")
- **Returns**: SHA-1 hex hash
- **Implementation**: Concatenates fields with `|` separator and hashes the result
- **Use Case**: Called before creating an event to check if it already exists

#### `find_event_by_dedupe_key(service: Resource, calendar_id: str, dedupe_key: str) -> Optional[Dict[str, Any]]`
- **Description**: Search for an existing event using the deduplication key.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: Calendar to search in
  - `dedupe_key`: The hash key from `generate_unique_key()`
- **Returns**: Event dictionary if found, None otherwise
- **Implementation**:
  - Calls `events().list()` with `privateExtendedProperty=appCreatedKey={dedupe_key}`
  - Returns first match (if any)
  - Silently returns None on error

#### `create_event(service, calendar_id, event, dedupe=True, dedupe_strategy="extendedProperties", if_exists="skip") -> Dict[str, Any]`
- **Description**: Create a single event with optional deduplication.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: Target calendar ID
  - `event`: Event dictionary (Google Calendar API format). Must have `summary` and `start`/`end`.
  - `dedupe`: (Optional, default=True) Whether to check for duplicates
  - `dedupe_strategy`: (Optional) Currently only supports "extendedProperties"
  - `if_exists`: (Optional) Strategy if duplicate found:
    - `"skip"` — Return the existing event without creating (default)
    - `"update"` — Update the existing event with new data
- **Returns**: Dictionary with keys:
  ```python
  {
    "calendar_id": str,
    "event_id": str,
    "iCalUID": str,
    "htmlLink": str,
    "created": bool,  # True if new, False if skipped/updated
    "status": "inserted" | "skipped" | "updated"
  }
  ```
- **Implementation**:
  1. **Normalize timezone**: If event has `dateTime` but no `timeZone`, adds user's default timezone
  2. **Generate dedupe key**: If `dedupe=True`, computes key from event fields and injects into `extendedProperties.private.appCreatedKey`
  3. **Check existing**: If dedupe enabled, searches for existing event
     - If found and `if_exists="skip"` → returns existing event (created=False)
     - If found and `if_exists="update"` → calls `update_event()` and returns result
  4. **Insert**: If not skipped, calls `events().insert()` to create
  5. Returns result with status
- **Error Handling**: Re-raises HttpError if insert fails (unless it's a duplicate key error which we handle)

#### `update_event(service, calendar_id, event_id, patch) -> Dict[str, Any]`
- **Description**: Update fields of an existing event.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: Calendar ID
  - `event_id`: Event ID to update
  - `patch`: Dictionary of fields to update (e.g., `{"summary": "New Title", "location": "Room 101"}`)
- **Returns**: Dictionary with `calendar_id`, `event_id`, `iCalUID`, `htmlLink`, `status="updated"`
- **Implementation**: Calls `events().patch()` with the provided fields
- **Note**: Preserves `extendedProperties` from original event

#### `delete_event(service: Resource, calendar_id: str, event_id: str) -> None`
- **Description**: Delete an event by ID.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: Calendar ID
  - `event_id`: Event ID to delete
- **Returns**: None
- **Implementation**: 
  - Calls `events().delete()`
  - **Gracefully handles** "410 Gone" (already deleted) and "404 Not Found" errors
  - Re-raises other HttpErrors
- **Use Case**: Safe to call even if event may have been deleted by another process

#### `get_event(service: Resource, calendar_id: str, event_id: str) -> Dict[str, Any]`
- **Description**: Fetch a single event's full details.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: Calendar ID
  - `event_id`: Event ID
- **Returns**: Full Event resource dictionary
- **Use Case**: Retrieve an event to inspect or update its details

---

## Usage Example

```python
from project_code import event_creation, calendar_creation
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

# Build service (from auth credentials)
service = build("calendar", "v3", credentials=creds)

# Create an event with deduplication
event = {
    "summary": "Team Standup",
    "start": {"dateTime": "2025-03-11T09:00:00", "timeZone": "America/New_York"},
    "end": {"dateTime": "2025-03-11T09:30:00", "timeZone": "America/New_York"},
    "location": "Room 101",
}

result = event_creation.create_event(
    service=service,
    calendar_id="primary",
    event=event,
    dedupe=True,
    if_exists="skip"
)

if result["created"]:
    print(f"Created event: {result['event_id']}")
else:
    print(f"Event already exists: {result['event_id']}")

# Create a calendar
new_cal = calendar_creation.create_calendar(
    service=service,
    summary="Project Q Planning",
    time_zone="America/Los_Angeles"
)

print(f"Calendar created: {new_cal['id']}")
```

---

## Known Issues & Improvements

### Issue 1: Timezone Normalization
- **Status**: Works, but could be more robust
- **Note**: Only adds timezone to `dateTime` fields; all-day events handled correctly
- **Improvement**: Could validate timezone is valid before inserting

### Issue 2: Deduplication Scope
- **Status**: Works within a single calendar
- **Limitation**: Cannot deduplicate across multiple calendars
- **Improvement**: Could accept optional cross-calendar dedupe flag

### Issue 3: Extended Properties Size Limit
- **Status**: Deduplication key is SHA-1 hash (fixed ~40 characters)
- **Note**: Google has limits on extended properties; current approach is safe
- **Improvement**: Could use shorter hash (e.g., first 16 chars of SHA-1) if needed

### Issue 4: Recurrence Rule Normalization
- **Status**: Raw comparison of recurrence arrays
- **Limitation**: Two functionally identical RRULE arrays in different orders would create separate keys
- **Improvement**: Normalize/sort recurrence rules before hashing

---

## Testing
- Unit tests should verify:
  - `generate_unique_key()` produces same output for same inputs
  - Duplicate detection works correctly
  - Timezone defaults applied properly
  - Error handling (404, 410, etc.) works
  - Undo functionality integrated