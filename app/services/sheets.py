"""
Google Sheets service — reads member data from the spreadsheet.
All data access goes through this file.
"""
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SHEET_ID   = os.getenv("GOOGLE_SHEET_ID")
SHEET_NAME = "Sheet1"
SCOPES     = ["https://www.googleapis.com/auth/spreadsheets"]

# Column indices (0-based) — adjust if your sheet differs
COL_NAME               = 0   # A
COL_COVERAGE_START     = 2   # C
COL_RENEWAL_STATUS     = 3   # D
COL_CONTRIBUTED_DEATHS = 4   # E
COL_BALANCE            = 5   # F
COL_EMAIL              = 6   # G
COL_STATUS             = 7   # H
COL_LAST_REMINDED      = 9   # J
COL_OPT_OUT            = 10  # K


def _get_service():
    """Build and return the Sheets API client."""
    creds = service_account.Credentials.from_service_account_file(
        os.getenv("GOOGLE_SERVICE_ACCOUNT_FILE", "service_account.json"),
        scopes=SCOPES,
    )
    return build("sheets", "v4", credentials=creds)


def _safe(val):
    """Return a clean string, never None."""
    return str(val).strip() if val is not None else ""


def _parse_balance(val):
    """Parse a balance value that might be a string like '$-10.50'."""
    if val is None or val == "":
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    cleaned = "".join(c for c in str(val) if c.isdigit() or c in ".-")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def _parse_family_size(name):
    """Extract family size from name like 'John K. & Family (5)'."""
    import re
    match = re.search(r"\((\d+)\)", name)
    return int(match.group(1)) if match else 1


def _parse_status(raw):
    s = raw.lower()
    if "deactivated" in s:
        return "deactivated"
    if "probation" in s:
        return "probation"
    return "active"


def get_all_members():
    """Return list of all members as dicts. Never raises — returns [] on error."""
    try:
        service  = _get_service()
        result   = service.spreadsheets().values().get(
            spreadsheetId=SHEET_ID,
            range=f"{SHEET_NAME}!A:K"
        ).execute()
        rows = result.get("values", [])
    except Exception as e:
        print(f"[sheets] Error fetching members: {e}")
        return []

    members = []
    for i, row in enumerate(rows[1:], start=1):  # skip header row
        # Pad row to avoid index errors
        while len(row) <= COL_OPT_OUT:
            row.append("")

        name = _safe(row[COL_NAME])
        if not name or name.lower() == "deactivated":
            continue

        email   = _safe(row[COL_EMAIL])
        balance = _parse_balance(row[COL_BALANCE])
        status  = _parse_status(_safe(row[COL_STATUS]))
        opt_out = _safe(row[COL_OPT_OUT]).lower() in ("yes", "y", "1", "true")

        members.append({
            "id":                 str(i),
            "row_index":          i,
            "name":               name,
            "email":              email,
            "balance":            balance,
            "status":             status,
            "coverage_start":     _safe(row[COL_COVERAGE_START]),
            "renewal_status":     _safe(row[COL_RENEWAL_STATUS]),
            "contributed_deaths": int(_parse_balance(row[COL_CONTRIBUTED_DEATHS])),
            "family_size":        _parse_family_size(name),
            "last_reminded":      _safe(row[COL_LAST_REMINDED]) or None,
            "opt_out":            opt_out,
        })

    return members


def get_member_by_email(email):
    """Find a single member by email. Returns None if not found."""
    email = email.lower().strip()
    for m in get_all_members():
        if m["email"].lower() == email:
            return m
    return None


def get_balance_status(balance):
    """Return urgency level for a balance number."""
    if balance > 0:
        return "positive"
    if balance == 0:
        return "zero"
    if balance > -10:
        return "warning"
    return "urgent"


def format_currency(amount):
    """Format a number as $X.XX"""
    return f"${abs(amount):.2f}"
