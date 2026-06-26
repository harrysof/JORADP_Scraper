# JORADP Scraper

A robust Python scraper to download PDF issues of the Algerian Official Gazette (**Journal Officiel de la République Algérienne Démocratique et Populaire – JORADP**) in French.

The scraper targets the following URL pattern:

```
https://www.joradp.dz/FTP/Jo-Francais/{YEAR}/F{YEAR}{ISSUE}.pdf
```

It includes features such as interactive prompts, resume support, retry logic, and polite rate limiting.

---

## Features

* **Multiple Modes:** Run a full scrape (2000–2025), target a specific year, run a quick test, or use the interactive CLI prompt.
* **Interactive CLI:** Guide the scraper by specifying year ranges (`2010-2015`) and month ranges (`mar-jun`) through a user-friendly prompt.
* **Resume Support:** Automatically skips PDFs that have already been downloaded to save bandwidth and time.
* **Smart Early Stopping:** Stops scraping a year if it hits **10 consecutive 404 (missing)** issues, preventing unnecessary requests.
* **Robust Fetching:** Includes retry logic with exponential backoff for timeouts and connection errors.
* **Metadata Tracking:** Saves a `metadata.json` file logging the status (`complete`, `missing`, `error`) and URL of every issue checked.
* **Polite Scraping:** Implements a configurable delay between requests to avoid overloading the JORADP servers.

---

# Installation

## Prerequisites

* Python 3.8+
* `pip` package manager

## Setup

Clone the repository (or save the script as `main.py`):

```bash
git clone https://github.com/yourusername/joradp-scraper.git
cd joradp-scraper
```

Install the required Python dependencies:

```bash
pip install requests tqdm
```

---

# Usage

You can run the scraper in several ways depending on your needs:

```bash
# 1. Full Scrape: Download all issues from 2000 to 2025
python main.py

# 2. Specific Year: Scrape only the year 2020
python main.py --year 2020

# 3. Quick Test: Scrape year 2000, issues 001-010 only
python main.py --test

# 4. Interactive Mode: Prompt for year(s) and month(s)
python main.py --interactive

# Short form
python main.py -i

# 5. Verbose Mode: Show every HTTP request and retry attempt
python main.py -v
```

---

# Interactive Mode Examples

When you run:

```bash
python main.py -i
```

you will be prompted to enter years and months.

Accepted formats include:

* **Years:** `2020`, `2010-2015`, or `all`
* **Months:** `3` (March), `mar`, `3-6` (March to June), `mar-jun`, or `all`

> **Note:** JORADP issues are numbered sequentially per year. The month mapping is approximate based on Algeria's typical publication rhythm of roughly **7 issues per month**.

---

# Project Structure & Output

Running the scraper creates the following directory structure:

```text
.
├── main.py
└── data/
    ├── metadata.json
    └── raw/
        ├── 2000/
        │   ├── F2000001.pdf
        │   ├── F2000002.pdf
        │   └── ...
        ├── 2020/
        │   ├── F2020001.pdf
        │   └── ...
        └── ...
```

## `data/metadata.json`

This file records the status of every issue processed.

Example:

```json
{
  "2020": {
    "001": {
      "year": 2020,
      "issue": "001",
      "status": "complete",
      "url": "https://www.joradp.dz/FTP/Jo-Francais/2020/F2020001.pdf"
    }
  }
}
```

---

# Configuration

You can customize the scraper by modifying the constants at the top of `main.py`.

| Variable                    | Default                | Description                                                             |
| --------------------------- | ---------------------- | ----------------------------------------------------------------------- |
| `DATA_DIR`                  | `./data`               | Root directory for output files.                                        |
| `RAW_DIR`                   | `./data/raw`           | Directory where downloaded PDFs are stored.                             |
| `METADATA_FILE`             | `./data/metadata.json` | Path to the metadata JSON file.                                         |
| `MAX_RETRIES`               | `3`                    | Number of retry attempts for failed requests.                           |
| `TIMEOUT`                   | `60`                   | HTTP timeout in seconds (large PDFs may take time).                     |
| `CONSECUTIVE_MISSING_LIMIT` | `10`                   | Number of consecutive 404 responses before skipping to the next year.   |
| `DELAY`                     | `0.5`                  | Delay in seconds between HTTP requests to avoid overloading the server. |

---

# Disclaimer

This tool is intended for **educational and research purposes**. JORADP issues are public records. Please use the built-in delays and avoid aggressive or highly parallel scraping in order to be respectful of the `joradp.dz` servers.
