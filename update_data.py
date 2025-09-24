import requests
import json
from datetime import datetime

TMDB_API_KEY = "YOUR_TMDB_API_KEY"  # Free key le sakta hai TMDb se

def fetch_tmdb():
    url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={TMDB_API_KEY}"
    res = requests.get(url).json()
    movies = []
    for movie in res.get("results", []):
        movies.append({
            "id": movie.get("id"),
            "title": movie.get("title"),
            "year": movie.get("release_date", "")[:4],
            "overview": movie.get("overview"),
            "poster": "https://image.tmdb.org/t/p/w500" + (movie.get("poster_path") or ""),
            "rating": movie.get("vote_average"),
            "genres": movie.get("genre_ids", [])
        })
    return movies

def fetch_tvmaze():
    url = "https://api.tvmaze.com/shows?page=1"
    res = requests.get(url).json()
    shows = []
    for show in res:
        shows.append({
            "id": show.get("id"),
            "title": show.get("name"),
            "year": show.get("premiered", "")[:4],
            "overview": show.get("summary", "").replace("<p>", "").replace("</p>", ""),
            "poster": show.get("image", {}).get("medium"),
            "rating": show.get("rating", {}).get("average"),
            "genres": show.get("genres", [])
        })
    return shows

def fetch_wikidata():
    # Example: Fetch some sample movie data from Wikidata
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
            "title": item.get("movieLabel", {}).get("value"),
            "poster": item.get("poster", {}).get("value"),
            "source": "Wikidata"
        })
    return movies

def main():
    tmdb_movies = fetch_tmdb()
    tvmaze_shows = fetch_tvmaze()
    wikidata_movies = fetch_wikidata()

    combined = tmdb_movies + tvmaze_shows + wikidata_movies

    with open("movies.json", "w", encoding="utf-8") as f:
        json.dump({
            "last_updated": datetime.utcnow().isoformat(),
            "movies": combined
        }, f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    main()
