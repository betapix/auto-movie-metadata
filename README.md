## Auto Movie Metadata

![Cover](https://via.placeholder.com/1200x360?text=Auto+Movie+Metadata)

Badges: ![Python](https://img.shields.io/badge/Python-3.11-blue) ![License](https://img.shields.io/badge/License-BSD%203--Clause-green) ![Schedule](https://img.shields.io/badge/Schedule-*/15min-lightgrey)

— by Abdul Mueed (Pakistan) · [GitHub](https://github.com/betapix) · [Website](https://am-abdulmueed.vercel.app) · am-abdulmueed3@gmail.com

---

### Overview (EN)
This repository automatically fetches and aggregates movie and TV metadata from TMDb, TVMaze, and Wikidata, then publishes a ready-to-consume `movies.json` and a compressed `movies.json.gz` for fast downloads. It runs every 15 minutes on GitHub Actions and supports incremental crawling so coverage continuously grows.

### تعارف (Urdu)
Yeh repo TMDb, TVMaze aur Wikidata se movies/TV shows ka metadata auto-fetch karta hai. Output `movies.json` aur tez download ke liye `movies.json.gz` generate hoti hai. Workflow har 15 minutes me chalta hai aur incremental crawling se coverage barhti rehti hai.

---

### Key Features
- Multi-source aggregation: TMDb (movies + TV), TVMaze, Wikidata
- Categories + pagination (movies: trending/popular/top_rated/now_playing/upcoming/latest; TV: trending/popular/top_rated/on_the_air/airing_today)
- Robust retries, timeouts, and exponential backoff
- Trailer cleanup: prefer Official YouTube; cap to max 2 per title
- OTT provider availability via TMDb watch/providers
- Gzip output (`movies.json.gz`) for faster delivery
- GitHub Actions automation (every 15 minutes) with queued concurrency (no overlap)
- Incremental crawl scaffolding (state + tunable ENV)

---

### Data Sources
- TMDb (The Movie Database) — API v3/v4
- TVMaze — public API
- Wikidata — SPARQL endpoint

> Note: Coverage depends on these aggregators; not a 1:1 mirror of all OTT catalogs.

---

### Outputs
- `movies.json`: Human-readable JSON (large)
- `movies.json.gz`: Compressed JSON (recommended for apps)

Example top-level structure:
```json
{
  "developer": {
    "name": "Abdul Mueed",
    "github": "https://github.com/betapix",
    "contact": "am-abdulmueed3@gmail.com",
    "website": "https://am-abdulmueed.vercel.app"
  },
  "last_updated": "2025-09-25T00:00:00Z",
  "total_entries": 5707,
  "breakdown": {
    "tmdb_movies": 1000,
    "tmdb_tv": 1200,
    "tvmaze_shows": 3500,
    "wikidata_movies": 7
  },
  "tmdb_categories": { "trending": 200, "popular": 200 },
  "tmdb_tv_categories": { "trending": 200 },
  "movies": []
}
```

Each item contains common fields like `id`, `title`, `year`, `overview`, `poster`, `rating`, `genres`, `cast`, `trailers` (max 2), `providers`, and `category`.

---

### Quick Start (Local)
1) Python 3.11+ required
2) Set TMDb credentials as environment variables:
```bash
# Windows PowerShell
$env:TMDB_API_KEY="<your_tmdb_v3_key>"
$env:TMDB_ACCESS_TOKEN="<your_tmdb_v4_bearer>"
```
3) Install dependency:
```bash
pip install requests
```
4) Run:
```bash
python update_data.py
```

Optional ENV for tuning:
```bash
# Pages fetched per category per run (default 10)
$env:PAGES_PER_CATEGORY="30"
# Sleep between requests in ms (default 200)
$env:SLEEP_MS="200"
```

---

### GitHub Actions (CI)
- Schedule: every 15 minutes
- Concurrency: queued (no overlapping runs)
- Commits: `movies.json`, `movies.json.gz` (and can include `state.json` when enabled)

Secrets needed:
- `TMDB_API_KEY`: TMDb v3 API Key
- `TMDB_ACCESS_TOKEN`: TMDb v4 Access Token (Bearer)

Optional ENV (uncomment in workflow):
- `PAGES_PER_CATEGORY`: pages per run per category
- `SLEEP_MS`: millis between requests

The workflow file also includes bilingual (Urdu/English) comments for quick onboarding.

---

### Consuming the Data
Use the compressed `movies.json.gz` in your app for speed.

JavaScript (browser/Node):
```js
async function fetchMovies() {
  const res = await fetch('https://raw.githubusercontent.com/<user>/<repo>/main/movies.json.gz');
  const buffer = await res.arrayBuffer();
  // Use a gzip decompression lib (e.g., fflate) in browser
  // const decompressed = fflate.decompressSync(new Uint8Array(buffer));
  // const text = new TextDecoder().decode(decompressed);
  // const data = JSON.parse(text);
}
```

Python:
```python
import gzip, json, urllib.request
with urllib.request.urlopen('https://raw.githubusercontent.com/<user>/<repo>/main/movies.json.gz') as resp:
    with gzip.GzipFile(fileobj=resp) as f:
        data = json.loads(f.read().decode('utf-8'))
print(len(data.get('movies', [])))
```

---

### Incremental Crawling (Roadmap/Config)
- `state.json` maintains cursors per category (and year-buckets; when enabled).
- Each queued CI run continues from the last fetched page window.
- Increase `PAGES_PER_CATEGORY` over time to accelerate coverage.

Advanced (optional):
- Discover endpoints with year buckets (movies/TV) for deep back-catalog
- MongoDB upsert with unique indexes for dedupe
- Matrix CI to shard crawl across categories/years

---

### Screenshots / Images
- Cover: `https://via.placeholder.com/1200x360?text=Auto+Movie+Metadata`
- You can add your own screenshots to `docs/` and reference them here.

---

### Author
- Name: Abdul Mueed (Pakistan)
- GitHub: https://github.com/betapix
- Website: https://am-abdulmueed.vercel.app
- Email: am-abdulmueed3@gmail.com

---

### License
BSD 3-Clause — Free to use, modify, and distribute with attribution. Copyright © Abdul Mueed.


