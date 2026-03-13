# calendar_creation.py Documentation

## Module Purpose
Handle all Google Calendar CRUD (Create, Read, Update, Delete) operations for the calendar management step of the app.

---

## Functions

### `get_user_default_timezone(service) -> str`
**Purpose:** Fetch the user's default timezone from Google Calendar settings.

**Input:** 
- `service`: Google Calendar API service object (built from credentials)

**Output:** 
- Timezone string (e.g., `"America/New_York"`, `"UTC"`)

**When to use:** 
- When creating a new calendar and the user doesn't specify a timezone
- Falls back to UTC if settings unavailable

**Example:**
```python
default_tz = get_user_default_timezone(service)
# Returns: "America/Los_Angeles"
```

---

### `list_calendars(service, exclude_primary=True) -> List[Dict]`
**Purpose:** Get all calendars the user has access to.

**Input:** 
- `service`: Google Calendar API service
- `exclude_primary`: If True, filters out the primary calendar (user's main @gmail.com calendar)

**Output:** 
- List of calendar dictionaries with keys: `id`, `summary`, `description`, `timeZone`, `location`, `primary`, etc.

**When to use:** 
- When populating the calendar selector dropdown in Step 1
- To show user's available calendars

**Example:**
```python
calendars = list_calendars(service, exclude_primary=True)
# Returns: [
#   {"id": "abc123@group.calendar.google.com", "summary": "Work", "timeZone": "UTC", ...},
#   {"id": "def456@group.calendar.google.com", "summary": "Personal", "timeZone": "America/New_York", ...}
# ]
```

---

### `create_calendar(service, summary, description="", time_zone=None, location="") -> Dict`
**Purpose:** Create a new secondary calendar with metadata.

**Input:**
- `service`: Google Calendar API service
- `summary` (required): Calendar title/name (e.g., "Work", "Projects")
- `description`: What this calendar is for (optional)
- `time_zone`: Timezone (e.g., "America/New_York"). If None, uses user's default (optional)
- `location`: Geographic location (optional, rarely used)

**Output:** 
- Created calendar dictionary with fields: `id`, `summary`, `description`, `timeZone`, `location`

**When to use:** 
- When user clicks "✅ Create Calendar" in the Create New tab

**Example:**
```python
new_cal = create_calendar(
    service,
    summary="Q1 Projects",
    description="Quarterly project deadlines",
    time_zone="America/New_York"
)
# Returns: {"id": "new_id_123", "summary": "Q1 Projects", ...}
```

---

### `update_calendar(service, calendar_id, summary=None, description=None, time_zone=None, location=None) -> Dict`
**Purpose:** Update an existing calendar's metadata (rename, change description, timezone, etc.).

**Input:**
- `service`: Google Calendar API service
- `calendar_id`: ID of calendar to update
- `summary`: New calendar title (optional - pass None to skip)
- `description`: New description (optional)
- `time_zone`: New timezone (optional)
- `location`: New location (optional)

**Output:** 
- Updated calendar dictionary

**When to use:** 
- When user clicks "💾 Save Changes" in the Edit/Delete tab

**Example:**
```python
updated = update_calendar(
    service,
    calendar_id="abc123@group.calendar.google.com",
    summary="Q1 Roadmap",
    description="Updated description"
)
```

---

### `delete_calendar(service, calendar_id) -> Dict`
**Purpose:** Delete a calendar (if user owns it) or unsubscribe (if user doesn't own it).

**Input:**
- `service`: Google Calendar API service
- `calendar_id`: ID of calendar to delete

**Output:** 
- Dictionary: `{"calendar_id": "...", "action": "deleted" | "unsubscribed"}`

**When to use:** 
- When user clicks "🗑️ Delete This Calendar" in the Danger Zone

**Example:**
```python
result = delete_calendar(service, "abc123@group.calendar.google.com")
# Returns: {"calendar_id": "abc123@group.calendar.google.com", "action": "deleted"}
```

---

## Usage in UI

### In `step1_calendar_management()`:
1. **Tab 1 (Select):** Uses `list_calendars()` to populate dropdown
2. **Tab 2 (Create):** Uses `get_user_default_timezone()` for default, then `create_calendar()`
3. **Tab 3 (Edit/Delete):** Uses `list_calendars()` to select calendar, then `update_calendar()` or `delete_calendar()`

---

## Error Handling
- All functions have built-in error handling with fallbacks
- `get_user_default_timezone()` falls back to "UTC"
- `delete_calendar()` tries delete first, then unsubscribe as fallback
- If errors occur, they're caught and displayed to user via `st.error()`