"""Resolve and download one logo per brand (service, studio, network)."""
import json
import os
import subprocess
import urllib.parse
import urllib.request

import tmdb

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets", "logos")
os.makedirs(os.path.join(OUT, "_probe"), exist_ok=True)
N3 = os.path.join(HERE, "assets", "n3")
N3_RAW = "https://raw.githubusercontent.com/luckynumb3rs/stremio-perfect-setup/main/collections/"


def n3_file(name):
    """A logo from the luckynumb3rs pack, e.g. 'streaming__cover__netflix.webp' (downloaded on first use)."""
    os.makedirs(N3, exist_ok=True)
    dest = os.path.join(N3, name)
    if not os.path.exists(dest):
        subprocess.run(["curl", "-sfL", "-o", dest, N3_RAW + name.replace("__", "/")], check=True)
    return dest

# key -> source. n3 = luckynumb3rs transparent logo pack; network/company = TMDB; provider = app icon;
# wiki = Wikimedia Commons file.
SERVICE_LOGOS = {
    "netflix": ("n3", "streaming__title__netflix.webp"),
    "prime-video": ("n3", "streaming__title__prime-video.webp"),
    "disney-plus": ("n3", "streaming__title__disney-plus.webp"),
    "hbo-max": ("n3", "streaming__title__hbo-max.webp"),
    "apple-tv": ("n3", "streaming__title__apple-tv.webp"),
    "hulu": ("n3", "streaming__title__hulu.webp"),
    "paramount-plus": ("n3", "streaming__title__paramount-plus.webp"),
    "peacock": ("n3", "streaming__title__peacock.webp"),
    "crunchyroll": ("n3", "streaming__title__crunchyroll.webp"),
    "starz": ("n3", "streaming__title__starz.webp"),
    "shudder": ("n3", "streaming__title__shudder.webp"),
    "jiohotstar": ("n3", "streaming__title__jiohotstar.webp"),
    "mgm-plus": ("network", 6219),
    "amc-plus": ("provider", 526),
    "mubi": ("company", 204957),
    "criterion": ("company", 10932),
    "sonyliv": ("network", 2646),
    "zee5": ("wiki", "File:ZEE5 2025.svg"),
    "mx-player": ("provider", 1898),
    "aha": ("network", 3758),
    "sun-nxt": ("provider", 309),
    "hoichoi": ("network", 2139),
    "manorama-max": ("network", 9538),
    "lionsgate-play": ("provider", 561),
    "shemaroo-me": ("provider", 474),
}


# Per-brand fixes after reviewing sheets/logos2.png. Value: (source, forced mode or None).
OVERRIDES = {
    "company:420": (("n3c", "studios__cover__marvel.webp"), "color"),
    "company:9993": (("n3c", "studios__cover__dc.webp"), "color"),
    "company:521": (("n3c", "studios__title__dreamworks.webp"), "color"),
    "company:3": (("n3c", "studios__title__pixar.webp"), "color"),
    "network:56": (("n3c", "studios__title__cartoon-network.webp"), "color"),
    "network:13": (("n3c", "studios__cover__nickelodeon.webp"), "color"),
    "company:33": (None, "white"),
    "company:4": (None, "white"),
    "network:2": (None, "invert"),
    "manorama-max": (None, "color"),
    "sonyliv": (("provider", 237), None),
    "criterion": (("provider", 258), None),
    "company:111627": (("text", "Hombale Films"), None),
}


def fetch(url, dest):
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        subprocess.run(["curl", "-sfL", "-m", "60", "-A", "nuvio-collections-builder/1.0", "-o", dest, url], check=False)
    return dest if os.path.exists(dest) and os.path.getsize(dest) > 0 else None


def analyse(png):
    """Luminance/saturation of the opaque pixels: is this logo readable on a dark tile?"""
    from PIL import Image
    import numpy as np
    im = Image.open(png).convert("RGBA")
    a = np.asarray(im).astype(float) / 255
    mask = a[..., 3] > 0.5
    if mask.sum() < 50:
        return 0.0, 0.0, 0.0
    rgb = a[..., :3][mask]
    lum = (0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2])
    mx, mn = rgb.max(1), rgb.min(1)
    sat = np.where(mx > 0, (mx - mn) / np.maximum(mx, 1e-6), 0)
    visible = float(((lum > 0.45) | ((sat > 0.45) & (mx > 0.45))).mean())
    return float(lum.mean()), float(sat.mean()), visible


def best_logo(kind, ident, key):
    d = tmdb.get(f"{kind}/{ident}/images") or {}
    logos = d.get("logos", [])
    if not logos:
        base = tmdb.get(f"{kind}/{ident}") or {}
        logos = [{"file_path": base["logo_path"], "file_type": ".png", "width": 500, "vote_average": 0}] if base.get("logo_path") else []
    scored = []
    for i, l in enumerate(logos[:8]):
        probe = fetch(tmdb.img(l["file_path"], "w300"), os.path.join(OUT, "_probe", f"{key}-{i}.png"))
        if not probe:
            continue
        lum, sat, vis = analyse(probe)
        score = (l.get("vote_average") or 0) + 3 * vis + (0.5 if l.get("file_type") == ".svg" else 0) \
            + min(l.get("width") or 0, 1200) / 1200
        scored.append((score, vis, l))
    if not scored:
        return None, None
    scored.sort(key=lambda t: -t[0])
    _, vis, l = scored[0]
    return l, ("color" if vis > 0.55 else "white")


def resolve(key, src):
    kind, ident = src
    if kind == "n3":
        src = n3_file(ident.replace("__title__", "__cover__"))
        dest = os.path.join(OUT, f"{key}.png")
        if not os.path.exists(dest):
            subprocess.run(["magick", src, "-trim", "+repage", dest], check=True)
        return {"path": dest, "mode": "color"}
    if kind in ("network", "company"):
        l, mode = best_logo(kind, ident, key)
        if not l:
            return None
        path = l["file_path"]
        if l.get("file_type") == ".svg":
            path = os.path.splitext(path)[0] + ".svg"
        ext = os.path.splitext(path)[1]
        return {"path": fetch(tmdb.img(path), os.path.join(OUT, f"{key}{ext}")), "mode": mode}
    if kind == "provider":
        for media in ("movie", "tv"):
            for region in ("US", "IN"):
                d = tmdb.get(f"watch/providers/{media}", watch_region=region) or {}
                for p in d.get("results", []):
                    if p["provider_id"] == ident:
                        return {"path": fetch(tmdb.img(p["logo_path"]), os.path.join(OUT, f"{key}.icon.jpg")), "mode": "icon"}
        return None
    if kind == "wiki":
        api = ("https://commons.wikimedia.org/w/api.php?action=query&prop=imageinfo&iiprop=url&format=json&titles="
               + urllib.parse.quote(ident))
        req = urllib.request.Request(api, headers={"User-Agent": "nuvio-collections-builder/1.0"})
        data = json.load(urllib.request.urlopen(req))
        page = next(iter(data["query"]["pages"].values()))
        url = page["imageinfo"][0]["url"]
        ext = os.path.splitext(urllib.parse.urlparse(url).path)[1]
        return {"path": fetch(url, os.path.join(OUT, key + ext)), "mode": "white"}
    raise ValueError(kind)


def brand_logo(spec_key):
    """spec_key: a SERVICE_LOGOS key, 'company:ID' or 'network:ID'."""
    if spec_key in OVERRIDES:
        src, mode = OVERRIDES[spec_key]
        if src is None:
            base = brand_logo_plain(spec_key)
        elif src[0] == "n3c":
            dest = os.path.join(OUT, spec_key.replace(":", "-") + ".n3.png")
            if not os.path.exists(dest):
                subprocess.run(["magick", n3_file(src[1]), "-trim", "+repage", dest], check=True)
            base = {"path": dest, "mode": "color"}
        elif src[0] == "text":
            base = {"path": None, "mode": "text", "text": src[1]}
        else:
            base = resolve(spec_key.replace(":", "-"), src)
        if mode:
            base["mode"] = mode
        return base
    return brand_logo_plain(spec_key)


def brand_logo_plain(spec_key):
    if spec_key in SERVICE_LOGOS:
        return resolve(spec_key, SERVICE_LOGOS[spec_key])
    kind, ident = spec_key.split(":")
    return resolve(f"{kind}-{ident}", (kind, int(ident)))


if __name__ == "__main__":
    full = json.load(open(os.path.join(HERE, "collections.full.json")))
    keys = sorted({f["_art"]["logo"] for c in full for f in c["folders"] if f["_art"].get("kind") == "brand"})
    res = {}
    for k in keys:
        try:
            res[k] = brand_logo(k)
        except Exception as e:  # noqa: BLE001
            res[k] = None
            print("FAIL", k, e)
    json.dump(res, open(os.path.join(HERE, "logos.json"), "w"), indent=1)
    print(sum(1 for v in res.values() if v), "/", len(res))
    print([k for k, v in res.items() if not v])
