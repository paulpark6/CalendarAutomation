# ui.py Documentation

## Module Purpose
Provide a clean, 2-step user interface for calendar automation:
1. **Step 1:** Select/Create/Edit/Delete a calendar
2. **Step 2:** Create events from pasted schedule text

---

## Functions

### `show_login_page()`
**Purpose:** Display the Google Sign-In login page when user is not authenticated.

**Input:** None (uses Streamlit secrets for OAuth config)

**Output:** Streamlit UI with title, description, and Google Sign-In button

**When to use:** 
- Called in `main.py` when user has no credentials

**What it shows:**
- Title: "😪 LazyCal 🗓️"
- Text: "🔐 Sign in to connect your Google Calendar."
- Button: "Continue with Google" (links to OAuth)

---

### `step1_calendar_management(service)`
**Purpose:** STEP 1 interface - allow user to select, create, edit, or delete calendars.

**Input:**
- `service`: Google Calendar API service object (built from credentials)

**Output:** Streamlit UI with 3 tabs for calendar operations

**Saves to session state:**
- `st.session_state["target_calendar_id"]` - ID of selected calendar for events

**Features:**
- **📋 Select Calendar Tab:** Dropdown to choose target calendar, displays details
- **➕ Create New Tab:** Form to create new calendar with summary, description, location, timezone
- **✏️ Edit/Delete Tab:** Modify existing calendar or delete it

---

### `step2_event_creation(service)`
**Purpose:** STEP 2 interface - create events from pasted schedule JSON.

**Input:**
- `service`: Google Calendar API service object

**Output:** Streamlit UI with text area, event verification, and apply button

**Process:**
1. User pastes JSON from Gemini/ChatGPT
2. App parses and validates JSON
3. Shows event preview in expandable table
4. User clicks "✅ Apply All Events"
5. Events are created in selected calendar

**Expected JSON format:**
```json
[
  {
    "summary": "Meeting Title",
    "start": "2026-03-15T10:00:00",
    "end": "2026-03-15T11:00:00",
    "description": "Optional description"
  }
]
```

**Error handling:**
- Validates calendar selected in Step 1
- Validates JSON format
- Shows warning for failed events
- Displays success count with celebration

---

### `render_app(service)`
**Purpose:** Main app layout - combines Step 1 and Step 2 side-by-side.

**Input:**
- `service`: Google Calendar API service object

**Output:** Complete app with:
- Header with title and logout button
- Two columns (50% each):
  - **Left:** Step 1 (Calendar Management)
  - **Right:** Step 2 (Event Creation)

**Example:**
```python
if st.session_state.get("credentials"):
    service = st.session_state["service"]
    ui.render_app(service)
```

---

## Session State Variables

| Variable | Set by | Used in |
|----------|--------|---------|
| `credentials` | main.py (OAuth) | render_app() |
| `service` | main.py (post-login) | all functions |
| `target_calendar_id` | step1_calendar_management() | step2_event_creation() |
| `calendars_cache` | step1_calendar_management() | list refreshes |
| `user_email` | main.py | shown in header |

---

## Integration Points

**Imports:**
- `calendar_creation` - CRUD operations
- `event_creation` - event creation

**Called functions:**
- `calendar_creation.list_calendars()` - list all calendars
- `calendar_creation.get_user_default_timezone()` - timezone default
- `calendar_creation.create_calendar()` - create new
- `calendar_creation.update_calendar()` - edit existing
- `calendar_creation.delete_calendar()` - delete
- `event_creation.create_event()` - create events from JSON
- `auth.logout_and_delete_token()` - logout

---

## User Flow

```
1. Google Sign-In (show_login_page)
        ↓
2. Main App (render_app with 2 columns)
        ├─ Step 1: Select/Create Calendar
        └─ Step 2: Create Events from JSON
```

---

## Layout

```
┌─────────────────────────────────────────────┐
│  📅 Calendar Agent          [Log out]       │
├──────────────────┬──────────────────────────┤
│                  │                          │
│  Step 1:         │  Step 2:                 │
│  Calendar Mgmt   │  Event Creation         │
│  • Select        │  • Paste JSON           │
│  • Create        │  • Verify               │
│  • Edit/Delete   │  • Apply                │
│                  │                          │
└──────────────────┴──────────────────────────┘
```

---

## Key Features

✅ **Simplified Design** - Only 2 core steps  
✅ **Side-by-Side Layout** - Both steps visible at once  
✅ **No Primary Calendar** - Users can't accidentally edit main calendar  
✅ **Email Display** - Shows which account is logged in  
✅ **Smart Defaults** - Timezone auto-fills from user settings  
✅ **JSON Verification** - Preview all events before creation  
✅ **Error Handling** - Graceful failures with clear messages