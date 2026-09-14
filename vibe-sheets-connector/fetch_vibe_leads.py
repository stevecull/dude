#!/usr/bin/env python3
"""Fetch new SaaS marketing/business-development prospect leads from the
Explorium API (the API behind Vibe Prospecting).

Two-step search:
1. fetch_businesses: SaaS companies (linkedin_category) in the given
   countries with a funding-round event in the last N days.
2. fetch_prospects: VP/Director marketing or business-development people
   at those specific businesses (business_id filter).

Writes the resulting prospect rows to a CSV. Feed that CSV into
connector.py to append only the new-to-the-sheet rows (deduped on
prospect_id) into a Google Sheet.
"""
import argparse
import csv
import os
import sys

import requests

API_BASE = "https://api.explorium.ai/v1"


def _post(path, api_key, body):
    response = requests.post(
        f"{API_BASE}/{path}",
        json=body,
        headers={"Content-Type": "application/json", "api_key": api_key},
        timeout=60,
    )
    if not response.ok:
        raise SystemExit(f"Explorium API error {response.status_code} calling {path}: {_format_error(response)}")
    return response.json()


def _format_error(response):
    try:
        payload = response.json()
    except ValueError:
        return response.text
    detail = payload.get("detail")
    if isinstance(detail, list):
        messages = []
        for item in detail:
            loc = ".".join(str(part) for part in item.get("loc", []))
            messages.append(f"{loc}: {item.get('msg')}" if loc else str(item.get("msg")))
        return "; ".join(messages)
    return str(payload)


def fetch_saas_businesses_with_funding(api_key, countries, linkedin_categories, funding_window_days, company_sizes, size):
    body = {
        "mode": "full",
        "size": size,
        "page_size": size,
        "page": 1,
        "filters": {
            "country_code": {"values": countries},
            "linkedin_category": {"values": linkedin_categories},
            "events": {"values": ["new_funding_round"], "last_occurrence": funding_window_days},
            "company_size": {"values": company_sizes},
        },
    }
    return _post("businesses", api_key, body).get("data", [])


def fetch_prospects_for_businesses(api_key, business_ids, job_levels, job_titles, size):
    if not business_ids:
        return []
    body = {
        "mode": "full",
        "size": size,
        "page_size": size,
        "page": 1,
        "filters": {
            "business_id": {"values": business_ids},
            "job_level": {"values": job_levels},
            "job_title": {"values": job_titles, "include_related_job_titles": True},
        },
    }
    return _post("prospects", api_key, body).get("data", [])


def write_csv(rows, path):
    if not rows:
        # Still write a header-only file so connector.py has something to read.
        with open(path, "w", newline="", encoding="utf-8") as f:
            f.write("")
        return
    fieldnames = sorted({key for row in rows for key in row.keys()})
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def parse_args():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--api-key",
        default=os.environ.get("EXPLORIUM_API_KEY"),
        help="Explorium API key (env: EXPLORIUM_API_KEY).",
    )
    parser.add_argument("--countries", nargs="+", default=["US", "CA"])
    parser.add_argument("--linkedin-categories", nargs="+", default=["software development"])
    parser.add_argument("--funding-window-days", type=int, default=90)
    parser.add_argument(
        "--company-sizes",
        nargs="+",
        default=["51-200", "201-500"],
        help="Explorium company_size buckets (e.g. 51-200 201-500) - fixed enum, no free-form ranges.",
    )
    parser.add_argument("--job-levels", nargs="+", default=["director", "vice president"])
    parser.add_argument("--job-titles", nargs="+", default=["Business Development", "Marketing"])
    parser.add_argument("--max-businesses", type=int, default=200, help="Max matching businesses to scope prospects to.")
    parser.add_argument("--max-prospects", type=int, default=100, help="Max prospect rows to fetch.")
    parser.add_argument("--out", default="vibe_leads.csv")
    args = parser.parse_args()
    if not args.api_key:
        parser.error("--api-key/EXPLORIUM_API_KEY is required")
    return args


def main():
    args = parse_args()

    businesses = fetch_saas_businesses_with_funding(
        args.api_key, args.countries, args.linkedin_categories, args.funding_window_days,
        args.company_sizes, args.max_businesses,
    )
    business_ids = [b["business_id"] for b in businesses if b.get("business_id")]
    print(f"Found {len(business_ids)} matching businesses.", file=sys.stderr)

    prospects = fetch_prospects_for_businesses(
        args.api_key, business_ids, args.job_levels, args.job_titles, args.max_prospects,
    )
    print(f"Found {len(prospects)} matching prospects.", file=sys.stderr)

    write_csv(prospects, args.out)
    print(f"Wrote {len(prospects)} row(s) to {args.out}", file=sys.stderr)


if __name__ == "__main__":
    main()
