# 📅 Calendar Automation Project

A Streamlit-based application to automate Google Calendar management. It features a user-friendly interface for creating events, managing calendars, and using AI to parse natural language into calendar events.

---

## 🚀 First Time Setup

Follow these steps to get the app running locally.

### 1. Prerequisites
- **Python 3.10+** installed.
- **Git** installed.
- A **Google Cloud Project** with the **Google Calendar API** enabled.

### 2. Google Cloud configuration
1.  Go to the [Google Cloud Console](https://console.cloud.google.com/).
2.  Create a new project (or select an existing one).
3.  **Enable API**: Search for "Google Calendar API" and enable it.
4.  **Configure OAuth Consent Screen**:
    - User Type: **External** (unless you have a Workspace organization).
    - Add user emails to "Test Users" (important for External apps in testing).
5.  **Create Credentials**:
    - Go to **Credentials** > **Create Credentials** > **OAuth client ID**.
    - Application type: **Web application**.
    - **Authorized redirect URIs**: Add `http://localhost:8501`.
    - Click **Create** and copy your **Client ID** and **Client Secret**.
    - *Tip*: If you closed the popup, click the **pencil icon (EDit)** next to your specific OAuth 2.0 Client ID in the Credentials tab to view the Client ID and Secret again.

### 3. Application Configuration
Create a secrets file for Streamlit to store your credentials.

1.  Create a folder named `.streamlit` in the project root.
2.  Inside it, create a file named `secrets.toml`.
3.  Add the following content (replace with your actual values):

```toml
[google_oauth]
client_id = "YOUR_CLIENT_ID_HERE"
client_secret = "YOUR_CLIENT_SECRET_HERE"
redirect_uri = "http://localhost:8501"
```

### 4. Installation
Open your terminal in the project root:

```bash
# 1. Create a virtual environment
python3 -m venv sandboxenv

# 2. Activate it
# Mac/Linux:
source sandboxenv/bin/activate
# Windows:
# .\sandboxenv\Scripts\Activate.ps1

# 3. Install dependencies
pip install -r requirements.txt
```

---

## ▶️ How to Use

### Start the App
Run the Streamlit server:
```bash
streamlit run streamlit_app/main.py
```
A browser tab should open automatically at `http://localhost:8501`.

### Features
1.  **Home Dashboard**: View your upcoming events and active calendar status.
2.  **Manage Calendars**: Create new calendars or switch your "Active" calendar to keep your primary calendar clean.
3.  **Event Builder**:
    *   **Natural Language (AI)**: Describes events in plain English.
        *   *Note*: Currently relies on using external tools like [ChatGPT](https://chatgpt.com/g/g-68b888b9f56481919ecd05f8c647130d-event-parser-assistant) or [Gemini](https://gemini.google.com/gem/18-IbkHbrqKkymmHJmirEUGfulE2BujaF?usp=sharing) to generate the JSON, or a local model (Coming Soon).
    *   **Upload / Paste**: Paste JSON or upload `.txt` files directly.

### Authentication
The app uses a "Web Application" flow. When you click "Continue with Google", you'll be redirected to Google to sign in. 
*   **Note**: If you get a "403 Access Denied" error, ensure your email is added to the "Test Users" list in the Google Cloud Console.

---

## 🛠 Troubleshooting

-   **"Address already in use"**: If port 8501 is taken, Streamlit will try 8502. Update your `redirect_uri` in Google Cloud Console to match (e.g., `http://localhost:8502`).
-   **Auth Errors**: Verify that `secrets.toml` is in the correctly named `.streamlit` folder and has the exact `[google_oauth]` header.

---
**Note:** This is a Streamlit application designed to eventually evolve into a full web application.
