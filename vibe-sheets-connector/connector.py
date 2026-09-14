#!/usr/bin/env python3
"""Sync a Vibe Prospecting CSV export into a Google Sheet.

Vibe Prospecting (Explorium) delivers results as a CSV export with a
download link (see the `export-to-csv` tool). This script takes that link
(or a local CSV file) and appends any rows not already present in the
target Google Sheet, using a key column to detect duplicates so the sync
can be re-run safely.
"""
import argparse
import csv
import io
import os
import sys

import requests
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def load_csv_rows(source):
    if source.startswith("http://") or source.startswith("https://"):
        response = requests.get(source, timeout=60)
        response.raise_for_status()
        text = response.text
    else:
        with open(source, newline="", encoding="utf-8") as f:
            text = f.read()
    return list(csv.reader(io.StringIO(text)))


def get_sheets_service(credentials_path):
    creds = service_account.Credentials.from_service_account_file(credentials_path, scopes=SCOPES)
    return build("sheets", "v4", credentials=creds)


def ensure_sheet_exists(service, spreadsheet_id, sheet_name):
    meta = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
    titles = [s["properties"]["title"] for s in meta.get("sheets", [])]
    if sheet_name not in titles:
        service.spreadsheets().batchUpdate(
            spreadsheetId=spreadsheet_id,
            body={"requests": [{"addSheet": {"properties": {"title": sheet_name}}}]},
        ).execute()


def read_existing(service, spreadsheet_id, sheet_name):
    result = (
        service.spreadsheets()
        .values()
        .get(spreadsheetId=spreadsheet_id, range=f"{sheet_name}!A:ZZ")
        .execute()
    )
    return result.get("values", [])


def sync(args):
    rows = load_csv_rows(args.source)
    if not rows:
        print("No rows found in source CSV.", file=sys.stderr)
        return
    header, data_rows = rows[0], rows[1:]

    service = get_sheets_service(args.credentials)
    ensure_sheet_exists(service, args.spreadsheet_id, args.sheet_name)

    existing = read_existing(service, args.spreadsheet_id, args.sheet_name)
    existing_header = existing[0] if existing else []

    key_index = header.index(args.key_column) if args.key_column in header else 0
    existing_key_index = (
        existing_header.index(args.key_column) if args.key_column in existing_header else key_index
    )
    existing_keys = {
        row[existing_key_index] for row in existing[1:] if len(row) > existing_key_index
    }

    values_to_append = [] if existing_header else [header]
    new_count = 0
    for row in data_rows:
        key = row[key_index] if len(row) > key_index else None
        if key and key in existing_keys:
            continue
        values_to_append.append(row)
        if key:
            existing_keys.add(key)
        new_count += 1

    if not values_to_append:
        print("Nothing new to sync.")
        return

    service.spreadsheets().values().append(
        spreadsheetId=args.spreadsheet_id,
        range=f"{args.sheet_name}!A1",
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body={"values": values_to_append},
    ).execute()

    print(f"Synced {new_count} new row(s) from Vibe export into '{args.sheet_name}'.")


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source",
        default=os.environ.get("VIBE_EXPORT_SOURCE"),
        help="Vibe export CSV URL or local file path (env: VIBE_EXPORT_SOURCE).",
    )
    parser.add_argument(
        "--spreadsheet-id",
        default=os.environ.get("GOOGLE_SHEET_ID"),
        help="Target Google Sheet ID (env: GOOGLE_SHEET_ID).",
    )
    parser.add_argument(
        "--sheet-name",
        default=os.environ.get("GOOGLE_SHEET_TAB", "Vibe Prospects"),
        help="Tab name within the spreadsheet (env: GOOGLE_SHEET_TAB).",
    )
    parser.add_argument(
        "--credentials",
        default=os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
        help="Path to a Google service-account JSON key (env: GOOGLE_APPLICATION_CREDENTIALS).",
    )
    parser.add_argument(
        "--key-column",
        default=os.environ.get("VIBE_KEY_COLUMN", "prospect_id"),
        help="Column used to detect and skip rows already synced (env: VIBE_KEY_COLUMN).",
    )
    args = parser.parse_args()

    missing = [
        name
        for name, value in (
            ("--source/VIBE_EXPORT_SOURCE", args.source),
            ("--spreadsheet-id/GOOGLE_SHEET_ID", args.spreadsheet_id),
            ("--credentials/GOOGLE_APPLICATION_CREDENTIALS", args.credentials),
        )
        if not value
    ]
    if missing:
        parser.error(f"missing required value(s): {', '.join(missing)}")
    return args


def main():
    sync(parse_args())


if __name__ == "__main__":
    main()
