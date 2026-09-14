# Vibe → Google Sheets Connector

Automatically finds new SaaS marketing/business-development prospect leads
via the Explorium API (the API behind Vibe Prospecting) and appends them
to a Google Sheet. Safe to re-run: rows are deduped by `prospect_id`, so
repeated runs only add rows that aren't already in the sheet.

Search criteria (edit via flags on `fetch_vibe_leads.py` if you want
something different): VP/Director of Marketing or Business Development,
at SaaS companies (`linkedin_category: software development`) with
50-500 employees, in the US/CA, that had a new funding round in the
last 90 days.

## How it works

1. `fetch_vibe_leads.py` calls the Explorium API in two steps: first
   `fetch_businesses` (SaaS companies in the US/CA with a recent funding
   event), then `fetch_prospects` scoped to just those companies
   (VP/Director marketing or business-development people). Writes the
   result to a CSV.
2. `connector.py` reads that CSV, compares it against what's already in
   the target Google Sheet (matching on `prospect_id`), and appends only
   the new rows.
3. `run_daily.sh` runs both steps back to back — this is what you put on
   a schedule.

## Setup

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Get an Explorium API key (Admin Portal → Access & Authentication →
   Getting Your API Key at admin.explorium.ai).

3. Authenticate with Google — two options:

   **Option A: gcloud Application Default Credentials (simplest for personal use)**

   ```bash
   gcloud auth application-default login \
     --scopes=https://www.googleapis.com/auth/spreadsheets
   ```

   Uses your own Google account — make sure it already has edit access to
   the target sheet. Leave `GOOGLE_APPLICATION_CREDENTIALS` unset.

   **Option B: service account (needed for unattended/scheduled runs on
   a machine you won't be logged into)**

   Create a Google Cloud service account with the Sheets API enabled,
   download its JSON key, and share the target Google Sheet with the
   service account's `client_email` as an **Editor**. Point
   `GOOGLE_APPLICATION_CREDENTIALS` at the downloaded key file.

4. Copy `.env.example` to `.env` and fill in `EXPLORIUM_API_KEY`,
   `GOOGLE_SHEET_ID`, `GOOGLE_SHEET_TAB`, and (if using Option B)
   `GOOGLE_APPLICATION_CREDENTIALS`.

## Usage

Run once by hand:

```bash
set -a; source .env; set +a
./run_daily.sh
```

Or run the two steps separately:

```bash
python fetch_vibe_leads.py --out todays_leads.csv
python connector.py --source todays_leads.csv --key-column prospect_id
```

`fetch_vibe_leads.py` flags for tweaking the search (all optional, shown
with their defaults):

```bash
python fetch_vibe_leads.py \
  --countries US CA \
  --linkedin-categories "software development" \
  --funding-window-days 90 \
  --company-sizes 51-200 201-500 \
  --job-levels director "vice president" \
  --job-titles "Business Development" "Marketing" \
  --max-businesses 10 \
  --max-prospects 100 \
  --out vibe_leads.csv
```

`--company-sizes` must use Explorium's fixed buckets: `1-10`, `11-50`,
`51-200`, `201-500`, `501-1000`, `1001-5000`, `5001-10000`, `10001+`.
There's no free-form range, so `51-200 201-500` is the closest fit to
"50-300 employees".

## Scheduling

Run daily via cron, e.g. at 7:05am US Central time:

```cron
CRON_TZ=America/Chicago
5 7 * * * cd /path/to/vibe-sheets-connector && ./run_daily.sh >> run.log 2>&1
```

(`CRON_TZ` keeps the time correct across daylight saving changes; if your
cron doesn't support it, use your system's local time directly instead —
check with `date`.)

Each run's fetched CSV is kept under `runs/` for an audit trail.
