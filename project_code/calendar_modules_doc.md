# Google Calendar Integration Modules

This directory contains the refactored modules for interacting with the Google Calendar API.  
**Core Principle**: Separation of concerns. `calendar_creation.py` handles the container (Calendar), and `event_creation.py` handles the items (Events).

---

## 1. `calendar_creation.py`

**Purpose**: Manage Calendar resources (create, update, delete, list).

### Functions

#### `get_user_default_timezone(service) -> str`
- **Description**: Fetches the authenticated user's default timezone from their Google Calendar settings. Defaults to "UTC" if not found.
- **Use Case**: Used automatically when creating calendars or events if no explicit timezone is provided.

#### `list_calendars(service) -> List[Dict]`
- **Description**: Returns all calendars in the user's "My Calendars" list.
- **Output**: List of dictionary objects containing keys like `id`, `summary`, `timeZone`, `primary`.

#### `create_calendar(service, summary, time_zone=None, default_reminders=None) -> Dict`
- **Description**: Creates a new secondary calendar.
- **Parameters**:
    - `summary`: Name of the calendar.
    - `time_zone`: (Optional) Timezone ID. **Defaults to user's primary timezone** if None.
    - `default_reminders`: (Optional) List of defaults, e.g., `[{'method': 'popup', 'minutes': 10}]`.
- **Output**: The full Calendar resource dict.

#### `update_calendar(service, calendar_id, ...) -> Dict`
- **Description**: Updates metadata (name, description, timezone) and default reminders.
- **Output**: Updated Calendar resource.

#### `delete_calendar(service, calendar_id) -> Dict`
- **Description**: Safely removes a calendar.
    - If **Owner**: Permanently deletes the calendar.
    - If **Reader/Writer**: Unsubscribes (removes from list) but does not delete the resource.
- **Output**: `{'calendar_id': '...', 'action': 'deleted' | 'unsubscribed'}`

---

## 2. `event_creation.py`

**Purpose**: Manage Event resources (create, update, delete, deduplicate).

### Key Concept: Deduplication
We prevent duplicates by generating a **deterministic key** based on the event's core fields (`title`, `start`, `end`, `location`, `recurrence`). This key is stored in the event's metadata (`extendedProperties.private.appCreatedKey`).

### Functions

#### `create_event(service, calendar_id, event, dedupe=True, if_exists='skip') -> Dict`
- **Description**: Creates a single event.
- **Parameters**:
    - `event`: Standard Google API Event dictionary (must have `summary`, `start`, `end`).
    - `dedupe`: If `True`, calculates a unique key and checks if it exists.
    - `if_exists`:
        - `'skip'`: Do nothing if duplicate found (returns `created=False`).
        - `'update'`: Update the existing event with new data.
- **Output**: `{'calendar_id': '...', 'event_id': '...', 'created': True/False, 'status': 'inserted'|'skipped'|'updated'}`

#### `update_event(service, calendar_id, event_id, patch) -> Dict`
- **Description**: Updates fields of an existing event.
- **Parameters**:
    - `patch`: Dictionary of fields to change.

#### `delete_event(service, calendar_id, event_id) -> None`
- **Description**: Deletes an event. Handles "Not Found" or "Already Deleted" errors gracefully.

#### `find_event_by_dedupe_key(service, calendar_id, dedupe_key) -> Optional[Dict]`
- **Description**: Helper to search for an event using our custom hash key.
