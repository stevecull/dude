#!/usr/bin/env bash
# Daily job: fetch new SaaS marketing/BD leads from Explorium, then sync
# any rows not already in the target Google Sheet (deduped on prospect_id).
set -euo pipefail
cd "$(dirname "$0")"

if [ -f .env ]; then
  set -a
  source .env
  set +a
fi

mkdir -p runs
LEADS_CSV="runs/leads_$(date +%Y-%m-%d).csv"

python3 fetch_vibe_leads.py --out "$LEADS_CSV" --max-businesses 10 --max-prospects 100
python3 connector.py --source "$LEADS_CSV" --key-column prospect_id
