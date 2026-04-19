# ADR 001 — Use Google Sheets as the database

## Date
April 2026

## Status
Accepted

## Context
The RPN Group already manages all member data in a Google Sheet.
The admin is comfortable with it and it is the source of truth.
We have no budget for a managed database service.

## Decision
Use the Google Sheets API as the data layer for this portal.
The Sheet remains the single source of truth.
The portal reads from and writes to it via a service account.

## Consequences
- No database migration needed
- Admin can continue editing the Sheet directly
- Google Sheets API has rate limits (300 req/min) — acceptable for <200 users
- If the group grows past 500 members, we will revisit and migrate to Supabase
