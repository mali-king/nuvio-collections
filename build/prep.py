"""Prepare what the cover templates measure: trimmed logos with their ink colour, still exposure, portrait cut-outs.

Writes prep.json next to art_plan.json. Logos are rasterised by Chromium (SVGs included) so they match the render.
"""
import colorsys
import hashlib
import json
import os
import shutil
import subprocess

import numpy as np
from PIL import Image

from logoprep import coverage, drop_small_lower, ink, load_rgba, trim

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "assets", "prep")
plan = json.load(open(os.path.join(HERE, "art_plan.json")))
logos = json.load(open(os.path.join(HERE, "logos.json")))
# Logos whose black lettering would vanish on a dark tile: near-black ink is repainted white.
DARK_INK_TO_WHITE = {"network:6"}


def tag(path, *extra):
    return hashlib.sha1("|".join([path, *map(str, extra)]).encode()).hexdigest()[:16]


def dominant_colour(im):
    """The logo's main saturated colour as #rrggbb, or None for white/black/grey marks."""
    arr = np.asarray(im.resize((max(1, im.width // 4), max(1, im.height // 4)))).astype(float) / 255
    m = arr[:, :, 3] > 0.5
    rgb = arr[:, :, :3][m]
    if len(rgb) == 0:
        return None
    sat = rgb.max(1) - rgb.min(1)
    keep = rgb[(sat > 0.3) & (rgb.max(1) > 0.25)]
    if len(keep) < 0.08 * len(rgb):
        return None
    hues = np.array([colorsys.rgb_to_hsv(*p)[0] for p in keep])
    bins = (hues * 24).astype(int) % 24
    top = np.bincount(bins, minlength=24).argmax()
    r, g, b = keep[bins == top].mean(0)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    r, g, b = colorsys.hsv_to_rgb(h, max(s, 0.65), 0.92)
    return "#%02x%02x%02x" % (int(r * 255), int(g * 255), int(b * 255))


def whiten_dark_ink(im):
    a = np.asarray(im).astype(float)
    rgb = a[:, :, :3] / 255
    dark = (rgb.max(2) < 0.25) & (rgb.max(2) - rgb.min(2) < 0.12)
    a[:, :, :3][dark] = 255
    return Image.fromarray(a.astype(np.uint8))


def rasterise_svgs(paths):
    """Render SVGs to transparent PNGs at 2400px wide through the same Chromium the covers use."""
    pages = os.path.join(OUT, "svg_pages")
    os.makedirs(pages, exist_ok=True)
    jobs = []
    for p in paths:
        page = os.path.join(pages, tag(p) + ".html")
        open(page, "w").write(
            '<!doctype html><html><head><style>html,body{margin:0;background:transparent}'
            'img{display:block;width:2400px;height:1200px;object-fit:contain}</style></head>'
            f'<body><img src="file://{p}"></body></html>')
        jobs.append({"html": page, "out": os.path.join(pages, tag(p) + ".png"), "width": 2400, "height": 1200,
                     "transparent": True})
    if jobs:
        jf = os.path.join(pages, "jobs.json")
        json.dump(jobs, open(jf, "w"))
        subprocess.run(["node", os.path.join(HERE, "render.cjs"), jf], check=True)
    return {p: j["out"] for p, j in zip(paths, jobs)}


def prep_logos():
    wanted = {}  # source path -> {"clean": bool, "icon": bool, "whiten": bool}
    for e in plan.values():
        if e["kind"] == "brand":
            lg = logos.get(e["logo_key"]) or {}
            if lg.get("path") and lg.get("mode") != "text":
                wanted[lg["path"]] = {"icon": lg.get("mode") == "icon", "whiten": e["logo_key"] in DARK_INK_TO_WHITE}
        elif e["kind"] == "franchise":
            for k in ("logo", "logo2"):
                if e.get(k):
                    wanted[e[k]] = {"clean": bool((e.get("logo_opts") or {}).get("clean")) and k == "logo"}
    svgs = rasterise_svgs(sorted(p for p in wanted if p.endswith(".svg")))
    out = {}
    os.makedirs(os.path.join(OUT, "logos"), exist_ok=True)
    for src, opts in wanted.items():
        dest = os.path.join(OUT, "logos", tag(src, opts.get("clean")) + ".png")
        if opts.get("icon"):  # square app icons keep their own background
            im = Image.open(src).convert("RGBA")
        else:
            im = trim(load_rgba(svgs.get(src, src)))
            if opts.get("clean"):
                im = drop_small_lower(im)
            if opts.get("whiten"):
                im = whiten_dark_ink(im)
        im.save(dest)
        lum, sat = ink(im)
        out[src] = {"png": dest, "w": im.width, "h": im.height, "lum": round(lum, 3), "sat": round(sat, 3),
                    "cov": round(coverage(im), 3),
                    "colour": None if opts.get("icon") else dominant_colour(im)}
    return out


def prep_stills():
    out = {}
    for e in plan.values():
        bg = e.get("bg")
        if bg and bg not in out and os.path.exists(bg):
            g = np.asarray(Image.open(bg).convert("L").resize((96, 54))).astype(float) / 255
            out[bg] = {"mean": round(float(g.mean()), 3), "right": round(float(g[:, 48:].mean()), 3)}
    return out


def prep_cutouts():
    tool = os.path.join(OUT, "cutout")
    if not os.path.exists(tool):
        subprocess.run(["swiftc", "-O", os.path.join(HERE, "cutout.swift"), "-o", tool], check=True)
    os.makedirs(os.path.join(OUT, "cut"), exist_ok=True)
    out, args = {}, []
    for key, e in plan.items():
        if e["kind"] == "director" and e.get("portrait"):
            dest = os.path.join(OUT, "cut", tag(e["portrait"]) + ".png")
            out[key] = dest
            if not os.path.exists(dest):
                args += [e["portrait"], dest]
    if args:
        subprocess.run([tool, *args], check=True)
        for dest in args[1::2]:
            if os.path.exists(dest):
                trim(load_rgba(dest), thresh=40).save(dest)
    return {k: v for k, v in out.items() if os.path.exists(v)}


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    result = {"logos": prep_logos(), "stills": prep_stills(), "cutouts": prep_cutouts()}
    json.dump(result, open(os.path.join(HERE, "prep.json"), "w"), indent=1)
    print("logos", len(result["logos"]), "stills", len(result["stills"]), "cutouts", len(result["cutouts"]))
    shutil.rmtree(os.path.join(OUT, "svg_pages"), ignore_errors=True)
