# Vibe → Google Sheets Connector

Syncs prospect/business records exported from Vibe Prospecting into a
Google Sheet, so a sales or ops team can work the list without needing
access to Vibe itself. Safe to re-run: rows are deduped by a key column
(default `prospect_id`) so repeated syncs only append new rows.

## How it works

1. Run a search in Vibe Prospecting and export the results to CSV (the
   `export-to-csv` tool returns a downloadable CSV link).
2. Run `connector.py` with that link (or a downloaded CSV file) and your
   target Google Sheet.
3. The script reads the existing sheet, skips rows whose key column value
   is already present, and appends the rest.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Authenticate with Google — two options:

   **Option A: gcloud Application Default Credentials (simplest for personal use)**

   ```bash
   gcloud auth application-default login \
     --scopes=https://www.googleapis.com/auth/spreadsheets
   ```

   This uses your own Google account, so you don't need to share the sheet
   with anything extra — just make sure the account you log in with already
   has edit access to the target sheet. Leave `--credentials` /
   `GOOGLE_APPLICATION_CREDENTIALS` unset when running the connector.

   **Option B: service account (better for unattended/scheduled runs)**

   Create a Google Cloud service account with the Sheets API enabled,
   download its JSON key, and share the target Google Sheet with the
   service account's `client_email` (found in the JSON key) as an
   **Editor**. Pass the key path via `--credentials` /
   `GOOGLE_APPLICATION_CREDENTIALS`.

3. Copy `.env.example` to `.env` and fill in the values, then export them
   into your shell (e.g. `set -a; source .env; set +a`) or pass the
   equivalent CLI flags.

## Usage

With gcloud ADC (Option A):

```bash
python connector.py \
  --source "https://.../vibe-export.csv" \
  --spreadsheet-id "1AbCDefGhiJklMnoPqrStuVwxYz..." \
  --sheet-name "Vibe Prospects" \
  --key-column prospect_id
```

With a service account key (Option B), add `--credentials "./service-account.json"`.

All flags can instead be set via environment variables (see
`.env.example`): `VIBE_EXPORT_SOURCE`, `GOOGLE_SHEET_ID`,
`GOOGLE_SHEET_TAB`, `GOOGLE_APPLICATION_CREDENTIALS`, `VIBE_KEY_COLUMN`.

Use `--key-column business_id` when syncing a businesses export instead of
a prospects export.

## Scheduling

To keep the sheet up to date automatically, run `connector.py` on a
schedule (cron, GitHub Actions, etc.) pointed at a fresh Vibe export link
each time.
