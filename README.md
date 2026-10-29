# 🔍 GeoRank SEO - Google Local Rank Tracker (Flask)

A lightweight, powerful Python **Flask** web application and CLI tool designed for SEO projects. It searches any keyword on Google emulating a **specific geographic location** (city, state, country) using Google's official canonical **UULE geo-encoding** and retrieves the exact organic rank/placing of your target website.

---

## 🌟 Key Features

- **Hyper-Local Location Emulation (UULE + `gl`):** Uses Google's canonical coordinate encoding to simulate searches from any city or country (e.g. `Colombo, Sri Lanka`, `Austin, Texas, United States`, `London, UK`) without requiring expensive residential proxies or suffering VPN IP blocks.
- **Multi-Page Deep Scanning (Beyond Top 9):** Automatically pages through Google SERPs (Page 1, 2, 3, up to 10 pages / 100 results) to find your target website wherever it appears.
- **Complete Occurrence Count:** If your domain ranks with multiple pages, subdomains, or blog posts, GeoRank tracks the total count and lists every ranking URL with its exact rank and page number.
- **Flask Architecture:** Clean, lightweight Flask web server with RESTful API endpoints and a responsive, modern dashboard.
- **Exact Rank & Page Detection:** Identifies the precise organic placing (`#1`, `#14`, `#35`) and the SERP page number (Page 1, Page 2...).
- **Flexible Domain Matching:** Supports root domains (`coffee.lk`), subdomains (`shop.coffee.lk`), full URLs, or brand names.
- **Redirect Resolution:** Automatically unwinds modern Google redirect URLs (`/goto?url=...` or `/url?q=...`) to identify the final destination URL.
- **SERP Competitor Breakdown:** Displays the entire Top 10 to Top 100 competitor search engine results page with titles, snippets, and domains.
- **CSV & JSON Export:** 1-click export of ranking audits and competitor lists to CSV and JSON formats.
- **SQLite History Tracking:** Automatically stores every search and rank result locally so you can monitor SEO rank changes over time.
- **Dual Interface:** Run via the modern **Web Dashboard** or the automated **CLI Tool**.

---

## 📁 Project Structure

```
ESO-REPORT/
├── app.py                 # Flask server, web routes & REST API endpoints
├── rank_tracker.py        # Core SERP tracker, UULE encoder, stealth Selenium browser
├── database.py            # SQLite database manager for tracking history & exports
├── cli.py                 # Command-line interface for terminal searches & automation
├── requirements.txt       # Project dependencies
├── templates/
│   ├── base.html          # Base layout with Tailwind CSS & FontAwesome
│   └── index.html         # Interactive SEO dashboard, live rank card & SERP table
└── rank_tracker.db        # SQLite database (auto-generated)
```

---

## 🚀 Quick Start

### 1. Requirements

Ensure you have Python 3.10+ and Google Chrome installed on your system.

Install dependencies:
```bash
pip install -r requirements.txt
```

### 2. Launch the Flask Web Dashboard

Start the Flask server:
```bash
python app.py
```
Open your browser and navigate to:
```
http://127.0.0.1:5000
```

1. Enter your **Target Keyword** (e.g., `best coffee colombo`).
2. Enter your **Search Location** (e.g., `Colombo, Sri Lanka` or click one of the quick chips).
3. Enter your **Target Website** (e.g., `snippetsofwonders.com` or `coffee.lk`).
4. Select your **Search Depth** (Top 10, Top 20, Top 30, Top 50, Top 100).
5. Click **Check Google Placing**!

---

## 💻 Command Line Interface (CLI)

You can also run rank checks directly from the command line:

```bash
# Basic rank check
python cli.py -k "best coffee colombo" -l "Colombo, Sri Lanka" -t "snippetsofwonders.com" -n 20

# Output results in pure JSON (great for cron jobs or piping to other tools)
python cli.py -k "plumber near me" -l "Austin, Texas, United States" -t "example.com" --json
```

### CLI Arguments:
- `-k, --keyword`: Target keyword to query (Required)
- `-l, --location`: Canonical location string (e.g., `"Austin, Texas, United States"` or `"London, UK"`) (Required)
- `-t, --target`: Website domain or URL to find (Required)
- `-n, --max-results`: Number of organic results to inspect (default: `30`)
- `-c, --country`: 2-letter ISO country code override (`us`, `lk`, `uk`, `ca`, `au`, etc.)
- `--json`: Format output as JSON

---

## 🔌 REST API Endpoints

The Flask application exposes clean REST API endpoints for seamless integration:

### 1. Check Rank (`POST /api/check`)
**Request Body (JSON):**
```json
{
  "keyword": "best coffee colombo",
  "location": "Colombo, Sri Lanka",
  "target_website": "snippetsofwonders.com",
  "max_results": 20,
  "country_code": "lk"
}
```

**Response (JSON):**
```json
{
  "success": true,
  "keyword": "best coffee colombo",
  "location": "Colombo, Sri Lanka",
  "country_code": "lk",
  "target_website": "snippetsofwonders.com",
  "target_found": true,
  "rank": 1,
  "page": 1,
  "matched_item": {
    "rank": 1,
    "page": 1,
    "title": "Best Cafes to Work From in Colombo, Sri Lanka ...",
    "url": "https://snippetsofwonders.com/colombos-best-productivity-cafes-focus-and-fuel/",
    "display_url": "https://snippetsofwonders.com › Blog",
    "is_target": true
  },
  "total_extracted": 6,
  "duration_seconds": 28.5,
  "id": 1,
  "results": [ ... ]
}
```

### 2. Get Audit History (`GET /api/history?limit=20`)
Returns a list of previous rank checks from the local SQLite database.

### 3. Get Check Details (`GET /api/check/<id>`)
Returns full details and all SERP competitor results for a specific check.

### 4. Export to CSV (`GET /export/csv/<id>`)
Downloads a formatted `.csv` file containing:
- Rank
- Page
- Title
- Destination URL
- Display Domain
- Snippet description
- Is Target Website (YES/NO)

### 5. Export to JSON (`GET /export/json/<id>`)
Downloads the raw `.json` record of the search.

---

## 🧠 How Google Local SEO Emulation Works

Google personalizes search engine results pages based on IP geolocation and browser cookies. To get an **unbiased, repeatable rank**:

1. **UULE Parameter:** Google uses the `uule` parameter to set precise geographic coordinates. We calculate the canonical UULE string using Google's length-key hashing algorithm (`w+CAIQICI...`).
2. **Country Code (`gl`):** We append the two-letter ISO country code corresponding to your target country (e.g., `gl=lk`, `gl=us`, `gl=uk`).
3. **Stealth Headless Browser:** Selenium Chrome runs with flags that strip automation identifiers (`navigator.webdriver = undefined`), avoiding anti-bot CAPTCHAs while rendering dynamic JavaScript elements.
