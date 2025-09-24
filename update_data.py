"""
Movie Metadata Auto-Updater
----------------------------

Developer: Abdul Mueed
Email: am-abdulmueed3@gmail.com
GitHub: https://github.com/betapix

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

# Get TMDb API keys from environment
TMDB_API_KEY = os.environ.get("TMDB_API_KEY")
TMDB_ACCESS_TOKEN = os.environ.get("TMDB_ACCESS_TOKEN")

if not TMDB_API_KEY or not TMDB_ACCESS_TOKEN:
    print("[ERROR] TMDB_API_KEY or TMDB_ACCESS_TOKEN not set in environment variables.")
    exit(1)


def fetch_tmdb():
    print("[INFO] Fetching TMDb trending movies...")
    try:
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}"
        res = requests.get(url, timeout=30)

        if res.status_code != 200:
            print(f"[TMDb Error] Status Code: {res.status_code}")
            return []

        movies = []
        for movie in res.json().get("results", []):
            release_date = movie.get("release_date")
            year = release_date[:4] if release_date else "N/A"
            movie_id = movie.get("id")

            try:
                # Movie details
                details = requests.get(
                    f"https://api.themoviedb.org/3/movie/{movie_id}",
                    headers={"Authorization": f"Bearer {TMDB_ACCESS_TOKEN}"},
                    timeout=30
                ).json()

                # Credits
                credits = requests.get(
                    f"https://api.themoviedb.org/3/movie/{movie_id}/credits",
                    headers={"Authorization": f"Bearer {TMDB_ACCESS_TOKEN}"},
                    timeout=30
                ).json()

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

                # Trailers
                videos = requests.get(
                    f"https://api.themoviedb.org/3/movie/{movie_id}/videos",
                    headers={"Authorization": f"Bearer {TMDB_ACCESS_TOKEN}"},
                    timeout=30
                ).json()

                trailers = [
                    f"https://www.youtube.com/watch?v={v.get('key')}"
                    for v in videos.get("results", [])
                    if v.get("site") == "YouTube"
                ]

                movies.append({
                    "id": movie_id,
                    "title": movie.get("title"),
                    "year": year,
                    "overview": movie.get("overview") or "",
                    "poster": f"https://image.tmdb.org/t/p/w500{movie.get('poster_path')}" if movie.get("poster_path") else "",
                    "rating": movie.get("vote_average") or None,
                    "genres": movie.get("genre_ids", []),
                    "budget": details.get("budget"),
                    "revenue": details.get("revenue"),
                    "directors": directors,
                    "writers": writers,
                    "cast": cast_list,
                    "trailers": trailers,
                    "source": "TMDb"
                })

            except Exception as e:
                print(f"[TMDb Movie Error] {movie.get('title')} ({movie_id}): {e}")

        return movies

    except Exception as e:
        print(f"[TMDb Fetch Error] {e}")
        return []


def fetch_tvmaze():
    print("[INFO] Fetching TVMaze shows...")
    try:
        url = "https://api.tvmaze.com/shows?page=1"
        res = requests.get(url, timeout=30)

        if res.status_code != 200:
            print(f"[TVMaze Error] Status Code: {res.status_code}")
            return []

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
        return shows
    except Exception as e:
        print(f"[TVMaze Fetch Error] {e}")
        return []


def fetch_wikidata(limit=10):
    print("[INFO] Fetching Wikidata movies...")
    try:
        query = f"""
        SELECT ?movie ?movieLabel ?poster WHERE {{
          ?movie wdt:P31 wd:Q11424.
          OPTIONAL {{ ?movie wdt:P18 ?poster. }}
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "en". }}
        }} LIMIT {limit}
        """
        url = "https://query.wikidata.org/sparql"
        headers = {"Accept": "application/sparql-results+json"}

        for attempt in range(3):  # retry mechanism
            try:
                res = requests.get(url, params={"query": query}, headers=headers, timeout=60)
                res.raise_for_status()
                break
            except Exception as e:
                print(f"[Wikidata Retry {attempt+1}] {e}")
                time.sleep(5)
        else:
            return []

        movies = []
        for item in res.json().get("results", {}).get("bindings", []):
            movies.append({
                "title": item.get("movieLabel", {}).get("value") or "N/A",
                "poster": item.get("poster", {}).get("value") or "",
                "source": "Wikidata"
            })
        return movies

    except Exception as e:
        print(f"[Wikidata Fetch Error] {e}")
        return []


def main():
    print("[INFO] Starting movie metadata update...")

    tmdb_movies = fetch_tmdb()
    tvmaze_shows = fetch_tvmaze()
    wikidata_movies = fetch_wikidata(limit=20)

    combined = tmdb_movies + tvmaze_shows + wikidata_movies

    output = {
        "developer": {
            "name": "Abdul Mueed",
            "contact": "am-abdulmueed3@gmail.com",
            "website": "https://github.com/betapix"
        },
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "movies": combined
    }

    with open("movies.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[INFO] movies.json updated with {len(combined)} entries.")


if __name__ == "__main__":
    main()
