"""Assemble the Nuvio collections JSON from spec.py and validate every source against TMDB."""
import json
import os
import re
import sys
import uuid
from concurrent.futures import ThreadPoolExecutor

import spec
import tmdb
from spec import (FLOORS, NOISE_TV, collection, company, director, discover, network, service_tabs,
                  standard_tabs)

HERE = os.path.dirname(os.path.abspath(__file__))
NS = uuid.UUID("6f1d3c2a-9b7e-4c55-8a10-5e0c7d1b2a99")
CDN = os.environ.get("COVER_BASE", "https://raw.githubusercontent.com/mali-king/nuvio-collections/v2")


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower().replace("+", "-plus").replace("&", "and")).strip("-")


def uid(*parts):
    return str(uuid.uuid5(NS, "/".join(parts)))


COLLECTIONS = []


def add_collection(title, folders, view="ROWS", show_all=True, pin=True):
    cslug = slug(title)
    out = []
    for f in folders:
        fslug = slug(f["title"])
        out.append({
            "id": uid(cslug, fslug),
            "title": f["title"],
            "coverImageUrl": f"{CDN}/covers/{cslug}/{fslug}.webp",
            "focusGifUrl": None,
            "focusGifEnabled": False,
            "coverEmoji": None,
            "tileShape": "LANDSCAPE",
            "hideTitle": True,
            "sources": f["sources"],
            "heroBackdropUrl": None,
            "heroVideoUrl": None,
            "titleLogoUrl": None,
            "_art": {**f.get("art", {}), "collection": cslug, "slug": fslug, "title": f["title"]},
        })
    COLLECTIONS.append({
        "id": uid(cslug),
        "title": title,
        "backdropImageUrl": None,
        "pinToTop": pin,
        "focusGlowEnabled": True,
        "viewMode": view,
        "showAllTab": show_all,
        "folders": out,
    })


# 1. Streaming services --------------------------------------------------------------
small = {"MGM+", "AMC+", "Shudder", "MUBI", "Criterion Channel", "Starz", "Crunchyroll"}
movie_only = {"MUBI", "Criterion Channel"}
folders = []
for title, prov, region, orig, logo in spec.SERVICES:
    folders.append({
        "title": title,
        "sources": service_tabs(prov, region, "mid" if title in small else "global", originals=orig,
                                originals_label=f"{title} Originals", series=title not in movie_only),
        "art": {"kind": "brand", "logo": logo},
    })
add_collection("Streaming Services", folders)

# 2. Indian streaming ------------------------------------------------------------------
folders = []
for title, prov, orig, logo, floor in spec.INDIA_SERVICES:
    # Small regional services: TMDB's provider data carries foreign noise, so pin them to Indian titles.
    origin = None if title in ("JioHotstar", "SonyLIV", "ZEE5", "Amazon MX Player", "Lionsgate Play") else "IN"
    label = title.replace(" India", "")
    folders.append({
        "title": title,
        "sources": service_tabs(prov, "IN", floor, originals=orig, originals_label=f"{label} Originals",
                                origin=origin),
        "art": {"kind": "brand", "logo": logo, "badge": "India" if title.endswith(" India") else None},
    })
add_collection("Indian Streaming", folders)

# 3. Genres --------------------------------------------------------------------------
folders = []
for title, mg, tg in spec.GENRES:
    f = {}
    if mg:
        f["m_withGenres"] = mg.replace("10751|16", "10751,16")
    if tg:
        f["tv_withGenres"] = tg
    folders.append({
        "title": title,
        "sources": standard_tabs("global", movies=bool(mg), series=bool(tg), **f),
        "art": {"kind": "scene"},
    })
add_collection("Genres", folders)

# 4. Indian cinema -------------------------------------------------------------------
folders = []
for title, lang in spec.INDIAN_CINEMA:
    floor = "india" if lang in ("hi", "te", "ta", "ml") else "india_small"
    fl = FLOORS[floor]
    srcs = standard_tabs(floor, label_t="Series", withOriginalLanguage=lang, tv_withoutGenres=NOISE_TV + "|10764")
    srcs.append(discover("Classics", "movie", "vote_count.desc", withOriginalLanguage=lang,
                         releaseDateLte="1999-12-31", voteCountGte=max(5, fl["pop_m"] // 2)))
    folders.append({"title": title, "sources": srcs, "art": {"kind": "scene"}})
folders.append({
    "title": "Indian Web Series",
    "sources": [
        discover("Popular", "tv", None, withOriginCountry="IN", voteCountGte=20, releaseDateGte="2015-01-01"),
        discover("New", "tv", "first_air_date.desc", withOriginCountry="IN", voteCountGte=5),
        discover("Top Rated", "tv", "vote_average.desc", withOriginCountry="IN", voteCountGte=60),
    ],
    "art": {"kind": "scene"},
})
folders.append({
    "title": "Pan-India Blockbusters",
    "sources": [
        discover("Biggest Hits", "movie", "vote_count.desc", withOriginCountry="IN", releaseDateGte="2015-01-01"),
        discover("Top Rated", "movie", "vote_average.desc", withOriginCountry="IN", voteCountGte=300),
        discover("All-Time", "movie", "vote_count.desc", withOriginCountry="IN"),
    ],
    "art": {"kind": "scene"},
})
add_collection("Indian Cinema", folders)

# 5. World cinema --------------------------------------------------------------------
folders = []
for title, fm, ft, floor, tv_label in spec.WORLD:
    f = {**{"m_" + k: v for k, v in fm.items()}, **{"tv_" + k: v for k, v in ft.items()}}
    folders.append({
        "title": title,
        "sources": standard_tabs(floor, label_t=tv_label if tv_label != "Series" else "Series", **f),
        "art": {"kind": "scene"},
    })
add_collection("World Cinema", folders)

# 6. Franchises ----------------------------------------------------------------------
add_collection("Franchises & Universes",
               [{"title": t, "sources": s, "art": {"kind": "franchise"}} for t, s in spec.FRANCHISES],
               view="TABBED_GRID")
add_collection("Indian Universes",
               [{"title": t, "sources": s, "art": {"kind": "franchise"}} for t, s in spec.INDIAN_FRANCHISES],
               view="TABBED_GRID")

# 7. Studios -------------------------------------------------------------------------
folders = []
for title, ids, media in spec.STUDIOS:
    fl = FLOORS["mid"]
    if len(ids) == 1:
        mk = lambda t, sort, **f: company(t, ids[0], media, sort, **f)
    else:
        mk = lambda t, sort, **f: discover(t, media, sort, withCompanies="|".join(map(str, ids)), **f)
    new_sort = "first_air_date.desc" if media == "tv" else "primary_release_date.desc"
    folders.append({
        "title": title,
        "sources": [
            mk("Popular", None, voteCountGte=fl["pop_m"]),
            mk("Latest", new_sort, voteCountGte=fl["new_m"]),
            mk("Essentials", "vote_count.desc"),
            mk("Top Rated", "vote_average.desc", voteCountGte=fl["top_m"] // 2),
        ],
        "art": {"kind": "brand", "logo": "company:" + str(ids[0])},
    })
add_collection("Studios", folders)

# 8. Networks ------------------------------------------------------------------------
folders = []
for title, ids in spec.NETWORKS:
    if len(ids) == 1:
        mk = lambda t, sort, **f: network(t, ids[0], sort, **f)
    else:
        mk = lambda t, sort, **f: discover(t, "tv", sort, withNetworks="|".join(map(str, ids)), **f)
    folders.append({
        "title": title,
        "sources": [
            mk("Popular", None, voteCountGte=20),
            mk("Latest", "first_air_date.desc", voteCountGte=5),
            mk("Essentials", "vote_count.desc"),
            mk("Top Rated", "vote_average.desc", voteCountGte=150),
        ],
        "art": {"kind": "brand", "logo": "network:" + str(ids[0])},
    })
add_collection("Networks", folders)

# 9. Directors -----------------------------------------------------------------------
add_collection("Directors", [{
    "title": name,
    "sources": [director("Essentials", pid, sort="vote_count.desc"),
                director("Newest", pid, sort="primary_release_date.desc")],
    "art": {"kind": "director", "person": pid},
} for name, pid in spec.DIRECTORS], view="TABBED_GRID", show_all=False)

# 10. Moods & themes -----------------------------------------------------------------
folders = []
for title, kw, _ in spec.THEMES:
    folders.append({
        "title": title,
        "sources": [
            discover("Popular Movies", "movie", None, withKeywords=kw, voteCountGte=100),
            discover("Popular Series", "tv", None, withKeywords=kw, voteCountGte=30),
            discover("Top Rated", "movie", "vote_average.desc", withKeywords=kw, voteCountGte=500),
            discover("Hidden Gems", "movie", "vote_count.asc", withKeywords=kw, voteCountGte=80,
                     voteAverageGte=7.0),
        ],
        "art": {"kind": "scene"},
    })
add_collection("Moods & Themes", folders)

# 11. Decades ------------------------------------------------------------------------
folders = []
for d in spec.DECADES:
    y = int(d[:4])
    rng = dict(releaseDateGte=f"{y}-01-01", releaseDateLte=f"{y + 9}-12-31")
    folders.append({
        "title": d,
        "sources": [
            discover("Essentials", "movie", "vote_count.desc", **rng),
            discover("Top Rated", "movie", "vote_average.desc", voteCountGte=800 if y >= 1970 else 300, **rng),
            discover("Series", "tv", "vote_count.desc", **rng),
            discover("Popular Now", "movie", None, voteCountGte=200, **rng),
        ],
        "art": {"kind": "scene", "decade": y},
    })
add_collection("Decades", folders)

# 12. Critics' picks -----------------------------------------------------------------
NO_DOC = "99|10402|10770"
add_collection("Critics' Picks", [
    {"title": "All-Time Greats", "art": {"kind": "scene"}, "sources": [
        discover("Films", "movie", "vote_average.desc", voteCountGte=12000, withoutGenres=NO_DOC),
        discover("Series", "tv", "vote_average.desc", voteCountGte=4000)]},
    {"title": "Modern Classics", "art": {"kind": "scene"}, "sources": [
        discover("Films", "movie", "vote_average.desc", voteCountGte=4000, releaseDateGte="2010-01-01", withoutGenres=NO_DOC),
        discover("Series", "tv", "vote_average.desc", voteCountGte=1500, releaseDateGte="2010-01-01")]},
    {"title": "Hidden Gems", "art": {"kind": "scene"}, "sources": [
        discover("Films", "movie", "vote_count.asc", voteCountGte=400, voteAverageGte=7.7, withoutGenres=NO_DOC + "|16"),
        discover("Series", "tv", "vote_count.asc", voteCountGte=150, voteAverageGte=8.2, withoutGenres=NOISE_TV + "|16|10764")]},
    {"title": "Best of This Year", "art": {"kind": "scene"}, "sources": [
        discover("Films", "movie", "vote_average.desc", voteCountGte=250, releaseDateGte="2026-01-01"),
        discover("Series", "tv", "vote_average.desc", voteCountGte=80, releaseDateGte="2026-01-01")]},
    {"title": "Documentaries", "art": {"kind": "scene"}, "sources": [
        discover("Essential", "movie", "vote_average.desc", withGenres="99", voteCountGte=400),
        discover("Docuseries", "tv", "vote_average.desc", withGenres="99", voteCountGte=150)]},
    {"title": "Animated Masterpieces", "art": {"kind": "scene"}, "sources": [
        discover("Films", "movie", "vote_average.desc", withGenres="16", voteCountGte=2000),
        discover("Series", "tv", "vote_average.desc", withGenres="16", voteCountGte=800)]},
], view="TABBED_GRID")


# ---- validation ---------------------------------------------------------------------
def check(args):
    cidx, fidx, sidx, src = args
    try:
        n, items = tmdb.resolve(src)
        names = [(i.get("title") or i.get("name") or "?") for i in items[:5]]
        return (cidx, fidx, sidx, n, names, None)
    except Exception as e:  # noqa: BLE001
        return (cidx, fidx, sidx, 0, [], str(e))


def validate():
    jobs = []
    for ci, c in enumerate(COLLECTIONS):
        for fi, f in enumerate(c["folders"]):
            for si, s in enumerate(f["sources"]):
                jobs.append((ci, fi, si, s))
    with ThreadPoolExecutor(12) as ex:
        res = list(ex.map(check, jobs))
    report, problems = [], []
    for ci, fi, si, n, names, err in res:
        c = COLLECTIONS[ci]
        f = c["folders"][fi]
        s = f["sources"][si]
        line = f"{c['title']} / {f['title']} / {s['title']}: {n} | {' · '.join(names)}"
        report.append(line)
        min_n = 3 if s["tmdbSourceType"] in ("COLLECTION", "DIRECTOR") else 12
        if err or n < min_n:
            problems.append(line + (f" ERR {err}" if err else ""))
        f.setdefault("_counts", {})[s["title"]] = n
    return report, problems


def prune():
    dropped = []
    for c in COLLECTIONS:
        keep_f = []
        for f in c["folders"]:
            keep = []
            for s in f["sources"]:
                n = f["_counts"].get(s["title"], 0)
                need = 1 if s["tmdbSourceType"] in ("COLLECTION", "DIRECTOR") else 3
                (keep if n >= need else dropped).append(s if n >= need else f"{c['title']} / {f['title']} / {s['title']} ({n})")
            f["sources"] = keep
            if keep:
                keep_f.append(f)
            else:
                dropped.append(f"FOLDER {c['title']} / {f['title']}")
        c["folders"] = keep_f
    return dropped


if __name__ == "__main__":
    report, problems = validate()
    dropped = prune()
    print("DROPPED", len(dropped))
    print("\n".join(dropped))
    open(os.path.join(HERE, "report.txt"), "w").write("\n".join(report))
    print("collections", len(COLLECTIONS), "folders", sum(len(c["folders"]) for c in COLLECTIONS),
          "sources", sum(len(f["sources"]) for c in COLLECTIONS for f in c["folders"]))
    print("PROBLEMS", len(problems))
    print("\n".join(problems))
    json.dump(COLLECTIONS, open(os.path.join(HERE, "collections.full.json"), "w"), indent=1, ensure_ascii=False)
