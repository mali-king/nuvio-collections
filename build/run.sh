#!/bin/sh
# Rebuild everything: validate sources against TMDB, fetch logos and artwork, render covers, export JSON.
# Needs: python3, ImageMagick (magick), cwebp, node + Playwright, and a TMDB key (TMDB_API_KEY or build/.tmdbkey).
set -e
cd "$(dirname "$0")"
[ -x .venv/bin/python ] || { python3 -m venv .venv && .venv/bin/pip install -q pillow numpy; }
python3 build.py
.venv/bin/python logos.py
python3 assets.py
python3 covers.py
python3 export.py
