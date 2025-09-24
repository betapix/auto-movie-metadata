"""
Movie Metadata Auto-Updater
----------------------------

Developer: Abdul Mueed
Email: am-abdulmueed3@gmail.com
GitHub: https://github.com/betapix

Description:
This script automatically fetches movie and TV show metadata from
TMDb, TVMaze, and Wikidata, combines the data, and generates
a movies.json file. This file is hosted via GitHub Pages to
allow developers to access real-time movie metadata without
a backend or API key.

License:
MIT License — Free to use, modify, and distribute with attribution.

Purpose:
To create a fully automated, developer-friendly movie metadata
service for use in Flutter, web, and mobile applications.
"""

import os
import requests
import json
from datetime import datetime

# 🔑 Securely get TMDb API Key from GitHub Secrets
TMDB_API_KEY = os.getenv("TMDB_API_KEY")

def fetch_tmdb():
    """Fetch trending movies from TMDb with full metadata."""
    try:
        url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}"
        res = requests.get(url).json()
        movies = []
        for movie in res.get("results", []):
            release_date = movie.get("release_date")
            year = release_date[:4] if release_date else "N/A"

            # Fetch extra details (budget, crew, trailers, etc.)
            details_url = f"https://api.themoviedb.org/3/movie/{movie['id']}?api_key={TMDB_API_KEY}&append_to_response=credits,videos"
            details = requests.get(details_url).json()

            directors = [c["name"] for c in details.get("credits", {}).get("crew", []) if c.get("job") == "Director"]
            writers = [c["name"] for c in details.get("credits", {}).get("crew", []) if c.get("department") == "Writing"]
            cast = [
                {"name": c["name"], "character": c["character"], 
                 "profile": f"https://image.tmdb.org/t/p/w300{c['profile_path']}" if c.get("profile_path") else ""}
                for c in details.get("credits", {}).get("cast", [])[:5]
            ]

            trailers = [
                f"https://www.youtube.com/watch?v={v['key']}" 
                for v in details.get("videos", {}).get("results", []) if v.get("site") == "YouTube"
            ]

            movies.append({
                "id": movie.get("id"),
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
                "cast": cast,
                "trailers": trailers,
                "source": "TMDb"
            })
        return movies
    except Exception as e:
        print(f"[TMDb Fetch Error] {e}")
        return []

def fetch_tvmaze():
    """Fetch TV shows from TVMaze."""
    try:
        url = "https://api.tvmaze.com/shows?page=1"
        res = requests.get(url).json()
        shows = []
        for show in res:
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

def fetch_wikidata():
    """Fetch some movie data from Wikidata."""
    try:
        query = """
        SELECT ?movie ?movieLabel ?poster WHERE {
          ?movie wdt:P31 wd:Q11424.
          OPTIONAL { ?movie wdt:P18 ?poster. }
          SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
        } LIMIT 10
        """
        url = "https://query.wikidata.org/sparql"
        headers = {"Accept": "application/sparql+json"}
        res = requests.get(url, params={"query": query}, headers=headers).json()
        movies = []
        for item in res["results"]["bindings"]:
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
    """Main function to fetch data and generate movies.json."""
    print("[INFO] Starting movie metadata update...")
    tmdb_movies = fetch_tmdb()
    tvmaze_shows = fetch_tvmaze()
    wikidata_movies = fetch_wikidata()

    combined = tmdb_movies + tvmaze_shows + wikidata_movies

    output = {
        "developer": {
            "name": "Abdul Mueed",
            "contact": "am-abdulmueed3@gmail.com",
            "website": "https://github.com/betapix"
        },
        "last_updated": datetime.utcnow().isoformat(),
        "movies": combined
    }

    with open("movies.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"[INFO] movies.json updated with {len(combined)} entries.")

if __name__ == "__main__":
    main()
