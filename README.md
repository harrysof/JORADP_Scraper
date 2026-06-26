# JORADP Scraper

A robust Python scraper to download PDF issues of the **Journal Officiel de la République Algérienne Démocratique et Populaire (JORADP)** in French.

The scraper downloads official gazette PDFs from URLs following the pattern:

```text
https://www.joradp.dz/FTP/JO-FRANCAIS/{YEAR}/F{YEAR}{ISSUE}.pdf
```

It supports resume functionality, automatic retries, metadata tracking, and downloading issues by year or in bulk.

---

## Features

* Downloads official JORADP PDF issues.
* Resume support (skips already downloaded files).
* Automatically organizes downloads by year.
* Stores download metadata in a JSON file.
* Automatic retry logic for transient failures.
* Stops scanning after multiple consecutive missing issues.
* Test mode for quick verification.
* Progress bars powered by `tqdm`.

---

## Python Version Requirement

> **Important:** This project requires **Python 3.12**.

The JORADP website currently uses legacy SSL/TLS behavior that is incompatible with newer Python/OpenSSL versions (such as Python 3.14), which may produce errors similar to:

```text
ssl.SSLError:
[SSL: UNSAFE_LEGACY_RENEGOTIATION_DISABLED]
unsafe legacy renegotiation disabled
```

For maximum compatibility, use **Python 3.12**.

---

## Installation

### 1. Install Python 3.12

Download and install Python 3.12 from the official Python website.

Verify your installation:

```bash
python --version
```

or

```bash
py -3.12 --version
```

### 2. Create a virtual environment

**Windows**

```bash
py -3.12 -m venv .venv
```

Activate it:

**Command Prompt**

```bash
.venv\Scripts\activate
```

**PowerShell**

```powershell
.venv\Scripts\Activate.ps1
```

**Linux / macOS**

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install requests tqdm
```

Or, if using a `requirements.txt`:

```bash
pip install -r requirements.txt
```

---

## Usage

Download every supported year:

```bash
python joradp_scraper.py
```

Download a specific year:

```bash
python joradp_scraper.py --year 2025
```

Run a quick test (issues `001`–`010` of year `2000`):

```bash
python joradp_scraper.py --test
```

Enable verbose HTTP logging:

```bash
python joradp_scraper.py --verbose
```

---

## Output Structure

```text
data/
├── metadata.json
└── raw/
    ├── 2000/
    │   ├── F2000001.pdf
    │   ├── F2000002.pdf
    │   └── ...
    ├── 2001/
    └── ...
```

---

## Metadata Format

Each downloaded (or attempted) issue is recorded in `metadata.json`:

```json
{
  "2025": {
    "001": {
      "year": 2025,
      "issue": "001",
      "status": "complete",
      "url": "https://www.joradp.dz/FTP/JO-FRANCAIS/2025/F2025001.pdf"
    }
  }
}
```

Possible status values:

* `complete`
* `missing`
* `error`

---

## Resume Support

If a PDF already exists on disk and has a non-zero file size, it is skipped automatically, allowing interrupted downloads to resume without downloading the same file again.

---

## Dependencies

* Python 3.12
* requests
* tqdm

Install manually:

```bash
pip install requests tqdm
```

---

## Notes

* JORADP issues are numbered sequentially throughout the year (`001`, `002`, `003`, etc.).
* Not every issue number necessarily exists.
* The scraper records missing issues in the metadata file.
* A short delay is inserted between requests to reduce server load.

---

## Disclaimer

This project is intended for educational, archival, and research purposes. Please use it responsibly and respect the policies and terms of use of the JORADP website.
