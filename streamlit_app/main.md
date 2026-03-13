# LazyCal - Simplified Calendar Agent

## Overview

**LazyCal** is a Streamlit web app that automates calendar event creation using Google Calendar API.

The app has a **simple 2-step flow:**
1. **Step 1:** Select or create a calendar
2. **Step 2:** Paste a schedule (JSON format) and create events

---

## Architecture

### Project Structure
```
CalendarProject/
├── streamlit_app/
│   ├── __init__.py
│   ├── main.py               # Entry point, OAuth handling, session management
│   └── ui.py                 # UI components for 2-step flow
│
├── project_code/
│   ├── __init__.py
│   ├── auth.py               # Google OAuth authentication
│   ├── calendar_creation.py  # Calendar CRUD operations
│   └── event_creation.py     # Event creation from JSON
│
├── .streamlit/
│   └── secrets.toml          # OAuth credentials (git-ignored)
│
├── requirements.txt          # Python dependencies
└── run_app.py               # Streamlit entry point
```

---

## Module Responsibilities

### 1. `auth.py` - Authentication
**Handles:** Google OAuth 2.0 flow (server-side, no PKCE)

**Key Functions:**
- `web_authorization_url()` - Generate Google login link
- `web_exchange_code()` - Exchange code for access token
- `build_calendar_service()` - Create Calendar API client
- `logout_and_delete_token()` - Revoke token

**Used by:** `main.py`

---

### 2. `calendar_creation.py` - Calendar Operations
**Handles:** All calendar CRUD (Create, Read, Update, Delete)

**Key Functions:**
- `list_calendars()` - Get all non-primary calendars
- `get_user_default_timezone()` - Get user's timezone
- `create_calendar()` - Create new calendar
- `update_calendar()` - Edit calendar metadata
- `delete_calendar()` - Delete or unsubscribe from calendar

**Used by:** `ui.py` (Step 1)

---

### 3. `event_creation.py` - Event Operations
**Handles:** Creating events from JSON with deduplication

**Key Functions:**
- `create_event()` - Create single event (with duplicate checking)
- Other event helpers

**Used by:** `ui.py` (Step 2)

---

### 4. `ui.py` - User Interface
**Handles:** 2-step UI flow

**Key Functions:**
- `show_login_page()` - Login screen
- `step1_calendar_management()` - Calendar selection/creation/editing
- `step2_event_creation()` - Event creation from JSON
- `render_app()` - Main app layout (both steps side-by-side)

**Used by:** `main.py`

---

### 5. `main.py` - Entry Point
**Handles:** OAuth flow, authentication, session management

**Key Steps:**
1. Check if user is logged in
2. If not → show `show_login_page()`
3. If yes → build Calendar service
4. Refresh token if expired
5. Call `render_app()` with service

---

## User Flow

```
┌─────────────────────────────────────────┐
│ User visits app                         │
└──────────────┬──────────────────────────┘
               │
               ▼
       ┌──────────────────┐
       │ Has credentials? │
       └─────┬────────┬───┘
             │        │
            NO       YES
             │        │
             ▼        ▼
      ┌──────────┐   ┌──────────────────┐
      │  Login   │   │  Main App        │
      │  Page    │   │  (2-step flow)   │
      └──────────┘   └──────────────────┘
           │                │
           │           Step 1 | Step 2
           │          (50%)   | (50%)
           ▼
      [Google OAuth]
           │
           ▼
      [Callback to app]
           │
           ▼
      [Save credentials]
           │
           ▼
      [Show main app]
```

---

## The 2-Step Flow

### Step 1: Calendar Management (Left Column)

**User can:**
- **Select** existing calendar
- **Create** new calendar (with title, description, timezone, location)
- **Edit** calendar metadata
- **Delete** calendar

**Saves:** Calendar ID to `st.session_state["target_calendar_id"]`

**Components:**
- Uses all functions from `calendar_creation.py`
- 3 tabs: Select / Create / Edit-Delete
- Shows logged-in email address

### Step 2: Event Creation (Right Column)

**User can:**
- **Paste** JSON schedule (from Gemini or ChatGPT)
- **Verify** events in expandable table
- **Apply** all events to calendar selected in Step 1

**Requires:** Calendar selected in Step 1

**Components:**
- Text area for JSON input
- Event preview/verification
- Progress bar during creation
- Success/error messages

**JSON Format:**
```json
[
  {
    "summary": "Meeting",
    "start": "2026-03-15T10:00:00",
    "end": "2026-03-15T11:00:00",
    "description": "Optional"
  }
]
```

---

## Data Flow

```
┌──────────────────────────────┐
│  Google Calendar API         │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  auth.py (build_service)     │
│  -> Credentials + Service    │
└────────────┬─────────────────┘
             │
             ▼
┌──────────────────────────────┐
│  main.py                     │
│  -> Save in st.session_state │
└────────────┬─────────────────┘
             │
        ┌────┴─────┐
        │           │
        ▼           ▼
   Step 1      Step 2
   ├─ calendar_creation.py    ├─ event_creation.py
   │ (CRUD ops)              │ (Create from JSON)
   └─ ui.render()            └─ ui.render()
```

---

## Session State Variables

| Variable | Type | Set by | Used in |
|----------|------|--------|---------|
| `credentials` | Credentials | main.py (OAuth) | all |
| `service` | API Service | main.py (post-login) | all |
| `user_email` | String | main.py (post-login) | ui.py (display) |
| `target_calendar_id` | String | step1 | step2 |
| `calendars_cache` | List | step1 | step1 (cache) |

---

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Google Cloud OAuth
1. Create OAuth 2.0 Web Application credentials in Google Cloud Console
2. Set authorized redirect URIs:
   - `http://localhost:8501/` (local testing)
   - `https://lazycal.streamlit.app/` (production)

### 3. Set Secrets
Create `.streamlit/secrets.toml`:
```toml
[google_oauth]
client_id = "YOUR_CLIENT_ID"
client_secret = "YOUR_CLIENT_SECRET"

[app]
mode = "local"
local_redirect_uri = "http://localhost:8501/"
cloud_redirect_uri = "https://lazycal.streamlit.app/"
```

### 4. Run Locally
```bash
streamlit run run_app.py
```

### 5. Deploy to Streamlit Cloud
1. Push to GitHub
2. Connect repo to Streamlit Cloud
3. Add secrets in Streamlit Cloud Settings
4. Deploy

---

## Key Design Decisions

✅ **No PKCE** - Server-side OAuth is simpler  
✅ **Exclude Primary** - Users can't accidentally modify main calendar  
✅ **Side-by-Side Steps** - Both actions visible at once  
✅ **JSON Input** - Structured format prevents parsing errors  
✅ **Simple Tabs** - Clear organization without clutter  
✅ **Email Display** - User always knows which account is active  
✅ **Timezone Auto-Fill** - Default to user's settings  
✅ **Deduplication** - Prevent duplicate events

---

## Future Improvements

- [ ] Direct LLM integration (Hugging Face) instead of external Gemini/ChatGPT
- [ ] File upload support (PDF, Word, text files)
- [ ] Event editing (not just creation)
- [ ] Event deletion interface
- [ ] Calendar sharing/permissions
- [ ] Recurring event support
- [ ] Event reminders configuration
- [ ] Calendar color customization
- [ ] Batch operations (create/delete multiple at once)

---

## Troubleshooting

### "Missing code verifier" Error
**Cause:** PKCE mismatch
**Solution:** Ensure `auth.py` doesn't send `code_challenge` (it shouldn't)

### SSL Error on Identity Check
**Cause:** API call failing on Streamlit Cloud
**Solution:** Skip identity check after token exchange (credentials already validated)

### "No calendars found"
**Cause:** User only has primary calendar
**Solution:** Remind user to create a secondary calendar first

### Timezone Not Saving
**Cause:** Invalid IANA timezone string
**Solution:** Validate timezone format before creating calendar

---

## Support

For issues, check:
1. Google Cloud OAuth configuration
2. Streamlit secrets setup
3. Network connectivity
4. Token expiration (refreshes automatically)

---

## Summary

LazyCal is a **minimal, focused calendar automation tool** with:
- Clean 2-step UI
- Simple Google OAuth
- Calendar CRUD operations
- Event creation from JSON
- Session-based state management

**Goal:** Make calendar management effortless!