# RPN Member Contribution Portal

> A self-hosted web portal for the **Retour au Pays Natal (R.P.N)** mutual aid group — giving members a private view of their contribution balance and giving the administrator a proper dashboard, replacing manual WhatsApp reminders with automated bilingual emails.

---

## Table of Contents

1. [What We Are Building](#1-what-we-are-building)
2. [Tech Stack](#2-tech-stack)
3. [Architecture Overview](#3-architecture-overview)
4. [Project Structure](#4-project-structure)
5. [File-by-File Explanation](#5-file-by-file-explanation)
6. [Getting Started — Clone and Run](#6-getting-started--clone-and-run)
7. [Google OAuth Setup — Start to Finish](#7-google-oauth-setup--start-to-finish)
8. [Google Sheets Setup](#8-google-sheets-setup)
9. [Environment Variables Reference](#9-environment-variables-reference)
10. [How Authentication Works](#10-how-authentication-works)
11. [How the Sheets Integration Works](#11-how-the-sheets-integration-works)
12. [Deployment](#12-deployment)
13. [Security Considerations](#13-security-considerations)
14. [What Is Done / What Is Left](#14-what-is-done--what-is-left)
15. [Troubleshooting](#15-troubleshooting)
16. [Design System](#16-design-system)

---

## 1. What We Are Building

### The problem

The R.P.N group is a 55-member community mutual aid organization. When a member's family experiences a bereavement, all members contribute funds that are pooled and sent to that family. Currently:

- All data lives in **one Google Sheet** managed by one volunteer
- The admin manually scans the sheet every month and sends **WhatsApp messages** to people who owe money
- Members have **no way to check their own balance** without messaging the admin
- There is **no audit trail** — no log of who was reminded, when, or what their balance was

### The solution

A simple web portal with two types of users:

| User | What they can do |
|------|-----------------|
| **Member** | Log in with Google → see their balance, status, contribution history |
| **Admin** | See all members, filter by deficit/probation, trigger email reminders |

The Google Sheet remains the **source of truth** — the admin keeps using it directly. The portal is a read layer on top, with write access only for updating the "last reminded" column.

### Non-goals (intentional simplicity)

- No in-app payments — Interac e-Transfer happens outside the app
- No separate database — Google Sheets is the DB
- No credit card processing
- No user registration — login is Google OAuth only, email must match the sheet

---

## 2. Tech Stack

| Layer | Technology | Why |
|-------|-----------|-----|
| **Backend** | Python 3 + Flask | Simple, readable, widely taught, easy to debug |
| **Templates** | Jinja2 (HTML) | Built into Flask, no extra tools needed |
| **Styling** | Bootstrap 5 + custom CSS | Responsive out of the box, minimal custom code |
| **Auth** | Google OAuth via Authlib | Members already have Google accounts, no passwords to manage |
| **Data** | Google Sheets API | Sheet already exists, admin already knows it |
| **Server** | Gunicorn | Production WSGI server for Flask |
| **Infrastructure** | Azure VM (Ubuntu) | Where the app runs |
| **Version control** | GitHub | Code storage and CI/CD hooks |

### Why Flask over Django?

Flask is a **micro-framework** — it gives you routing, templates, and sessions without forcing a project structure on you. For a project this size (a handful of routes, no complex ORM), Django would be overkill. Flask is also what most Python courses teach first.

### Why Google Sheets as the database?

- The data **already exists** there — no migration needed
- The admin is **already comfortable** editing it directly
- The Sheets API is free and well-documented
- For 55–200 users, it handles the load easily (300 requests/minute limit)
- When the group grows past ~500 members, migrating to a real database (PostgreSQL, Supabase) is straightforward

---

## 3. Architecture Overview

```
Browser (member or admin)
        |
        | HTTPS
        v
   Flask App (run.py)
        |
   +----|--------------------------------------------+
   |    |          app/__init__.py                   |
   |    |          creates the Flask app,            |
   |    |          registers blueprints              |
   |    |                                            |
   |  routes/auth.py      routes/member.py           |
   |  / /login /callback  /dashboard /history        |
   |                                                 |
   |  routes/admin.py                               |
   |  /admin /admin/members/<id>                    |
   |    |                                            |
   |  services/sheets.py  services/oauth.py          |
   |  reads Google Sheet  manages Google OAuth       |
   +----|--------------------------------------------+
        |
        | Google APIs
        v
   Google OAuth     Google Sheets API
   (identity)       (member data)
        |                |
   user's Gmail    your Google Sheet
```

### Request lifecycle (member login)

```
1. User visits /
2. Flask renders auth/login.html
3. User clicks "Sign in with Google"
4. Flask redirects to Google OAuth (/login/google)
5. Google authenticates the user, redirects back to /callback
6. Flask receives the user's email from Google
7. Flask checks if email exists in the Google Sheet
8. If found and active → stores email in session → redirects to /dashboard
9. /dashboard reads that member's row from the Sheet and renders it
```

---

## 4. Project Structure

```
rpn-web-portal/
│
├── app/                        # The Flask application
│   ├── __init__.py             # App factory — creates and configures Flask
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── auth.py             # Login, OAuth callback, logout, unauthorized
│   │   ├── member.py           # Dashboard, history, coverage (member views)
│   │   └── admin.py            # Admin dashboard, member detail, reminders
│   ├── services/
│   │   ├── __init__.py
│   │   ├── sheets.py           # All Google Sheets read/write logic
│   │   └── oauth.py            # Google OAuth client setup
│   ├── templates/
│   │   ├── base.html           # Shared layout: navbar, Bootstrap, flash messages
│   │   ├── auth/
│   │   │   ├── login.html      # Login page with Google button
│   │   │   └── unauthorized.html
│   │   ├── member/
│   │   │   ├── dashboard.html  # Balance hero, stats, recent activity
│   │   │   ├── history.html    # Contribution history (Phase 2)
│   │   │   └── coverage.html   # Family coverage (Phase 2)
│   │   └── admin/
│   │       ├── dashboard.html  # Full member table with stats
│   │       ├── member_detail.html
│   │       ├── reminders.html  # Reminder trigger (Phase 3)
│   │       └── settings.html
│   └── static/
│       └── css/
│           └── style.css       # Custom styles on top of Bootstrap
│
├── docs/
│   ├── adr/                    # Architecture Decision Records
│   └── wireframes/             # Figma exports
│
├── infrastructure/
│   ├── docker/                 # Dockerfile (Phase 4)
│   ├── ansible/                # VM configuration (Phase 5)
│   └── terraform/              # Infrastructure as code (Phase 5)
│
├── run.py                      # Entry point — starts the Flask server
├── requirements.txt            # Python dependencies
├── .env.example                # Template for environment variables
├── .env                        # Your real secrets (never committed to git)
├── service_account.json        # Google service account key (never committed)
├── .gitignore
└── README.md
```

---

## 5. File-by-File Explanation

### `run.py`
The entry point. Imports the Flask app from `app/` and runs it.
```python
from app import create_app
app = create_app()
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
```
In production, Gunicorn calls `app:app` directly — it imports `app` from `app/__init__.py`.

---

### `app/__init__.py` — App factory
Creates the Flask app, loads config, and registers the three blueprints (auth, member, admin).

**Why a factory function?** It makes testing easier and allows multiple app instances with different configs. It's the recommended Flask pattern.

---

### `app/routes/auth.py` — Authentication routes

| Route | Method | What it does |
|-------|--------|-------------|
| `/` | GET | Shows login page, redirects if already logged in |
| `/login/google` | GET | Starts Google OAuth flow |
| `/callback` | GET | Receives OAuth result, checks sheet, sets session |
| `/logout` | GET | Clears session |
| `/unauthorized` | GET | Shows access denied page |

The session stores:
```python
session["user"]     = {"email": "...", "name": "..."}
session["is_admin"] = True / False
```

---

### `app/routes/member.py` — Member views

All routes are protected by the `@login_required` decorator — if there's no session, you're redirected to login.

| Route | What it renders |
|-------|----------------|
| `/dashboard` | Balance card, 3 stats, recent activity |
| `/history` | Contribution history (Phase 2) |
| `/coverage` | Family coverage details (Phase 2) |

---

### `app/routes/admin.py` — Admin views

All routes are protected by `@admin_required` — checks both `session["user"]` and `session["is_admin"]`.

| Route | What it renders |
|-------|----------------|
| `/admin/` | Stats bar + full member table sorted by balance |
| `/admin/members/<id>` | Single member detail |
| `/admin/reminders` | Reminder controls (Phase 3) |
| `/admin/settings` | Portal settings (Phase 3) |

---

### `app/services/sheets.py` — Google Sheets integration

The most important service file. Contains:

| Function | What it does |
|----------|-------------|
| `_get_service()` | Authenticates with Google using the service account and returns the Sheets API client |
| `get_all_members()` | Reads the entire sheet, parses every row into a dict, returns a list |
| `get_member_by_email(email)` | Finds one member by email — used on every dashboard load |
| `get_balance_status(balance)` | Returns `"positive"`, `"warning"`, `"urgent"`, or `"zero"` |
| `format_currency(amount)` | Returns `"$12.50"` |
| `update_member_opt_out(row, val)` | Writes to column K |
| `update_last_reminded(row, date)` | Writes to column J |

**Column mapping** (0-based indices, matches your sheet):
```
A=0  Name
C=2  Coverage start
D=3  Renewal status
E=4  Deaths contributed
F=5  Balance ← most important
G=6  Email
H=7  Status (active/probation/deactivated)
J=9  Last reminded
K=10 Do not email (opt-out)
```
> If your sheet columns differ, update the `COL_*` constants at the top of `sheets.py`.

---

### `app/services/oauth.py` — OAuth client

Initializes Authlib's OAuth client with Google's OIDC configuration. Called once when the app starts.

---

### `app/templates/base.html` — Shared layout

Every page extends this. It provides:
- Bootstrap 5 CSS/JS via CDN
- Custom `style.css`
- Navbar with member links + admin links (admin links only visible if `session.is_admin`)
- Flash message display area
- Responsive mobile-first structure

---

### `app/static/css/style.css` — Mediterranean palette

Defines the color system as CSS variables and applies them to Bootstrap components:
```css
--terra-cotta: #C0522A  /* primary, CTAs, negative balance */
--sand:        #EDE3CF  /* page background */
--olive:       #5C6B2E  /* positive balance, success */
--ochre:       #C98A1A  /* warning, minor debt */
--clay:        #B5622A  /* secondary text, labels */
--sea:         #2A5F6B  /* links, nav active, info */
--ink:         #2C2416  /* all body text */
```

---

## 6. Getting Started — Clone and Run

### Prerequisites

- Python 3.10 or higher
- Git
- A Google account (for OAuth and Sheets access)
- Access to the R.P.N Google Sheet (or a copy for testing)

### Step 1 — Clone the repo

```bash
git clone https://github.com/ChelsieSalome/rpn-web-portal.git
cd rpn-web-portal
```

### Step 2 — Create a virtual environment

```bash
python3 -m venv venv
source venv/bin/activate        # Linux / Mac
# venv\Scripts\activate         # Windows
```

### Step 3 — Install dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Set up your environment file

```bash
cp .env.example .env
```

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Open `.env` and fill in all values (see [Environment Variables Reference](#9-environment-variables-reference)).

### Step 5 — Add your service account JSON

Place your Google service account JSON file at the project root and name it:
```
service_account.json
```
See [Google Sheets Setup](#8-google-sheets-setup) for how to create this.

### Step 6 — Run the development server

```bash
python run.py
```

Visit `http://localhost:5000` in your browser.

---

## 7. Google OAuth Setup — Start to Finish

This is required for the login button to work. Takes about 10 minutes.

### Step 1 — Create a Google Cloud project

1. Go to [console.cloud.google.com](https://console.cloud.google.com)
2. Click the project dropdown at the top → **New Project**
3. Name it `rpn-portal` → **Create**
4. Make sure the new project is selected in the dropdown

### Step 2 — Enable required APIs

In your project, go to **APIs & Services → Library** and enable:
- **Google Sheets API**
- **Google Drive API** (needed by the Sheets client)

### Step 3 — Create OAuth credentials

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → OAuth client ID**
3. If prompted, configure the OAuth consent screen first:
   - User type: **External**
   - App name: `RPN Portal`
   - User support email: your email
   - Developer contact: your email
   - Save and continue through all steps
   - Under **Test users**, add the emails you want to test with
4. Back to Create OAuth client ID:
   - Application type: **Web application**
   - Name: `RPN Web Portal`
   - **Authorized redirect URIs** — add both:
     ```
     http://localhost:5000/callback
     https://your-domain.com/callback
     ```
5. Click **Create**
6. Copy the **Client ID** and **Client Secret** into your `.env` file

### Step 4 — Create a service account (for Sheets access)

1. Go to **APIs & Services → Credentials**
2. Click **+ Create Credentials → Service Account**
3. Name: `rpn-sheets-reader`
4. Role: **Editor** (or just **Viewer** if you don't need write access yet)
5. Click **Done**
6. Click on the service account you just created
7. Go to the **Keys** tab → **Add Key → Create new key → JSON**
8. Download the JSON file
9. Rename it to `service_account.json` and place it at the project root
10. Copy the `client_email` value from that file — it looks like:
    ```
    rpn-sheets-reader@rpn-portal.iam.gserviceaccount.com
    ```

### Step 5 — Share the Google Sheet with the service account

1. Open your Google Sheet
2. Click **Share**
3. Paste the service account email from Step 4
4. Give it **Editor** access (needed to write "last reminded" dates)
5. Click **Send**

### Step 6 — Copy the Sheet ID

The Sheet ID is in the URL:
```
https://docs.google.com/spreadsheets/d/THIS_IS_THE_ID/edit
```
Paste it into your `.env` as `GOOGLE_SHEET_ID`.

---

## 8. Google Sheets Setup

### Expected column layout

Your sheet must have data starting from row 2 (row 1 is the header). The app reads these columns:

| Column | Letter | Contains |
|--------|--------|---------|
| 0 | A | Member name |
| 2 | C | Coverage start date |
| 3 | D | Renewal status |
| 4 | E | Number of deaths contributed |
| 5 | F | **Balance (the key column)** |
| 6 | G | **Email address** |
| 7 | H | Status (`active` / `probation` / `deactivated`) |
| 9 | J | Last reminded date (written by the app) |
| 10 | K | Do not email flag (`yes` to suppress reminders) |

### Adding the email and opt-out columns

If your sheet doesn't have columns J and K yet:

1. Insert a column after H (Status) → this becomes column I
2. Insert another column → column J = **Last Reminded** (header in J1)
3. Insert another → column K = **Do Not Email** (header in K1)

> If your column layout differs from the above, edit the `COL_*` constants in `app/services/sheets.py` before running the app.

### Adding test data

For local testing without real member data, create a sheet with these columns and add a few rows with your own email address as the email — you'll be able to log in and see the dashboard immediately.

---

## 9. Environment Variables Reference

All variables live in `.env` at the project root. Never commit this file.

```bash
# Flask internals
FLASK_SECRET_KEY=          # Long random string — used to sign sessions
FLASK_ENV=development      # Use "production" when deployed
FLASK_DEBUG=1              # Set to 0 in production

# Google OAuth
GOOGLE_CLIENT_ID=          # From Google Cloud Console
GOOGLE_CLIENT_SECRET=      # From Google Cloud Console

# Google Sheets
GOOGLE_SHEET_ID=           # From the sheet URL
GOOGLE_SERVICE_ACCOUNT_FILE=service_account.json  # Path to the JSON key file

# Access control
ADMIN_EMAIL=               # The one email address that gets admin access

# Shown to members in the UI
PAYMENT_EMAIL=             # Interac e-Transfer destination
PAYMENT_DEADLINE=          # e.g. "the 25th of this month"
```

---

## 10. How Authentication Works

```
User clicks "Sign in with Google"
          |
          v
Flask redirects to Google
(passing client_id and redirect_uri)
          |
          v
User approves on Google's page
          |
          v
Google sends back an authorization code to /callback
          |
          v
Flask exchanges the code for a token (server-side)
          |
          v
Flask extracts user email from the token
          |
     .----+----.
     |         |
  Admin?     Member in sheet?
     |              |
   yes            yes/no
     |              |
  set           active? -----no-----> /unauthorized
  is_admin=True    |
     |            yes
     |              |
     v              v
 /admin/       /dashboard
```

### Sessions

Flask uses **server-side sessions signed with your secret key**. The session cookie contains:
```python
session["user"]     = {"email": "...", "name": "..."}
session["is_admin"] = True | False
```

The cookie is **signed but not encrypted** — don't store sensitive data in it. The email and name are safe; never store the balance or member ID in the session.

### Why Google OAuth only?

- Members already have Google accounts
- No password storage = no password security risk
- If Google's OAuth is compromised, that's Google's problem, not ours
- Simple to implement and maintain

---

## 11. How the Sheets Integration Works

Every time a page loads that needs member data, the app calls the Sheets API:

```
Page request → route handler → sheets.get_member_by_email(email)
                                        |
                               sheets.get_all_members()
                                        |
                         Google Sheets API (reads entire sheet)
                                        |
                         Returns list of all member dicts
                                        |
                         Filter by email → return single member
```

### Why read the whole sheet every time?

For 55–200 members, this is fast (under 1 second) and simple. The alternative — caching or indexing — adds complexity without meaningful benefit at this scale.

> **When to add caching:** If you notice the dashboard taking more than 2 seconds to load, or if your Sheets API quota gets hit (300 requests/minute), add a 5-minute in-memory cache using Flask-Caching.

### Balance status logic

```python
def get_balance_status(balance):
    if balance > 0:   return "positive"   # olive green
    if balance == 0:  return "zero"       # sand
    if balance > -10: return "warning"    # ochre
    return "urgent"                       # terra cotta
```

---

## 12. Deployment

### Current setup (Azure VM)

The app runs on an Azure Ubuntu VM. To run in production:

```bash
# Activate virtual environment
source venv/bin/activate

# Run with Gunicorn (production WSGI server)
gunicorn --workers 2 --bind 0.0.0.0:5000 "app:create_app()"
```

### Set FLASK_ENV to production

```bash
# In your .env
FLASK_ENV=production
FLASK_DEBUG=0
```

### Keep the app running with systemd

```bash
sudo nano /etc/systemd/system/rpn.service
```

Paste:
```ini
[Unit]
Description=RPN Portal
After=network.target

[Service]
User=azureuser
WorkingDirectory=/home/azureuser/RPN/rpn-web-portal
ExecStart=/home/azureuser/RPN/rpn-web-portal/venv/bin/gunicorn \
    --workers 2 \
    --bind 0.0.0.0:5000 \
    "app:create_app()"
Restart=always
EnvironmentFile=/home/azureuser/RPN/rpn-web-portal/.env

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable rpn
sudo systemctl start rpn
sudo systemctl status rpn
```

### Add a domain and HTTPS (optional but recommended)

If you have a domain, point it to your VM's public IP, then:

```bash
# Install Nginx as a reverse proxy
sudo apt install nginx -y

# Install Certbot for free SSL
sudo apt install certbot python3-certbot-nginx -y

# Get certificate (replace with your domain)
sudo certbot --nginx -d rpngroup.ca
```

Nginx config (`/etc/nginx/sites-available/rpn`):
```nginx
server {
    listen 80;
    server_name rpngroup.ca;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name rpngroup.ca;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/rpn /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

---

## 13. Security Considerations

| Risk | Mitigation |
|------|-----------|
| **Member sees another member's data** | Every data fetch is filtered by the authenticated user's email server-side. The full sheet is never sent to the browser. |
| **Someone accesses /admin** | `@admin_required` decorator checks `session["is_admin"]` on every request. Admin status is set server-side at login — never trusted from the client. |
| **Session hijacking** | Sessions are signed with `FLASK_SECRET_KEY`. Use a long random key (32+ chars). Rotate it if compromised (all sessions invalidate). |
| **Secret key in code** | All secrets are in `.env` which is git-ignored. The `.env.example` has no real values. |
| **Service account key exposed** | `service_account.json` is git-ignored. Never commit it. Store it securely on the server. |
| **CSRF attacks** | Flask sessions use `SameSite=Lax` cookies by default. For Phase 3 (forms that modify data), add Flask-WTF for CSRF tokens. |
| **HTTPS** | Enforced by Nginx + Let's Encrypt in production. Never run without HTTPS when members are logging in. |
| **PIPEDA (Canadian privacy)** | No PII stored in the app's database — data stays in the Sheet. A privacy notice is on the login page. |
| **Inactive accounts** | Deactivated members are redirected to /unauthorized at the OAuth callback — they never reach any page. |

### What NOT to do

- Never store `FLASK_SECRET_KEY`, `GOOGLE_CLIENT_SECRET`, or the service account key in Git
- Never print session data or member data to logs
- Never pass the full member list to a template on a member-facing page
- Never trust data coming from the browser — always validate server-side

---

## 14. What Is Done / What Is Left

### ✅ Phase 0 — Design (complete)
- [x] User flows and wireframes (Figma)
- [x] Hi-fi mockups with Mediterranean palette
- [x] Design system documented
- [x] Planning document written

### ✅ Phase 1 — MVP (complete)
- [x] Flask project structure
- [x] Google OAuth login
- [x] Google Sheets integration
- [x] Member dashboard (balance, stats)
- [x] Admin dashboard (full member table)
- [x] Member detail page
- [x] Unauthorized page
- [x] Bootstrap 5 responsive layout
- [x] Mediterranean color system

### 🔲 Phase 2 — Full member features
- [ ] Contribution history page (reads transaction log from sheet)
- [ ] Coverage page (family members listed)
- [ ] Language toggle (EN/FR) using Flask-Babel or session variable

### 🔲 Phase 3 — Full admin features
- [ ] Inline opt-out toggle (writes to sheet column K)
- [ ] Status change dropdown (writes to sheet column H)
- [ ] Reminder trigger — calls existing Google Apps Script via HTTP
- [ ] Reminder log tab in the sheet, displayed in the portal
- [ ] Admin settings page (payment email, deadline, thresholds)

### 🔲 Phase 4 — DevOps & observability
- [ ] Dockerfile + docker-compose
- [ ] GitHub Actions CI (lint + test on push)
- [ ] Prometheus metrics endpoint
- [ ] Grafana dashboard
- [ ] Structured logging with Python logging module

### 🔲 Phase 5 — Kubernetes & portfolio polish
- [ ] Helm chart
- [ ] Ansible playbook for VM provisioning
- [ ] Terraform for infrastructure
- [ ] Architecture diagram
- [ ] LinkedIn write-up

---

## 15. Troubleshooting

### App won't start

```bash
# Check if venv is activated
which python   # should point to venv/bin/python

# Check for missing packages
pip install -r requirements.txt

# Check for syntax errors
python -c "from app import create_app; create_app()"
```

### Login redirects to /unauthorized unexpectedly

1. Check that your email is in column G of the sheet
2. Check that the sheet is shared with the service account email
3. Check that `GOOGLE_SHEET_ID` in `.env` matches the actual sheet URL
4. Check that the status column (H) doesn't say "deactivated" for your row
5. Check the terminal output — `sheets.py` prints errors to stdout

### Google OAuth error: "redirect_uri_mismatch"

The redirect URI in Google Cloud Console must exactly match what Flask sends. Check:
- Google Cloud Console → Credentials → your OAuth client → Authorized redirect URIs
- Must include `http://localhost:5000/callback` for local dev
- Must include `https://yourdomain.com/callback` for production
- No trailing slashes

### Google OAuth error: "Access blocked — app not verified"

During development, your OAuth app is in "testing" mode. Add your test email addresses under **APIs & Services → OAuth consent screen → Test users**.

### Sheets API error: "PERMISSION_DENIED"

The service account doesn't have access to the sheet. Re-share the sheet:
1. Open the Google Sheet
2. Share → paste the service account email (from `service_account.json`, key: `client_email`)
3. Give Editor access

### Balance showing as 0 for everyone

The `COL_BALANCE` constant in `sheets.py` is set to column index 5 (column F). If your balance is in a different column, count from A=0 and update the constant:
```python
COL_BALANCE = 5  # change this to match your sheet
```

### Port 5000 already in use

```bash
# Find what's using port 5000
sudo lsof -i :5000

# Kill it
sudo kill -9 <PID>

# Or run Flask on a different port
python run.py --port 5001
```

### Changes to templates not showing

Flask caches templates in production mode. Make sure `FLASK_DEBUG=1` in `.env` during development. If still stale, do a hard refresh in the browser (`Ctrl+Shift+R`).

---

## 16. Design System

### Color palette (Mediterranean)

| Name | Hex | Used for |
|------|-----|---------|
| Terra Cotta | `#C0522A` | Primary buttons, H1, negative balance |
| Sand | `#EDE3CF` | Page background, disabled states |
| Olive | `#5C6B2E` | Positive balance, success |
| Ochre | `#C98A1A` | Warnings, minor debt |
| Clay | `#B5622A` | Secondary text, labels |
| Sea | `#2A5F6B` | Links, nav active, info |
| Ink | `#2C2416` | All body text |

### Balance status → color mapping

| Balance | Status | Color shown |
|---------|--------|------------|
| `> 0` | positive | Olive green card |
| `= 0` | zero | Sand card |
| `< 0` and `> -10` | warning | Ochre card |
| `≤ -10` | urgent | Terra Cotta card |

### Typography rule

- **Headings and balance numbers**: Georgia serif
- **Everything else**: Arial sans-serif

---

## Contributing / Maintaining

This project is maintained by one volunteer developer. The goal is **simplicity first** — before adding a feature, ask: does this save the admin meaningful time, or does it add complexity for its own sake?

### Branch strategy

```
main        → production (what's running on the server)
develop     → staging (test here before merging to main)
feature/*   → one branch per feature, merge to develop
```

### Making a change

```bash
git checkout -b feature/your-feature-name
# make changes
git add .
git commit -m "feat: describe what you did"
git push origin feature/your-feature-name
# open a pull request on GitHub
```

---

*R.P.N Portal — built with care for the community. April 2026.*
