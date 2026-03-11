# Auth Package Documentation
**File:** `project_code/auth.py`

This module handles Google OAuth authentication and session management. It provides helpers for both credential validation and Web Flow (OAuth 2.0) for user login.

## Scopes

**Current OAuth Scopes Requested:**
```python
SCOPES = ["https://www.googleapis.com/auth/calendar"]
```

⚠️ **IMPORTANT**: The code currently only requests the Calendar scope. If you need to retrieve the user's email address, you **must add** the userinfo scope:
```python
SCOPES = [
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/userinfo.email"  # Add this!
]
```

## Functions

### `build_calendar_service(creds)`
- **Description**: Builds a Google Calendar API service instance. Automatically refreshes expired credentials.
- **Parameters**: `creds` (google.oauth2.credentials.Credentials)
- **Returns**: `googleapiclient.discovery.Resource`
- **Implementation**: Checks if credentials are expired and refresh_token exists, then calls refresh before building the service.

### `assert_service_has_identity(service)`
- **Description**: Validates that the service has valid credentials and can access the user's calendar list.
- **Returns**: The ID of the primary calendar (usually the user's email).
- **Raises**: `AssertionError` if auth fails with a descriptive message.
- **Implementation**: 
  - Extracts credentials from service._http
  - Makes a request to `users/me/calendarList` endpoint
  - Returns the primary calendar's ID
  - Handles SSL errors, network errors, and missing calendars gracefully

### `authorized_session_from_service(service)`
- **Description**: Extracts an `AuthorizedSession` from a service instance for making raw HTTP requests.
- **Returns**: `google.auth.transport.requests.AuthorizedSession`
- **Use Case**: When you need more control over HTTP requests than the discovery client provides.

### `web_authorization_url(client_id, client_secret, redirect_uri)`
- **Description**: Generates the Google OAuth authorization URL for the user to authorize your app.
- **Parameters**:
  - `client_id`: OAuth 2.0 Client ID from Google Cloud Console
  - `client_secret`: OAuth 2.0 Client Secret
  - `redirect_uri`: Where Google sends the user after authorization (must match registered URI exactly)
- **Returns**: Tuple of `(auth_url: str, state: str)`
- **Implementation**:
  - Creates a Flow object from client config
  - Sets access_type="offline" (to get refresh_token)
  - Sets prompt="consent" (force consent screen)
  - Returns the authorization URL
- **Use Case**: Step 1 of OAuth flow — generate the login URL to show the user.

### `web_exchange_code(client_id, client_secret, redirect_uri, code)`
- **Description**: Exchanges the authorization code returned by Google for OAuth credentials.
- **Parameters**:
  - `client_id`, `client_secret`, `redirect_uri`: Same as above
  - `code`: The `?code=xyz` parameter from Google's callback
- **Returns**: `google.oauth2.credentials.Credentials` object (contains access_token and refresh_token)
- **Implementation**:
  - Creates a Flow object
  - Calls fetch_token(code=code) to exchange
  - Returns the resulting credentials
- **Use Case**: Step 2 of OAuth flow — handle the OAuth callback and store credentials.

### `refresh_if_needed(creds: Credentials) -> Credentials`
- **Description**: Refreshes the access token if expired and a refresh_token is available.
- **Parameters**: `creds` - the Credentials object to potentially refresh
- **Returns**: Updated `Credentials` object
- **Side Effect**: Modifies the credentials in place
- **Note**: Safe to call even if credentials are not expired (checks before refreshing)

### `get_authenticated_email(service, creds=None) -> Optional[str]`
- **Description**: Retrieves the authenticated user's email address.
- **Parameters**:
  - `service`: Google Calendar API service instance
  - `creds`: (Optional) Credentials object for userinfo endpoint
- **Strategy**:
  1. If creds provided: tries `oauth2/v2/userinfo` endpoint
  2. Falls back to: reads primary calendar ID from calendarList
- **Returns**: Email string or None if unable to retrieve
- **Note**: Userinfo endpoint works better but requires the `userinfo.email` scope

### `get_default_calendar_timezone(service, calendar_id: str = "primary") -> str`
- **Description**: Fetches the timezone of a specific calendar.
- **Parameters**:
  - `service`: Google Calendar API service
  - `calendar_id`: Calendar ID (defaults to "primary" = user's main calendar)
- **Returns**: Timezone string (e.g., "America/New_York") or "UTC" as fallback
- **Implementation**: Calls `calendars().get()` endpoint and extracts the timeZone field

### `revoke_google_token(creds: Optional[Credentials]) -> bool`
- **Description**: Attempts to revoke the OAuth token with Google (best-effort logout).
- **Parameters**: `creds` - the Credentials to revoke
- **Strategy**:
  1. Prefers `refresh_token` (stronger invalidation)
  2. Falls back to `access_token` if refresh token not available
- **Returns**: `True` if a revoke attempt was made, `False` if no token found
- **Implementation**: Makes a POST request to `oauth2.googleapis.com/revoke`
- **Note**: Best-effort only — exceptions are silently caught. Google may not always complete revocation.

### `logout_and_delete_token(creds: Optional[Credentials]) -> None`
- **Description**: Wrapper that revokes the token. Designed for cloud deployments (no local file deletion).
- **Parameters**: `creds` - credentials to revoke
- **Use Case**: Called when user clicks "Log Out" button in Streamlit
- **Implementation**: Simply calls `revoke_google_token(creds)`

## Usage & Dependencies
- **Dependencies**: `google-auth`, `google-auth-oauthlib`, `google-api-python-client`, `requests`
- **Primary Users**: 
  - `streamlit_app/ui.py` — for login flow and rendering login page
  - `streamlit_app/main.py` — for session management and token refresh

## Design Principles
- **No Streamlit dependency**: This module is pure Python and doesn't import Streamlit, making it reusable for non-Streamlit apps (e.g., FastAPI backend).
- **Cloud-safe**: All functions work in cloud environments. No local file I/O except token revocation (best-effort).
- **Separation of Concerns**: OAuth logic is separate from UI rendering (UI lives in streamlit_app/ui.py).

## Known Issues & TODOs
- [ ] `SCOPES` currently missing `userinfo.email` — should be added if you need user email
- [ ] No caching of timezone lookups — could optimize by caching in session_state
- [ ] `authorized_session_from_service` could be used more consistently instead of creating new sessions