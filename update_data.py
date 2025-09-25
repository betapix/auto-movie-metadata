"""
Movie Metadata Auto-Updater
----------------------------
Developer: Abdul Mueed  From Pakistan
Email: am-abdulmueed3@gmail.com
github: https://github.com/betapix 
Website: https://am-abdulmueed.vercel.app
LICIENCE: BSD 3-Clause
--------------------------------------------

Description:
Automatically fetches movie metadata from TMDb, TVMaze, and Wikidata,
and generates movies.json for apps or websites.

License:
MIT License — Free to use, modify, and distribute with attribution.
"""

import requests
import json
import os
import time
from datetime import datetime, timezone
import gzip
from typing import Dict, Any

# TMDb API keys
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_ACCESS_TOKEN = os.environ.get("TMDB_ACCESS_TOKEN")

# Config via environment
def _get_int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, str(default)))
    except Exception:
        return default

PAGES_PER_CATEGORY = _get_int_env("PAGES_PER_CATEGORY", 10)
SLEEP_MS = _get_int_env("SLEEP_MS", 200)

def sleep_ms(ms: int) -> None:
    if ms and ms > 0:
        time.sleep(ms / 1000.0)

# Incremental state management
STATE_FILE = "state.json"

def load_state() -> Dict[str, Any]:
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state: Dict[str, Any]) -> None:
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[STATE] Failed to save state: {e}")

def get_start_page(state: Dict[str, Any], namespace: str, key: str, default_start: int = 1) -> int:
    return int(((state or {}).get(namespace, {}) or {}).get(key, {}).get("next_page", default_start))

def set_next_page(state: Dict[str, Any], namespace: str, key: str, next_page: int) -> None:
    if namespace not in state:
        state[namespace] = {}
    if key not in state[namespace]:
        state[namespace][key] = {}
    state[namespace][key]["next_page"] = int(next_page)

if not TMDB_API_KEY or not TMDB_ACCESS_TOKEN:
    print("[ERROR] TMDB_API_KEY or TMDB_ACCESS_TOKEN not set in environment variables.")
    exit(1)

CURRENCY_MAP = {
    "US": "$", "GB": "£", "EU": "€", "IN": "₹", "JP": "¥"
}


def fetch_tmdb():
    print("[INFO] Fetching MAXIMUM TMDb data from all categories...")
    
    # Define all categories with pagination support
    categories = {
        "trending": "https://api.themoviedb.org/3/trending/movie/week",
        "popular": "https://api.themoviedb.org/3/movie/popular", 
        "top_rated": "https://api.themoviedb.org/3/movie/top_rated",
        "now_playing": "https://api.themoviedb.org/3/movie/now_playing",
        "upcoming": "https://api.themoviedb.org/3/movie/upcoming",
        "latest": "https://api.themoviedb.org/3/movie/latest"
    }
    
    # Pages to fetch per category (increase for more data)
    PAGES_PER_CATEGORY = 10  # Fetch 10 pages = 200 movies per category
    all_movies = []
    
    for category, base_url in categories.items():
        print(f"[INFO] Fetching {category} movies (up to {PAGES_PER_CATEGORY} pages = {PAGES_PER_CATEGORY * 20} movies)...")
        category_movies = []
        
        for page in range(1, PAGES_PER_CATEGORY + 1):
            try:
                url = f"{base_url}?api_key={TMDB_API_KEY}&page={page}"
                
                # Retry logic for each page
                for attempt in range(3):
                    try:
                        res = requests.get(url, timeout=60)  # Increased timeout
                        if res.status_code == 200:
                            break
                        else:
                            print(f"[TMDb {category} Page {page} Retry {attempt+1}] Status Code: {res.status_code}")
                            if attempt < 2:
                                time.sleep(5)
                    except Exception as e:
                        print(f"[TMDb {category} Page {page} Retry {attempt+1}] {e}")
                        if attempt < 2:
                            time.sleep(5)
                else:
                    print(f"[TMDb Error] Failed to fetch {category} page {page} after retries")
                    continue

                page_movies = []
                for movie in res.json().get("results", []):
                    release_date = movie.get("release_date")
                    year = release_date[:4] if release_date else "N/A"
                    movie_id = movie.get("id")

                    try:
                        # Movie details with retry logic
                        details = None
                        for attempt in range(2):
                            try:
                                details = requests.get(
                                    f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={TMDB_API_KEY}&append_to_response=watch/providers",
                                    timeout=60
                                ).json()
                                break
                            except Exception as e:
                                print(f"[TMDb Details Retry {attempt+1}] {movie.get('title')}: {e}")
                                if attempt < 1:
                                    time.sleep(3)

                        if not details:
                            continue

                        # Credits with retry logic
                        credits = None
                        for attempt in range(2):
                            try:
                                credits = requests.get(
                                    f"https://api.themoviedb.org/3/movie/{movie_id}/credits?api_key={TMDB_API_KEY}",
                                    timeout=60
                                ).json()
                                break
                            except Exception as e:
                                print(f"[TMDb Credits Retry {attempt+1}] {movie.get('title')}: {e}")
                                if attempt < 1:
                                    time.sleep(3)

                        if not credits:
                            credits = {"cast": [], "crew": []}

                        cast_list = [
                            {
                                "name": c.get("name"),
                                "character": c.get("character"),
                                "profile": f"https://image.tmdb.org/t/p/w300{c.get('profile_path')}" if c.get("profile_path") else ""
                            }
                            for c in credits.get("cast", [])[:10]
                        ]

                        directors = [
                            c.get("name") for c in credits.get("crew", [])
                            if c.get("job") == "Director"
                        ]

                        writers = [
                            c.get("name") for c in credits.get("crew", [])
                            if c.get("job") in ["Writer", "Screenplay", "Story"]
                        ]

                        # Trailers with retry logic (dedupe and cap: prefer official YouTube, max 2)
                        trailers = []
                        for attempt in range(2):
                            try:
                                videos = requests.get(
                                    f"https://api.themoviedb.org/3/movie/{movie_id}/videos?api_key={TMDB_API_KEY}",
                                    timeout=60
                                ).json().get("results", [])

                                def trailer_priority(v):
                                    # Higher is better
                                    is_youtube = 1 if v.get("site") == "YouTube" else 0
                                    is_official = 1 if v.get("official") else 0
                                    name = (v.get("name") or "").lower()
                                    name_bonus = 1 if "official trailer" in name else 0
                                    type_val = v.get("type") or ""
                                    type_rank = {"Trailer": 3, "Teaser": 2, "Clip": 1}.get(type_val, 0)
                                    date = v.get("published_at") or ""
                                    return (is_youtube, is_official, name_bonus, type_rank, date)

                                # Sort by priority and pick top 2 unique URLs
                                sorted_videos = sorted(videos, key=trailer_priority, reverse=True)
                                seen = set()
                                for v in sorted_videos:
                                    url = None
                                    if v.get("site") == "YouTube" and v.get("key"):
                                        url = f"https://www.youtube.com/watch?v={v.get('key')}"
                                    elif v.get("url"):
                                        url = v.get("url")
                                    if not url or url in seen:
                                        continue
                                    seen.add(url)
                                    trailers.append(url)
                                    if len(trailers) >= 2:
                                        break
                                break
                            except Exception as e:
                                print(f"[TMDb Videos Retry {attempt+1}] {movie.get('title')}: {e}")
                                if attempt < 1:
                                    time.sleep(3)

                        # Currency sign
                        country_code = details.get("production_countries")[0]["iso_3166_1"] if details.get("production_countries") else "US"
                        currency_symbol = CURRENCY_MAP.get(country_code, "$")

                        # OTT providers
                        providers = details.get("watch/providers", {}).get("results", {})

                        page_movies.append({
                            "id": movie_id,
                            "title": movie.get("title"),
                            "year": year,
                            "overview": movie.get("overview") or "",
                            "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else "",
                            "rating": movie.get("vote_average") or None,
                            "genres": [g["name"] if isinstance(g, dict) else g for g in details.get("genres", [])],
                            "budget": f"{currency_symbol}{details.get('budget', 0):,}" if details.get("budget") else None,
                            "revenue": f"{currency_symbol}{details.get('revenue', 0):,}" if details.get("revenue") else None,
                            "directors": directors,
                            "writers": writers,
                            "cast": cast_list,
                            "trailers": trailers,
                            "networks": [n["name"] for n in details.get("networks", [])],
                            "origin_country": country_code,
                            "providers": providers,
                            "production_companies": [pc["name"] for pc in details.get("production_companies", [])],
                            "category": category,
                            "source": "TMDb"
                        })

                    except Exception as e:
                        print(f"[TMDb Movie Error] {movie.get('title')} ({movie_id}): {e}")

                category_movies.extend(page_movies)
                print(f"[INFO] {category} Page {page}: {len(page_movies)} movies fetched")

            except Exception as e:
                print(f"[TMDb {category} Page {page} Error] {e}")

        all_movies.extend(category_movies)
        print(f"[INFO] {category} Total: {len(category_movies)} movies fetched")
        
    return all_movies


def fetch_tmdb_tv():
    print("[INFO] Fetching MAXIMUM TMDb TV series from all categories...")
    categories = {
        "trending": "https://api.themoviedb.org/3/trending/tv/week",
        "popular": "https://api.themoviedb.org/3/tv/popular",
        "top_rated": "https://api.themoviedb.org/3/tv/top_rated",
        "on_the_air": "https://api.themoviedb.org/3/tv/on_the_air",
        "airing_today": "https://api.themoviedb.org/3/tv/airing_today"
    }
    PAGES_PER_CATEGORY = 10
    all_series = []

    for category, base_url in categories.items():
        print(f"[INFO] Fetching TV {category} (up to {PAGES_PER_CATEGORY} pages)...")
        category_items = []
        for page in range(1, PAGES_PER_CATEGORY + 1):
            try:
                url = f"{base_url}?api_key={TMDB_API_KEY}&page={page}"
                for attempt in range(3):
                    try:
                        res = requests.get(url, timeout=60)
                        if res.status_code == 200:
                            break
                        else:
                            print(f"[TMDb TV {category} Page {page} Retry {attempt+1}] Status Code: {res.status_code}")
                            if attempt < 2:
                                time.sleep(5)
                    except Exception as e:
                        print(f"[TMDb TV {category} Page {page} Retry {attempt+1}] {e}")
                        if attempt < 2:
                            time.sleep(5)
                else:
                    print(f"[TMDb TV Error] Failed to fetch {category} page {page} after retries")
                    continue

                page_items = []
                for show in res.json().get("results", []):
                    tv_id = show.get("id")
                    name = show.get("name")
                    first_air_date = show.get("first_air_date")
                    year = first_air_date[:4] if first_air_date else "N/A"

                    try:
                        # Details
                        details = None
                        for attempt in range(2):
                            try:
                                details = requests.get(
                                    f"https://api.themoviedb.org/3/tv/{tv_id}?api_key={TMDB_API_KEY}&append_to_response=watch/providers",
                                    timeout=60
                                ).json()
                                break
                            except Exception as e:
                                print(f"[TMDb TV Details Retry {attempt+1}] {name}: {e}")
                                if attempt < 1:
                                    time.sleep(3)
                        if not details:
                            continue

                        # Credits
                        credits = None
                        for attempt in range(2):
                            try:
                                credits = requests.get(
                                    f"https://api.themoviedb.org/3/tv/{tv_id}/credits?api_key={TMDB_API_KEY}",
                                    timeout=60
                                ).json()
                                break
                            except Exception as e:
                                print(f"[TMDb TV Credits Retry {attempt+1}] {name}: {e}")
                                if attempt < 1:
                                    time.sleep(3)
                        if not credits:
                            credits = {"cast": [], "crew": []}

                        cast_list = [
                            {
                                "name": c.get("name"),
                                "character": c.get("character"),
                                "profile": f"https://image.tmdb.org/t/p/w300{c.get('profile_path')}" if c.get("profile_path") else ""
                            }
                            for c in credits.get("cast", [])[:10]
                        ]

                        creators = [c.get("name") for c in details.get("created_by", [])]

                        # Trailers (TV)
                        trailers = []
                        for attempt in range(2):
                            try:
                                videos = requests.get(
                                    f"https://api.themoviedb.org/3/tv/{tv_id}/videos?api_key={TMDB_API_KEY}",
                                    timeout=60
                                ).json().get("results", [])
                                def trailer_priority(v):
                                    is_youtube = 1 if v.get("site") == "YouTube" else 0
                                    is_official = 1 if v.get("official") else 0
                                    name = (v.get("name") or "").lower()
                                    name_bonus = 1 if "official trailer" in name else 0
                                    type_rank = {"Trailer": 3, "Teaser": 2, "Clip": 1}.get(v.get("type") or "", 0)
                                    date = v.get("published_at") or ""
                                    return (is_youtube, is_official, name_bonus, type_rank, date)
                                sorted_videos = sorted(videos, key=trailer_priority, reverse=True)
                                seen = set()
                                for v in sorted_videos:
                                    url = None
                                    if v.get("site") == "YouTube" and v.get("key"):
                                        url = f"https://www.youtube.com/watch?v={v.get('key')}"
                                    elif v.get("url"):
                                        url = v.get("url")
                                    if not url or url in seen:
                                        continue
                                    seen.add(url)
                                    trailers.append(url)
                                    if len(trailers) >= 2:
                                        break
                                break
                            except Exception as e:
                                print(f"[TMDb TV Videos Retry {attempt+1}] {name}: {e}")
                                if attempt < 1:
                                    time.sleep(3)

                        providers = details.get("watch/providers", {}).get("results", {})
                        origin_countries = details.get("origin_country") or []
                        origin_country = origin_countries[0] if origin_countries else "US"

                        page_items.append({
                            "id": tv_id,
                            "title": name,
                            "year": year,
                            "overview": details.get("overview") or "",
                            "poster": f"https://image.tmdb.org/t/p/w500{show.get('poster_path')}" if show.get("poster_path") else "",
                            "rating": show.get("vote_average") or None,
                            "genres": [g.get("name") for g in details.get("genres", [])],
                            "creators": creators,
                            "cast": cast_list,
                            "trailers": trailers,
                            "origin_country": origin_country,
                            "providers": providers,
                            "category": category,
                            "type": "tv",
                            "source": "TMDb"
                        })
                    except Exception as e:
                        print(f"[TMDb TV Show Error] {name} ({tv_id}): {e}")

                category_items.extend(page_items)
                print(f"[INFO] TV {category} Page {page}: {len(page_items)} items")
            except Exception as e:
                print(f"[TMDb TV {category} Page {page} Error] {e}")

        all_series.extend(category_items)
        print(f"[INFO] TV {category} Total: {len(category_items)} items")

    return all_series

def fetch_tvmaze():
    print("[INFO] Fetching MAXIMUM TVMaze shows...")
    
    # Fetch multiple pages for maximum data
    PAGES_TO_FETCH = 20  # Fetch 20 pages = 500+ shows
    all_shows = []
    
    for page in range(1, PAGES_TO_FETCH + 1):
        try:
            url = f"https://api.tvmaze.com/shows?page={page}"
            print(f"[INFO] Fetching TVMaze page {page}...")
            
            # Retry logic for each page
            for attempt in range(3):
                try:
                    res = requests.get(url, timeout=60)  # Increased timeout
                    if res.status_code == 200:
                        break
                    else:
                        print(f"[TVMaze Page {page} Retry {attempt+1}] Status Code: {res.status_code}")
                        if attempt < 2:
                            time.sleep(5)
                except Exception as e:
                    print(f"[TVMaze Page {page} Retry {attempt+1}] {e}")
                    if attempt < 2:
                        time.sleep(5)
            else:
                print(f"[TVMaze Error] Failed to fetch page {page} after retries")
                continue

        shows = []
        for show in res.json():
            premiered = show.get("premiered")
            year = premiered[:4] if premiered else "N/A"
            shows.append({
                "id": show.get("id"),
                "title": show.get("name"),
                "year": year,
                "overview": show.get("summary", "").replace("<p>", "").replace("</p>", "") if show.get("summary") else "",
                "poster": show.get("image", {}).get("medium") if show.get("image") else "",
                "rating": show.get("rating", {}).get("average") if show.get("rating") else None,
                "genres": show.get("genres", []),
                "source": "TVMaze"
            })
            
            all_shows.extend(shows)
            print(f"[INFO] TVMaze Page {page}: {len(shows)} shows fetched")
            
    except Exception as e:
            print(f"[TVMaze Page {page} Error] {e}")
    
    print(f"[INFO] TVMaze Total: {len(all_shows)} shows fetched")
    return all_shows


def fetch_wikidata(limit=50):
    print(f"[INFO] Fetching MAXIMUM Wikidata movies (limit: {limit})...")
    try:
        # Optimized query with increased limit
        query = f"""
        SELECT ?movie ?movieLabel ?poster WHERE {{
          ?movie wdt:P31 wd:Q11424.
          OPTIONAL {{ ?movie wdt:P18 ?poster. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT {limit}
        """
        url = "https://query.wikidata.org/sparql"
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "MovieMetadataUpdater/1.0"
        }

        # Enhanced retry logic with exponential backoff
        for attempt in range(5):  # Increased retries
            try:
                print(f"[Wikidata] Attempt {attempt+1}/5...")
                res = requests.get(
                    url, 
                    params={"query": query}, 
                    headers=headers, 
                    timeout=120  # Increased timeout to 2 minutes
                )
                res.raise_for_status()
                
                data = res.json()
        movies = []
                for item in data.get("results", {}).get("bindings", []):
            movies.append({
                "title": item.get("movieLabel", {}).get("value") or "N/A",
                "poster": item.get("poster", {}).get("value") or "",
                "source": "Wikidata"
            })
                
                print(f"[Wikidata] Successfully fetched {len(movies)} movies")
        return movies
                
            except requests.exceptions.Timeout:
                print(f"[Wikidata Timeout] Attempt {attempt+1} - Request timed out after 120s")
                if attempt < 4:
                    wait_time = (attempt + 1) * 10  # Exponential backoff: 10s, 20s, 30s, 40s
                    print(f"[Wikidata] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    
            except requests.exceptions.ConnectionError:
                print(f"[Wikidata Connection Error] Attempt {attempt+1} - Network issue")
                if attempt < 4:
                    wait_time = (attempt + 1) * 8
                    print(f"[Wikidata] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                    
            except Exception as e:
                print(f"[Wikidata Error] Attempt {attempt+1}: {e}")
                if attempt < 4:
                    wait_time = (attempt + 1) * 5
                    print(f"[Wikidata] Waiting {wait_time}s before retry...")
                    time.sleep(wait_time)

        print("[Wikidata Error] Failed to fetch after all retries")
        return []

    except Exception as e:
        print(f"[Wikidata Fetch Error] {e}")
        return []


def main():
    print("=" * 60)
    print("🎬 MOVIE METADATA AUTO-UPDATER")
    print("=" * 60)
    print(f"[INFO] Starting movie metadata update at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()

    # Track progress
    total_fetched = 0
    
    print("📡 Fetching from TMDb (movies)...")
    tmdb_movies = fetch_tmdb()
    print(f"✅ TMDb Movies: {len(tmdb_movies)} fetched")
    total_fetched += len(tmdb_movies)
    print()

    print("📡 Fetching from TMDb (TV series)...")
    tmdb_tv = fetch_tmdb_tv()
    print(f"✅ TMDb TV: {len(tmdb_tv)} fetched")
    total_fetched += len(tmdb_tv)
    print()

    print("📺 Fetching from TVMaze...")
    tvmaze_shows = fetch_tvmaze()
    print(f"✅ TVMaze: {len(tvmaze_shows)} shows fetched")
    total_fetched += len(tvmaze_shows)
    print()

    print("🌐 Fetching from Wikidata...")
    wikidata_movies = fetch_wikidata(limit=50)  # Increased limit for maximum data
    print(f"✅ Wikidata: {len(wikidata_movies)} movies fetched")
    total_fetched += len(wikidata_movies)
    print()

    print("🔄 Combining all data...")
    combined = tmdb_movies + tmdb_tv + tvmaze_shows + wikidata_movies

    # Calculate category breakdown for TMDb movies
    tmdb_categories = {}
    for item in tmdb_movies:
        category = item.get("category", "unknown")
        tmdb_categories[category] = tmdb_categories.get(category, 0) + 1
    tmdb_tv_categories = {}
    for item in tmdb_tv:
        category = item.get("category", "unknown")
        tmdb_tv_categories[category] = tmdb_tv_categories.get(category, 0) + 1

    print("💾 Saving to movies.json...")
    output = {
        "developer": {
            "name": "Abdul Mueed",
            "contact": "am-abdulmueed3@gmail.com",
            "website": "https://github.com/betapix"
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "total_entries": len(combined),
        "breakdown": {
            "tmdb_movies": len(tmdb_movies),
            "tmdb_tv": len(tmdb_tv),
            "tvmaze_shows": len(tvmaze_shows),
            "wikidata_movies": len(wikidata_movies)
        },
        "tmdb_categories": tmdb_categories,
        "tmdb_tv_categories": tmdb_tv_categories,
        "movies": combined
    }

    try:
    with open("movies.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

        # Also write compressed JSON for faster downloads
        with gzip.open("movies.json.gz", "wt", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False)
        
        print("=" * 60)
        print("🎉 SUCCESS!")
        print(f"📊 Total entries: {len(combined)}")
        print(f"   • TMDb movies: {len(tmdb_movies)}")
        print(f"   • TVMaze shows: {len(tvmaze_shows)}")
        print(f"   • Wikidata movies: {len(wikidata_movies)}")
        print()
        print("🎬 TMDb Categories:")
        for category, count in tmdb_categories.items():
            print(f"   • {category.title()}: {count} movies")
        print(f"⏰ Updated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("📦 Compressed output: movies.json.gz")
        print("=" * 60)
        
    except Exception as e:
        print(f"❌ Error saving movies.json: {e}")
        print("=" * 60)


if __name__ == "__main__":
    main()
