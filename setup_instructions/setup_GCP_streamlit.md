# Google Cloud Platform Setup Guide for LazyCal

This guide walks you through setting up Google Cloud Platform (GCP) for the LazyCal Streamlit application, including OAuth 2.0 credentials and configuration for both local development and cloud deployment.

---

## Table of Contents

1. [Create a New GCP Project](#create-a-new-gcp-project)
2. [Enable Google Calendar API](#enable-google-calendar-api)
3. [Create OAuth 2.0 Credentials](#create-oauth-20-credentials)
4. [Configure OAuth Consent Screen](#configure-oauth-consent-screen)
5. [Set Up Redirect URIs](#set-up-redirect-uris)
6. [Configure Local Environment (.streamlit/secrets.toml)](#configure-local-environment)
7. [Configure Streamlit Cloud Secrets](#configure-streamlit-cloud-secrets)
8. [Test Your Setup](#test-your-setup)

---

## Create a New GCP Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click the **Project dropdown** (top left, next to "Google Cloud")
3. Click **"New Project"**
4. **Project name**: Enter `LazyCal` (or your preferred name)
5. **Parent resource**: Leave as "No organization" (unless using Workspace)
6. Click **Create**
7. Wait for the project to be created (usually takes a few seconds)
8. Once created, you'll be automatically switched to the new project

---

## Enable Google Calendar API

1. In the new project, go to **APIs & Services → Library**
2. Search for **"Google Calendar API"**
3. Click on the **Google Calendar API** result
4. Click the blue **Enable** button
5. Wait for it to finish enabling (you'll see "API enabled" confirmation)

---

## Create OAuth 2.0 Credentials

This section has two parts:
1. **Configure the OAuth Consent Screen** (what users see when they log in)
2. **Create the OAuth Client ID** (your app's credentials)

---

### Part 1: Configure the OAuth Consent Screen

#### Step 1A: Check the Overview

1. Go to **APIs & Services → OAuth consent screen**
2. Click on the **Overview** tab (on the left sidebar)
3. You'll see a summary of your consent screen status
   - If this is your first time, it should be empty or show "Not yet configured"
   - **This is just informational** — helps you understand what's been set up
4. **Continue to Branding** (next step)

#### Step 1B: Configure Branding (App Name & Contact Info)

1. Click on the **Branding** tab (left sidebar)
2. You'll see a form to fill out. Complete these fields:
   - **App name**: `LazyCal`
   - **App logo** (optional): You can skip this for now
   - **App domain** (optional): You can skip this
   - **User support email**: Enter your email address (this appears on the login screen)
   - **Developer contact information**:
     - Enter your email address in the email field
3. Scroll down and click **Save and Continue**

#### Step 1C: Set User Type

1. Click on the **Audience** tab (left sidebar)
2. You'll see **"User type"** is already set to **"External"** (good!)
   - If it's not set to External, click **Edit** next to it and select **External**
3. You can leave this tab as is

#### Step 1D: Add API Scopes (Permissions)

1. Click on the **Data access** tab (left sidebar)
2. You'll see a section that says:
   - **"Scopes express the permissions that you request users to authorise for your app"**
3. Click the blue **"Add or remove scopes"** button
4. A dialog will open with available scopes
5. Search for and select BOTH of these:
   - `https://www.googleapis.com/auth/calendar` (allows reading/writing Google Calendar events)
   - `https://www.googleapis.com/auth/userinfo.email` (allows reading the user's email address)
6. Click **Update** to add them
7. You should see the scopes now appear in the "Your sensitive scopes" section
8. Click **Save** at the bottom to confirm

#### Step 1E: Add Test Users (Critical!)

1. You should now be on the **Audience** tab (if not, click it in the left sidebar)
   - Don't worry, you haven't created your OAuth Client ID yet — this tab also manages test users
2. Look for **"Test users"** section (scroll if needed)
3. Click **Add users** (or the **+** button)
4. A dialog will appear asking for email addresses
   - Enter the **email address(es)** you'll use to test the app:
     - Your personal email (for local testing)
     - Any colleagues or other test emails
   - **Make sure to add at least YOUR email**
5. Click **Add** to add the email(s)
6. You should see your email(s) appear in the "Test users" list

---

### Part 2: Create the OAuth Client ID

#### Step 2A: Create a New OAuth Client ID

1. Go to **APIs & Services → Credentials** (different from OAuth consent screen)
2. Click **+ Create Credentials** (top of the page)
3. Click **OAuth client ID**
4. A dialog will ask **"Application type"**
   - Select **Web application**
5. Fill in the form:
   - **Name**: `LazyCal Web` (this is just a label for you to identify this credential)
   - Leave other fields blank for now

#### Step 2B: Add Redirect URIs

1. Scroll down to **Authorized redirect URIs** section
2. Click **Add URI**
3. Enter the first redirect URI: `http://localhost:8501/`
4. Click **Add URI** again
5. Enter the second redirect URI: `https://lazycal.streamlit.app/`
6. You should now see BOTH URIs listed:
   - `http://localhost:8501/`
   - `https://lazycal.streamlit.app/`

#### Step 2C: Save and Copy Your Credentials

1. Click **Create**
2. A popup will appear showing your **Client ID** and **Client Secret**
   - **IMPORTANT**: Copy these values somewhere safe (notepad, password manager, etc.)
   - You'll need them in the next steps
   - ⚠️ You can only see the Client Secret once — if you close this, you'll need to create a new credential
3. After copying, you can close the popup

#### Step 2D: Verify Your Client ID Shows in Credentials List

1. You should still be on the **APIs & Services → Credentials** page
2. Scroll down to **OAuth 2.0 Client IDs** section
3. You should see **"LazyCal Web"** listed with your Client ID
4. ✅ **This confirms your credential was created successfully**

---

### Summary of What You Just Did

| What | Where | Purpose |
|------|-------|---------|
| Set app name & contact email | Branding tab | Users see this on login screen |
| Set user type | Audience tab | Defines who can use your app (External = anyone with a Google account) |
| Added API scopes | Data access tab | Tells Google what your app can access (Calendar + Email) |
| Added test users | Clients tab | Allows those emails to log in during testing |
| Created OAuth Client ID | Credentials page | Generated your app's Client ID & Secret |
| Added redirect URIs | OAuth Client ID settings | Tells Google where to send users after login |

---

### Next Steps

You now have:
- ✅ OAuth Consent Screen configured
- ✅ OAuth Client ID created
- ✅ Client Secret saved

Continue to the next section: **[Configure Local Environment](#configure-local-environment)** to set up your `.streamlit/secrets.toml` file with these credentials.

---

## Set Up Redirect URIs

### Step 1: Create OAuth Client ID

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials** → **OAuth client ID**
3. **Application type**: Select **Web application**
4. **Name**: Enter `LazyCal Web` (or similar)
5. Under **Authorized redirect URIs**, click **Add URI** and add BOTH:
   - `http://localhost:8501/` (for local development)
   - `https://lazycal.streamlit.app/` (for cloud deployment)
6. Click **Create**
7. You'll see a popup with your **Client ID** and **Client Secret**
   - **Copy these values immediately** and save them securely
   - You can close the popup; you can retrieve them anytime from the Credentials page

---

## Configure Local Environment

### Create `.streamlit/secrets.toml`

1. In your project root, create a folder named `.streamlit` (if it doesn't exist)
2. Inside `.streamlit`, create a file named `secrets.toml`
3. Add the following content (replace with your actual values):

```toml
[google_oauth]
client_id = "YOUR_CLIENT_ID_HERE"
client_secret = "YOUR_CLIENT_SECRET_HERE"

[app]
mode = "local"
local_redirect_uri = "http://localhost:8501/"
cloud_redirect_uri = "https://lazycal.streamlit.app/"
```

**Where to find your values:**
- **client_id**: From the popup when you created the OAuth Client ID (looks like `12345678-abcdef.apps.googleusercontent.com`)
- **client_secret**: From the same popup
- Keep the redirect URIs exactly as shown (including the trailing slash)

### Add to `.gitignore`

Make sure `.streamlit/secrets.toml` is in your `.gitignore` to avoid committing secrets to GitHub:

```
.streamlit/secrets.toml
```

---

## Configure Streamlit Cloud Secrets

When you deploy to Streamlit Cloud, the app won't have access to your local `secrets.toml`. You need to configure secrets in the Streamlit Cloud dashboard.

### Step 1: Deploy Your App to Streamlit Cloud

1. Push your code to GitHub (with the `.streamlit/secrets.toml` in `.gitignore`)
2. Go to [Streamlit Cloud](https://share.streamlit.io/)
3. Click **"New app"**
4. Connect your GitHub repo, select the branch, and choose `streamlit_app/main.py` as the entry point
5. Streamlit Cloud will start deploying your app

### Step 2: Add Secrets in Streamlit Cloud Dashboard

1. Once your app is deployed (or while deploying), go to your app's settings
2. Click **Settings** (bottom right or top right)
3. Click **"Secrets"** in the left sidebar
4. Paste the following content (with your actual Client ID and Secret):

```toml
[google_oauth]
client_id = "YOUR_CLIENT_ID_HERE"
client_secret = "YOUR_CLIENT_SECRET_HERE"

[app]
mode = "cloud"
local_redirect_uri = "http://localhost:8501/"
cloud_redirect_uri = "https://lazycal.streamlit.app/"
```

**Important:** The `mode = "cloud"` tells your app to use the cloud redirect URI in the OAuth flow.

5. Click **Save**
6. Streamlit Cloud will automatically redeploy your app with the new secrets

---

## Test Your Setup

### Local Testing

1. Activate your Python virtual environment:
   ```bash
   source sandboxenv/bin/activate  # macOS/Linux
   # or
   .\sandboxenv\Scripts\Activate.ps1  # Windows
   ```

2. Run the Streamlit app:
   ```bash
   streamlit run streamlit_app/main.py
   ```

3. A browser should open to `http://localhost:8501/`
4. Click the **"Continue with Google"** button
5. You should be able to sign in with one of your test user emails
6. If you get a 403 error, make sure:
   - Your email is in the Test Users list
   - The redirect URI exactly matches (including `http://localhost:8501/`)
   - Secrets are correctly configured in `.streamlit/secrets.toml`

### Cloud Testing

1. Go to `https://lazycal.streamlit.app/` (replace with your actual URL)
2. Click the **"Continue with Google"** button
3. You should be redirected to Google login
4. Sign in with one of your test user emails
5. You should be redirected back to your app

---

## Troubleshooting

### 403 Forbidden Error

**Possible causes:**
1. Your email is NOT in the Test Users list
   - **Fix**: Go to OAuth consent screen → Test users → Add your email

2. Redirect URI doesn't match exactly
   - **Fix**: Check the OAuth Client ID settings → verify redirect URIs match exactly (including `http://` vs `https://` and trailing slash)

3. Secrets not configured
   - **Fix**: Ensure `.streamlit/secrets.toml` exists locally and secrets are pasted in Streamlit Cloud dashboard

4. App is still in development mode
   - **Fix**: Publish the app (go to OAuth consent screen, click "Publish" app)

### Address Already in Use (Port 8501)

If port 8501 is taken:
1. Streamlit will try port 8502
2. Update your redirect URI in GCP to match: `http://localhost:8502/`
3. Also update `local_redirect_uri` in `secrets.toml`

### Token Refresh Fails

If you see "Session expired/revoked":
1. Clear your browser cookies for `localhost:8501`
2. Clear Streamlit cache: Delete the `.streamlit/` folder in your browser's cache
3. Try logging in again

---

## Reference: OAuth Flow

For context, here's how the OAuth flow works in your app:

1. User clicks **"Continue with Google"**
2. User is redirected to Google's login page
3. After login, Google redirects back to your app with a `code` parameter
4. Your app's `main.py` exchanges this `code` for an access token
5. Your app stores the token in `st.session_state["credentials"]`
6. The token is used to make Google Calendar API calls on behalf of the user

---

## Summary Checklist

- [ ] Created new GCP project
- [ ] Enabled Google Calendar API
- [ ] Created OAuth 2.0 Client ID (Web application)
- [ ] Added both redirect URIs (`http://localhost:8501/` and `https://lazycal.streamlit.app/`)
- [ ] Configured OAuth consent screen (External user type)
- [ ] Added test user email(s)
- [ ] Created `.streamlit/secrets.toml` with Client ID and Secret
- [ ] Added `.streamlit/secrets.toml` to `.gitignore`
- [ ] Deployed app to Streamlit Cloud
- [ ] Added secrets to Streamlit Cloud dashboard
- [ ] Tested local login with test user email
- [ ] Tested cloud login with test user email

---

## Next Steps

Once OAuth is working:
1. Implement calendar management features
2. Add LLM parsing for natural language event creation
3. Implement undo/batch operations
4. Set up billing controls for LLM usage
5. Deploy to production with custom domain (optional)