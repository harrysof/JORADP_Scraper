#!/usr/bin/env python3
"""
JORADP Scraper — Download French official gazette PDFs from JORADP

URL pattern: https://www.joradp.dz/FTP/Jo-Francais/{YEAR}/F{YEAR}{ISSUE}.pdf
Each issue is ONE single PDF file.

Usage:
    python joradp_scraper.py              # Scrape all years 2000-2025
    python joradp_scraper.py --year 2020  # Scrape only 2020
    python joradp_scraper.py --test       # Quick test: year 2000, issues 001-010
    python joradp_scraper.py --interactive  # Interactive prompt for year(s) and months
    python joradp_scraper.py -i             # Same, short form

Note on months: JORADP issues are numbered sequentially (001–099) per year with
no month encoded in the URL. The month→issue mapping below is approximate based
on Algeria's typical ~7 issues/month publication rhythm (~84 issues/year).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Tuple

import requests
from tqdm import tqdm

# ── Configuration ────────────────────────────────────────────────────────────

BASE_URL = "https://www.joradp.dz/FTP/Jo-Francais"
DATA_DIR = Path("./data")
RAW_DIR = DATA_DIR / "raw"
METADATA_FILE = DATA_DIR / "metadata.json"

MAX_RETRIES = 3
TIMEOUT = 60                  # full issues can be large PDFs
CONSECUTIVE_MISSING_LIMIT = 10
DELAY = 0.5                   # polite delay between requests

CURRENT_YEAR = 2025

# ── Month → approximate issue range ─────────────────────────────────────────
# JORADP publishes ~7 issues/month (~84/year). These boundaries are approximate.
# Issues beyond the last real one for a year are automatically skipped (404).
MONTH_ISSUE_RANGES: Dict[int, Tuple[int, int]] = {
    1:  (1,  7),
    2:  (8,  14),
    3:  (15, 21),
    4:  (22, 28),
    5:  (29, 35),
    6:  (36, 42),
    7:  (43, 49),
    8:  (50, 56),
    9:  (57, 63),
    10: (64, 70),
    11: (71, 77),
    12: (78, 99),  # 99 = max; early stop kicks in on consecutive 404s
}

MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April",
    5: "May", 6: "June", 7: "July", 8: "August",
    9: "September", 10: "October", 11: "November", 12: "December",
}


# ── Interactive prompt helpers ───────────────────────────────────────────────

def _ask(prompt: str) -> str:
    """Print a prompt and return stripped user input."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print("\nAborted.")
        sys.exit(0)


def _parse_years(raw: str) -> List[int]:
    """
    Parse a year or year range from a string.

    Accepted formats:
        2020        → [2020]
        2010-2015   → [2010, 2011, 2012, 2013, 2014, 2015]
        all         → [2000 … CURRENT_YEAR]
    """
    raw = raw.lower().strip()
    if raw in ("all", ""):
        return list(range(2000, CURRENT_YEAR + 1))
    if "-" in raw:
        parts = raw.split("-")
        if len(parts) == 2:
            try:
                start, end = int(parts[0]), int(parts[1])
                if 1962 <= start <= end <= CURRENT_YEAR:
                    return list(range(start, end + 1))
            except ValueError:
                pass
    try:
        y = int(raw)
        if 1962 <= y <= CURRENT_YEAR:
            return [y]
    except ValueError:
        pass
    return []


def _parse_months(raw: str) -> Tuple[int, int]:
    """
    Parse a month selection and return the (first_issue, last_issue) range.

    Accepted formats:
        all             → issues 1–99
        1               → January only
        3-6             → March through June
        jan             → January only (3-letter abbreviation)
        jan-jun         → January through June
    """
    raw = raw.lower().strip()
    if raw in ("all", ""):
        return (1, 99)

    # Build name → number lookup (full name + 3-letter abbrev)
    name_map: Dict[str, int] = {}
    for num, name in MONTH_NAMES.items():
        name_map[name.lower()] = num
        name_map[name.lower()[:3]] = num

    def _to_month_num(token: str) -> int | None:
        token = token.strip()
        if token in name_map:
            return name_map[token]
        try:
            n = int(token)
            if 1 <= n <= 12:
                return n
        except ValueError:
            pass
        return None

    if "-" in raw:
        parts = raw.split("-", 1)
        m1 = _to_month_num(parts[0])
        m2 = _to_month_num(parts[1])
        if m1 and m2 and m1 <= m2:
            return (MONTH_ISSUE_RANGES[m1][0], MONTH_ISSUE_RANGES[m2][1])

    m = _to_month_num(raw)
    if m:
        return MONTH_ISSUE_RANGES[m]

    return (0, 0)   # sentinel: invalid


def prompt_interactive() -> Tuple[List[int], range]:
    """
    Run the interactive prompt and return (years, issue_range).
    """
    print()
    print("╔══════════════════════════════════════════════════════════╗")
    print("║         JORADP Interactive Scraper — Setup               ║")
    print("╚══════════════════════════════════════════════════════════╝")
    print()

    # ── Year(s) ──────────────────────────────────────────────────────────
    print("  Year(s) to scrape:")
    print("    • A single year       →  2020")
    print("    • A range of years    →  2010-2015")
    print("    • Everything          →  all  (2000–2025)")
    print()
    years: List[int] = []
    while not years:
        raw = _ask("  Year(s): ")
        years = _parse_years(raw)
        if not years:
            print(f"  ✗ Could not parse '{raw}'. Try: 2020 | 2010-2015 | all")
    print(f"  ✓ Years  : {years[0]}–{years[-1]}  ({len(years)} year(s))")
    print()

    # ── Month(s) ─────────────────────────────────────────────────────────
    print("  Month(s) to scrape  (issues are approximate — ~7 issues/month):")
    print("    • A single month      →  3      or  march")
    print("    • A range of months   →  3-6    or  mar-jun")
    print("    • All months          →  all    or  just press Enter")
    print()
    first_issue, last_issue = 0, 0
    while first_issue == 0 and last_issue == 0:
        raw = _ask("  Month(s): ")
        first_issue, last_issue = _parse_months(raw)
        if first_issue == 0 and last_issue == 0:
            print(f"  ✗ Could not parse '{raw}'. Try: 3 | mar | 3-6 | mar-jun | all")

    if (first_issue, last_issue) == (1, 99):
        print(f"  ✓ Months : all  (issues 001–099 per year)")
    else:
        # Figure out which month names we landed on for display
        m_start = next(
            (m for m, (s, _) in MONTH_ISSUE_RANGES.items() if s == first_issue), "?"
        )
        m_end = next(
            (m for m, (_, e) in MONTH_ISSUE_RANGES.items() if e == last_issue), "?"
        )
        name_start = MONTH_NAMES.get(m_start, "?")
        name_end   = MONTH_NAMES.get(m_end, "?")
        print(
            f"  ✓ Months : {name_start}–{name_end}  "
            f"(approx. issues {first_issue:03d}–{last_issue:03d} per year)"
        )

    print()
    print("  ─────────────────────────────────────────────────────────")
    print(f"  Ready to scrape {len(years)} year(s), issues {first_issue:03d}–{last_issue:03d}")
    print("  ─────────────────────────────────────────────────────────")
    print()
    confirm = _ask("  Start? [Y/n]: ").lower()
    if confirm not in ("", "y", "yes"):
        print("  Aborted.")
        sys.exit(0)
    print()

    return years, range(first_issue, last_issue + 1)




# ── URL / path helpers ───────────────────────────────────────────────────────

def build_url(year: int, issue: str) -> str:
    """https://www.joradp.dz/FTP/Jo-Francais/2000/F2000005.pdf"""
    return f"{BASE_URL}/{year}/F{year}{issue}.pdf"


def build_filepath(year: int, issue: str) -> Path:
    """./data/raw/2000/F2000005.pdf"""
    return RAW_DIR / str(year) / f"F{year}{issue}.pdf"


# ── Metadata I/O ─────────────────────────────────────────────────────────────

def load_metadata() -> Dict:
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, "r", encoding="utf-8") as fh:
                return json.load(fh)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_metadata(metadata: Dict) -> None:
    METADATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(METADATA_FILE, "w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2, ensure_ascii=False)


# ── Download logic ───────────────────────────────────────────────────────────

def download_issue(
    session: requests.Session,
    year: int,
    issue: str,
    verbose: bool = False,
) -> str:
    """
    Download one full issue PDF. Streams to disk to handle large files.

    Returns
    -------
    'exists'    — already downloaded (resume support)
    'downloaded'— newly downloaded OK
    'missing'   — 404 (issue doesn't exist)
    'error'     — unrecoverable error after retries
    """
    url = build_url(year, issue)
    filepath = build_filepath(year, issue)

    # ── Resume support ─────────────────────────────────────────────────
    if filepath.exists() and filepath.stat().st_size > 0:
        if verbose:
            tqdm.write(f"      ✓ already exists: {filepath.name}")
        return "exists"

    # ── Download with retries ──────────────────────────────────────────
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            if verbose:
                tqdm.write(f"      → GET {url}  (attempt {attempt})")

            # stream=True so we don't load the entire PDF into RAM
            resp = session.get(url, timeout=TIMEOUT, stream=True)

            if resp.status_code == 404:
                return "missing"

            if resp.status_code == 200:
                filepath.parent.mkdir(parents=True, exist_ok=True)
                with open(filepath, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=8192):
                        if chunk:
                            fh.write(chunk)
                return "downloaded"

            # Other HTTP status — retry with back-off
            if attempt < MAX_RETRIES:
                tqdm.write(
                    f"    ⚠ HTTP {resp.status_code}, retry {attempt}/{MAX_RETRIES}"
                )
                time.sleep(2 ** attempt)
            else:
                tqdm.write(
                    f"    ✗ HTTP {resp.status_code} after {MAX_RETRIES} tries: {url}"
                )
                return "error"

        except requests.ConnectionError:
            if attempt < MAX_RETRIES:
                tqdm.write(
                    f"    ⚠ Connection error (retry {attempt}/{MAX_RETRIES})"
                )
                time.sleep(2 ** attempt)
            else:
                tqdm.write(f"    ✗ Connection failed 3×: {url}")
                return "error"

        except requests.Timeout:
            if attempt < MAX_RETRIES:
                tqdm.write(
                    f"    ⚠ Timeout {TIMEOUT}s (retry {attempt}/{MAX_RETRIES})"
                )
                time.sleep(2 ** attempt)
            else:
                tqdm.write(f"    ✗ Timed out 3×: {url}")
                return "error"

        except requests.RequestException as exc:
            tqdm.write(f"    ✗ Unexpected: {exc}")
            return "error"

    return "error"


# ── CLI & main loop ─────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Download French PDFs from the Algerian Official Gazette (JORADP)"
    )
    parser.add_argument(
        "--year", type=int, default=None,
        help="Scrape only a specific year (e.g. 2020)",
    )
    parser.add_argument(
        "--test", action="store_true",
        help="Test mode: year 2000, issues 001-010 only",
    )
    parser.add_argument(
        "--interactive", "-i", action="store_true",
        help="Interactive prompt: choose year(s) and month(s) before scraping",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Show every HTTP request",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.test:
        years = [2000]
        issue_range = range(1, 11)       # 001 – 010
    elif args.year:
        years = [args.year]
        issue_range = range(1, 100)      # 001 – 099
    else:
        years = range(2000, 2026)
        issue_range = range(1, 100)

    metadata = load_metadata()

    session = requests.Session()
    session.headers.update({
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "application/pdf,*/*",
    })

    total_downloaded = 0
    total_skipped = 0

    for year in years:
        year_key = str(year)
        if year_key not in metadata:
            metadata[year_key] = {}

        tqdm.write(f"\n{'═' * 58}")
        tqdm.write(f"  Scraping year {year}")
        tqdm.write(f"{'═' * 58}")

        consecutive_missing = 0

        for issue_num in tqdm(
            issue_range,
            desc=f"Year {year}",
            unit="issue",
            leave=True,
            file=sys.stdout,
        ):
            issue = f"{issue_num:03d}"
            result = download_issue(session, year, issue, verbose=args.verbose)

            # ── Record metadata ─────────────────────────────────────────
            if result in ("downloaded", "exists"):
                status = "complete"
                if result == "downloaded":
                    total_downloaded += 1
                else:
                    total_skipped += 1
            elif result == "missing":
                status = "missing"
            else:
                status = "error"

            metadata[year_key][issue] = {
                "year": year,
                "issue": issue,
                "status": status,
                "url": build_url(year, issue),
            }

            tqdm.write(
                f"  Year {year} | Issue {issue} | {status.upper()}"
            )

            # ── Early stop on consecutive missing ───────────────────────
            if status == "missing":
                consecutive_missing += 1
                if consecutive_missing >= CONSECUTIVE_MISSING_LIMIT and not args.test:
                    tqdm.write(
                        f"  ⏭  {CONSECUTIVE_MISSING_LIMIT} missing in a row "
                        f"— skipping rest of {year}"
                    )
                    break
            else:
                consecutive_missing = 0

            # ── Save metadata after every issue ─────────────────────────
            save_metadata(metadata)

            # ── Polite delay ────────────────────────────────────────────
            time.sleep(DELAY)

    save_metadata(metadata)
    tqdm.write(f"\n✓ Done!")
    tqdm.write(f"  Downloaded : {total_downloaded}")
    tqdm.write(f"  Skipped    : {total_skipped} (already existed)")
    tqdm.write(f"  PDFs       → {RAW_DIR.resolve()}")
    tqdm.write(f"  Metadata   → {METADATA_FILE.resolve()}")


if __name__ == "__main__":
    main()