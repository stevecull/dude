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

2. Create a Google Cloud service account with the Sheets API enabled, and
   download its JSON key.
3. Share the target Google Sheet with the service account's
   `client_email` (found in the JSON key) as an **Editor**.
4. Copy `.env.example` to `.env` and fill in the values, then export them
   into your shell (e.g. `set -a; source .env; set +a`) or pass the
   equivalent CLI flags.

## Usage

```bash
python connector.py \
  --source "https://.../vibe-export.csv" \
  --spreadsheet-id "1AbCDefGhiJklMnoPqrStuVwxYz..." \
  --sheet-name "Vibe Prospects" \
  --credentials "./service-account.json" \
  --key-column prospect_id
```

All flags can instead be set via environment variables (see
`.env.example`): `VIBE_EXPORT_SOURCE`, `GOOGLE_SHEET_ID`,
`GOOGLE_SHEET_TAB`, `GOOGLE_APPLICATION_CREDENTIALS`, `VIBE_KEY_COLUMN`.

Use `--key-column business_id` when syncing a businesses export instead of
a prospects export.

## Scheduling

To keep the sheet up to date automatically, run `connector.py` on a
schedule (cron, GitHub Actions, etc.) pointed at a fresh Vibe export link
each time.
