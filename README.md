# Nuvio Curated Collections

A from-scratch collections setup for a new Nuvio account: 13 Home rows, 247 folders, 940 rails, and a
matching cover for every folder. Every rail is a native Nuvio **TMDB source** (Discover, Network, Company,
Collection, Director), so it needs no catalog addon, keeps itself current, and opens titles through
Nuvio's own TMDB-to-IMDb lookup, which your stream addons understand.

Built against Nuvio desktop 0.1.30 (`CollectionModels.kt`, `TmdbCollectionSourceResolver.kt`). The JSON
passes the same checks as Nuvio's `validateImportModel`.

## What's in it

| Row (Home order) | Folders | Opens as | Built from |
|---|---|---|---|
| Streaming Services | 15 | rows | Watch providers, US region, plus each service's originals network |
| Indian Streaming | 12 | rows | Watch providers, India region (small services pinned to Indian titles) |
| Genres | 20 | rows | TMDB genres, movies and series |
| Franchises & Universes | 33 | tabbed grid | TMDB collections and franchise keywords, in release order where TMDB allows |
| Indian Cinema | 10 | rows | Original language (Hindi, Telugu, Tamil, Malayalam, Kannada, Bengali, Marathi, Punjabi) |
| Moods & Themes | 34 | rows | TMDB keywords |
| Directors | 28 | tabbed grid | Director credits, "Essentials" (most voted) and "Newest" |
| Indian Universes | 12 | tabbed grid | Collections and universe keywords (Cop Universe, LCU, MHCU, YRF Spy) |
| Studios | 31 | rows | Production companies |
| World Cinema | 16 | rows | Language / origin country |
| Networks | 22 | rows | TV networks |
| Critics' Picks | 6 | tabbed grid | Vote-based curation (all-time greats, hidden gems, this year's best) |
| Decades | 8 | rows | Release-date ranges, 1950s to 2020s |

Inside a folder, the usual rails are **Popular**, **New**, **Top Rated** for movies and series, plus
**Originals** for services. Each rail has a vote-count floor so unreleased placeholders and filler
(News, Talk and Soap genres) stay out. Rails that TMDB can't fill (fewer than 3 titles) were dropped
automatically; `build/report.txt` lists every rail with its count and first titles.

## Files

- `nuvio-collections.min.json`: the file to import (paste its contents).
- `nuvio-collections.json`: the same, indented, for reading and diffs.
- `covers/<row>/<folder>.webp`: 1600×900 covers, about 80 KB each.
- `build/`: the pipeline that produced all of it.

## Covers

Four templates, one per kind of folder:

- **Brand** (services, studios, networks): a tilted wall of that brand's own posters, darkened, with the
  logo in a fixed-size box so every logo reads at the same optical size.
- **Scene** (genres, moods, world and Indian cinema, decades, critics' picks): a textless still from one
  hand-picked film, graded, with the title set in SF Pro. Indian and world cinema add the name in its own
  script.
- **Franchise**: a still plus the franchise's official title logo.
- **Director**: a black-and-white portrait, the name in New York serif, and their three most-voted films.

No film is used twice across all 247 covers. `build/hero_overrides.json` holds the hand-picked stills,
`build/logo_overrides.json` the franchise logos, `build/tweaks.json` per-tile adjustments.

Covers reference `https://cdn.jsdelivr.net/gh/mali-king/nuvio-collections@v1/covers/...`. They load
once this repo is public on GitHub with a `v1` tag. To host them elsewhere, set `COVER_BASE` and rerun.

## Import into the new account

1. In Nuvio desktop, sign in to the new account (profile 1).
2. Copy the JSON: `pbcopy < ~/Projects/nuvio-collections/nuvio-collections.min.json`
3. Settings → Collections → Import, paste, Import. This replaces that profile's collections.
4. Collections sync to the account, so the phone and TV apps get them on sign-in.

## Rebuild

Needs python3, ImageMagick, `cwebp`, node with Playwright, and a TMDB v3 key in `TMDB_API_KEY` or
`build/.tmdbkey` (gitignored).

```sh
build/run.sh
```

Edit `build/spec.py` to change what's curated; rerunning validates every source against TMDB again.

## Credits

Data and artwork from [TMDB](https://www.themoviedb.org) (this product uses the TMDB API but is not
endorsed or certified by TMDB). Several service and studio logos come from the
[luckynumb3rs stremio-perfect-setup](https://github.com/luckynumb3rs/stremio-perfect-setup) pack.
Brand names and logos belong to their owners; this is a personal setup.
