"""Tiny cached TMDB v3 client used to validate collection sources and fetch artwork."""
import hashlib
import json
import os
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
# Your own TMDB v3 key: env TMDB_API_KEY, or a one-line build/.tmdbkey file (gitignored).
KEY = os.environ.get("TMDB_API_KEY") or open(os.path.join(HERE, ".tmdbkey")).read().strip()
CACHE = os.path.join(HERE, "cache")
os.makedirs(CACHE, exist_ok=True)
BASE = "https://api.themoviedb.org/3/"


def get(endpoint, **params):
    q = {k: v for k, v in params.items() if v is not None and v != ""}
    key = hashlib.sha1((endpoint + json.dumps(q, sort_keys=True)).encode()).hexdigest()
    path = os.path.join(CACHE, key + ".json")
    if os.path.exists(path):
        with open(path) as f:
            return json.load(f)
    url = BASE + endpoint + "?" + urllib.parse.urlencode({**q, "api_key": KEY})
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=30) as r:
                data = json.load(r)
            break
        except urllib.error.HTTPError as e:
            if e.code == 404:
                data = None
                break
            if e.code == 429:
                time.sleep(2 + attempt * 2)
                continue
            raise
        except Exception:
            time.sleep(1 + attempt)
    else:
        raise RuntimeError("TMDB failed: " + endpoint)
    with open(path, "w") as f:
        json.dump(data, f)
    return data


# Mirrors TmdbCollectionSourceResolver.buildDiscoverQuery in Nuvio 0.1.30.
def discover_query(source, page=1):
    f = source.get("filters") or {}
    st = source.get("tmdbSourceType", "DISCOVER")
    media = "tv" if st == "NETWORK" or (source.get("mediaType") in ("tv", "series")) else "movie"
    sort = source.get("sortBy") or "popularity.desc"
    if media == "movie" and sort == "first_air_date.desc":
        sort = "primary_release_date.desc"
    if media == "tv" and sort == "primary_release_date.desc":
        sort = "first_air_date.desc"
    q = {"language": "en-US", "page": page, "sort_by": sort}
    tid = source.get("tmdbId")
    q["with_companies"] = str(tid) if st == "COMPANY" else f.get("withCompanies")
    q["without_companies"] = f.get("withoutCompanies")
    q["with_networks"] = str(tid) if st == "NETWORK" else f.get("withNetworks")
    q["with_genres"] = f.get("withGenres")
    q["without_genres"] = f.get("withoutGenres")
    q["vote_count.gte"] = f.get("voteCountGte")
    q["vote_average.gte"] = f.get("voteAverageGte")
    q["vote_average.lte"] = f.get("voteAverageLte")
    q["with_original_language"] = f.get("withOriginalLanguage")
    q["with_origin_country"] = f.get("withOriginCountry")
    q["with_keywords"] = f.get("withKeywords")
    q["without_keywords"] = f.get("withoutKeywords")
    if f.get("withWatchProviders") or f.get("withoutWatchProviders"):
        q["with_watch_providers"] = f.get("withWatchProviders")
        q["without_watch_providers"] = f.get("withoutWatchProviders")
        q["watch_region"] = f.get("watchRegion") or "US"
        if f.get("withWatchProviders"):
            q["with_watch_monetization_types"] = "flatrate|free|ads|rent|buy"
    if f.get("year"):
        q["year" if media == "movie" else "first_air_date_year"] = f["year"]
    gte = "primary_release_date.gte" if media == "movie" else "first_air_date.gte"
    lte = "primary_release_date.lte" if media == "movie" else "first_air_date.lte"
    q[gte] = f.get("releaseDateGte")
    q[lte] = f.get("releaseDateLte")
    return "discover/" + media, q


def resolve(source, page=1):
    """Return (total_results, first-page items) the way Nuvio would load them."""
    st = source.get("tmdbSourceType", "DISCOVER")
    if st in ("DISCOVER", "COMPANY", "NETWORK"):
        ep, q = discover_query(source, page)
        d = get(ep, **q) or {}
        return d.get("total_results", 0), d.get("results", [])
    if st == "COLLECTION":
        d = get(f"collection/{source['tmdbId']}", language="en-US") or {}
        parts = d.get("parts", [])
        return len(parts), parts
    if st in ("PERSON", "DIRECTOR"):
        d = get(f"person/{source['tmdbId']}/combined_credits", language="en-US") or {}
        media = "tv" if source.get("mediaType") in ("tv", "series") else "movie"
        rows = d.get("crew", []) if st == "DIRECTOR" else d.get("cast", [])
        if st == "DIRECTOR":
            rows = [r for r in rows if (r.get("job") or "").lower() == "director"]
        rows = [r for r in rows if r.get("media_type") == media]
        seen, out = set(), []
        for r in rows:
            if r["id"] not in seen:
                seen.add(r["id"])
                out.append(r)
        return len(out), out
    if st == "LIST":
        d = get(f"list/{source['tmdbId']}", language="en-US", page=page) or {}
        return d.get("total_results", len(d.get("items", []))), d.get("items", [])
    raise ValueError(st)


def img(path, size="original"):
    return f"https://image.tmdb.org/t/p/{size}{path}" if path else None
