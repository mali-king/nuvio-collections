"""Pick and download the artwork every cover needs (textless backdrops, posters, title logos, portraits)."""
import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor

import tmdb
from logos import n3_file

HERE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(HERE, "assets", "img")
os.makedirs(IMG, exist_ok=True)

# Curated hero picks ("movie:ID" / "tv:ID"), keyed by "collection/folder". Filled in after reviewing sheets.
HERO = json.load(open(os.path.join(HERE, "hero_overrides.json"))) if os.path.exists(
    os.path.join(HERE, "hero_overrides.json")) else {}
# Title-logo source per franchise ("movie:ID" / "tv:ID" / "n3:file").
LOGO = json.load(open(os.path.join(HERE, "logo_overrides.json"))) if os.path.exists(
    os.path.join(HERE, "logo_overrides.json")) else {}


def fetch(url, dest):
    if not os.path.exists(dest) or os.path.getsize(dest) == 0:
        subprocess.run(["curl", "-sfL", "-m", "90", "-o", dest, url], check=False)
    return dest if os.path.exists(dest) and os.path.getsize(dest) > 0 else None


def media_of(item, source):
    if item.get("media_type") in ("movie", "tv"):
        return item["media_type"]
    if source.get("tmdbSourceType") == "NETWORK" or source.get("mediaType") in ("tv", "series"):
        return "tv"
    return "movie"


def textless_backdrop(media, tid):
    d = tmdb.get(f"{media}/{tid}/images", include_image_language="null") or {}
    bds = [b for b in d.get("backdrops", []) if b.get("iso_639_1") is None and b["width"] >= 1280
           and 1.7 <= b["aspect_ratio"] <= 1.8]
    if not bds:
        return None
    bds.sort(key=lambda b: (-(b["vote_average"] or 0), -b["width"]))
    return bds[0]["file_path"]


def title_logo(media, tid):
    d = tmdb.get(f"{media}/{tid}/images", include_image_language="en,null") or {}
    logos = [l for l in d.get("logos", []) if l.get("iso_639_1") in ("en", None)]
    if not logos:
        return None
    logos.sort(key=lambda l: (-(l["vote_average"] or 0), l.get("file_type") != ".svg", -l["width"]))
    l = logos[0]
    path = l["file_path"]
    if l.get("file_type") == ".svg":
        path = os.path.splitext(path)[0] + ".svg"
    return path


def candidates(folder, prefer=None, limit=40):
    """Items from the folder's own rails, most recognisable first."""
    seen, out = set(), []
    order = folder["sources"]
    if prefer:
        order = sorted(order, key=lambda s: 0 if any(p in s["title"] for p in prefer) else 1)
    for s in order:
        _, items = tmdb.resolve(s)
        for it in items:
            m = media_of(it, s)
            key = f"{m}:{it['id']}"
            if key in seen:
                continue
            seen.add(key)
            out.append((key, it))
    return out[:limit] if limit else out


USED = set(HERO.values())


def pick_hero(folder, prefer=None, rank="votes"):
    ck = f"{folder['_art']['collection']}/{folder['_art']['slug']}"
    if ck in HERO:
        key = HERO[ck]
        m, tid = key.split(":")
        path = textless_backdrop(m, tid) or (tmdb.get(f"{m}/{tid}") or {}).get("backdrop_path")
        return key, path
    cands = candidates(folder, prefer)
    if rank == "votes":
        cands.sort(key=lambda kv: -(kv[1].get("vote_count") or 0))
    for key, it in cands:
        if key in USED:
            continue
        m, tid = key.split(":")
        path = textless_backdrop(m, tid)
        if path:
            USED.add(key)
            return key, path
    return None, None


def plan():
    full = json.load(open(os.path.join(HERE, "collections.full.json")))
    jobs, plan_out = [], {}
    # Pass 1: the tiles whose hero choice matters most claim films first.
    order = ["franchises-and-universes", "indian-universes", "directors", "genres", "indian-cinema",
             "world-cinema", "decades", "critics-picks", "moods-and-themes", "streaming-services",
             "indian-streaming", "studios", "networks"]
    by_slug = {f"{c['folders'][0]['_art']['collection']}": c for c in full if c["folders"]}
    for cslug in order:
        c = by_slug[cslug]
        for f in c["folders"]:
            art = f["_art"]
            key = f"{art['collection']}/{art['slug']}"
            entry = {"kind": art["kind"], "title": art["title"], "collection": art["collection"], "slug": art["slug"]}
            if art["kind"] in ("scene", "franchise"):
                hk, hp = pick_hero(f)
                entry["hero"] = hk
                if hp:
                    entry["bg"] = os.path.join(IMG, f"bd{hp.replace('/', '_')}")
                    jobs.append((tmdb.img(hp, "original"), entry["bg"]))
                if art["kind"] == "franchise":
                    lk = LOGO.get(key) or hk
                    entry["logo_src"] = lk
                    if lk and lk.startswith("file:"):
                        entry["logo"] = os.path.join(HERE, lk[5:])
                    elif lk and lk.startswith("n3:"):
                        dest = os.path.join(IMG, "n3_" + lk[3:].replace(".webp", ".png"))
                        if not os.path.exists(dest):
                            subprocess.run(["magick", n3_file(lk[3:]), "-trim", "+repage", dest], check=True)
                        entry["logo"] = dest
                    elif lk:
                        m, tid = lk.split(":")
                        lp = title_logo(m, tid)
                        if lp:
                            entry["logo"] = os.path.join(IMG, f"logo{lp.replace('/', '_')}")
                            jobs.append((tmdb.img(lp, "original"), entry["logo"]))
            elif art["kind"] == "director":
                pid = art["person"]
                imgs = (tmdb.get(f"person/{pid}/images") or {}).get("profiles", [])
                imgs.sort(key=lambda p: (-(p["vote_average"] or 0), -p["width"]))
                if imgs:
                    entry["portrait"] = os.path.join(IMG, f"pf{imgs[0]['file_path'].replace('/', '_')}")
                    jobs.append((tmdb.img(imgs[0]["file_path"], "original"), entry["portrait"]))
                hk, hp = pick_hero(f, prefer=["Essentials"])
                entry["hero"] = hk
                if hp:
                    entry["bg"] = os.path.join(IMG, f"bd{hp.replace('/', '_')}")
                    jobs.append((tmdb.img(hp, "w1280"), entry["bg"]))
                films = [it for _, it in candidates(f, ["Essentials"], 0) if it.get("title")]
                films.sort(key=lambda it: -(it.get("vote_count") or 0))
                entry["films"] = [it["title"] for it in films[:4]]
            elif art["kind"] == "brand":
                entry["logo_key"] = art["logo"]
                entry["badge"] = art.get("badge")
                posters = []
                for k, it in candidates(f, ["Originals", "Popular", "Essentials"], 60):
                    if it.get("poster_path") and (it.get("vote_count") or 0) >= 5:
                        posters.append(it["poster_path"])
                    if len(posters) >= 18:
                        break
                entry["posters"] = [os.path.join(IMG, f"po{p.replace('/', '_')}") for p in posters]
                jobs += [(tmdb.img(p, "w342"), os.path.join(IMG, f"po{p.replace('/', '_')}")) for p in posters]
            plan_out[key] = entry
    with ThreadPoolExecutor(12) as ex:
        list(ex.map(lambda j: fetch(*j), jobs))
    json.dump(plan_out, open(os.path.join(HERE, "art_plan.json"), "w"), indent=1, ensure_ascii=False)
    missing = [k for k, v in plan_out.items() if v["kind"] in ("scene", "franchise", "director") and not v.get("bg")]
    print("tiles", len(plan_out), "downloads", len(jobs), "missing bg", missing)
    print("franchise without logo", [k for k, v in plan_out.items() if v["kind"] == "franchise" and not v.get("logo")])


if __name__ == "__main__":
    plan()
