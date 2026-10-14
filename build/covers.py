"""Render every collection cover (1600x900 WebP) from art_plan.json with HTML templates + Playwright."""
import html
import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
PNG = os.path.join(HERE, "png")
OUT = os.path.join(HERE, "..", "covers")
W, H = 1600, 900

plan = json.load(open(os.path.join(HERE, "art_plan.json")))
logos = json.load(open(os.path.join(HERE, "logos.json")))

KICKER = {
    "genres": "Genre", "indian-cinema": "Indian Cinema", "world-cinema": "World Cinema",
    "moods-and-themes": "Mood", "decades": "Decade", "critics-picks": "Critics’ Picks",
}
ACCENT = {
    "genres": "#F5B841", "indian-cinema": "#FF9F43", "world-cinema": "#4FD1C5",
    "moods-and-themes": "#B794F4", "decades": "#E8C170", "critics-picks": "#F6E05E",
    "franchises-and-universes": "#FFFFFF", "indian-universes": "#FF9F43", "directors": "#FFFFFF",
}
NATIVE = {
    "indian-cinema/bollywood": "हिन्दी सिनेमा", "indian-cinema/telugu": "తెలుగు",
    "indian-cinema/tamil": "தமிழ்", "indian-cinema/malayalam": "മലയാളം", "indian-cinema/kannada": "ಕನ್ನಡ",
    "indian-cinema/bengali": "বাংলা", "indian-cinema/marathi": "मराठी", "indian-cinema/punjabi": "ਪੰਜਾਬੀ",
    "world-cinema/korean": "한국", "world-cinema/anime": "アニメ", "world-cinema/japanese": "日本映画",
    "world-cinema/chinese": "华语", "world-cinema/turkish": "Türk", "world-cinema/spanish": "Español",
    "world-cinema/latin-american": "Latinoamérica", "world-cinema/french": "Français",
    "world-cinema/italian": "Italiano", "world-cinema/german": "Deutsch", "world-cinema/nordic": "Norden",
    "world-cinema/thai": "ไทย", "world-cinema/filipino": "Pilipino", "world-cinema/arabic": "عربي",
}
# Optional per-tile tweaks: {"key": {"pos": "70% 30%", "logoScale": 0.8, ...}}
TWEAKS = json.load(open(os.path.join(HERE, "tweaks.json"))) if os.path.exists(os.path.join(HERE, "tweaks.json")) else {}

BASE_CSS = f"""
*{{margin:0;padding:0;box-sizing:border-box}}
html,body{{width:{W}px;height:{H}px;overflow:hidden;background:#07070a}}
body{{font-family:-apple-system,"SF Pro Display",system-ui,sans-serif;color:#fff;-webkit-font-smoothing:antialiased}}
.bg{{position:absolute;inset:0;background-size:cover;background-position:var(--pos,center)}}
.layer{{position:absolute;inset:0}}
.noise{{position:absolute;inset:0;opacity:.05;mix-blend-mode:overlay;
  background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>")}}
.frame{{position:absolute;inset:0;box-shadow:inset 0 0 0 2px rgba(255,255,255,.06)}}
"""


def url(p):
    return "file://" + p


def esc(s):
    return html.escape(s or "")


def title_size(t, base=150):
    n = len(t)
    if n <= 8:
        return base
    if n <= 12:
        return int(base * .86)
    if n <= 16:
        return int(base * .74)
    if n <= 22:
        return int(base * .64)
    return int(base * .56)


def scene(e, key):
    tw = TWEAKS.get(key, {})
    accent = ACCENT.get(e["collection"], "#fff")
    native = NATIVE.get(key)
    kicker = KICKER.get(e["collection"], "")
    size = tw.get("size") or title_size(e["title"])
    native_html = f'<div class="native">{esc(native)}</div>' if native else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
.bg{{filter:saturate({tw.get('sat', .95)}) contrast(1.06) brightness({tw.get('bright', .86)})}}
.g1{{background:linear-gradient(90deg,rgba(6,6,9,.94) 0%,rgba(6,6,9,.72) 30%,rgba(6,6,9,.18) 62%,rgba(6,6,9,0) 78%)}}
.g2{{background:linear-gradient(0deg,rgba(6,6,9,.88) 0%,rgba(6,6,9,.25) 38%,rgba(6,6,9,0) 60%)}}
.g3{{background:radial-gradient(120% 90% at 100% 0%,rgba(0,0,0,0) 40%,rgba(0,0,0,.35) 100%)}}
.text{{position:absolute;left:104px;bottom:96px;right:40%}}
.bar{{width:64px;height:7px;border-radius:4px;background:{accent};margin-bottom:26px;box-shadow:0 0 24px {accent}88}}
.kicker{{font-size:30px;font-weight:700;letter-spacing:.3em;text-transform:uppercase;color:rgba(255,255,255,.72);margin-bottom:14px}}
.title{{font-size:{size}px;font-weight:800;letter-spacing:-.035em;line-height:.95;text-shadow:0 4px 40px rgba(0,0,0,.45)}}
.native{{margin-top:22px;font-size:46px;font-weight:600;color:{accent};opacity:.95;letter-spacing:.01em}}
</style></head><body>
<div class="bg" style="background-image:url('{url(e['bg'])}');--pos:{tw.get('pos', 'center')}"></div>
<div class="layer g1"></div><div class="layer g2"></div><div class="layer g3"></div><div class="noise"></div>
<div class="text"><div class="bar"></div><div class="kicker">{esc(kicker)}</div><div class="title">{esc(e['title'])}</div>{native_html}</div>
<div class="frame"></div></body></html>"""


def franchise(e, key):
    tw = TWEAKS.get(key, {})
    logo = e.get("logo")
    lf = tw.get("logoFilter", "none")
    lw, lh = tw.get("logoW", 46), tw.get("logoH", 36)
    if logo:
        mark = f'<img class="logo" src="{url(logo)}" style="filter:{lf} drop-shadow(0 10px 40px rgba(0,0,0,.65))">'
    else:
        mark = f'<div class="ttl">{esc(e["title"])}</div>'
    kicker = "Universe" if "universe" in e["title"].lower() or e["collection"] == "indian-universes" else "Collection"
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
.bg{{filter:saturate(1.02) contrast(1.05) brightness({tw.get('bright', .8)})}}
.g1{{background:linear-gradient(90deg,rgba(5,5,8,.9) 0%,rgba(5,5,8,.62) 34%,rgba(5,5,8,.08) 66%,rgba(5,5,8,0) 80%)}}
.g2{{background:linear-gradient(0deg,rgba(5,5,8,.8) 0%,rgba(5,5,8,0) 46%)}}
.wrap{{position:absolute;left:100px;top:0;bottom:0;width:{lw}%;display:flex;flex-direction:column;justify-content:center;align-items:flex-start}}
.logo{{width:100%;height:{lh * H / 100}px;object-fit:contain;object-position:left center}}
.ttl{{font-size:{title_size(e['title'], 132)}px;font-weight:800;letter-spacing:-.03em;line-height:.95}}
.kicker{{position:absolute;left:104px;bottom:80px;font-size:26px;font-weight:700;letter-spacing:.32em;text-transform:uppercase;color:rgba(255,255,255,.6)}}
</style></head><body>
<div class="bg" style="background-image:url('{url(e['bg'])}');--pos:{tw.get('pos', 'center')}"></div>
<div class="layer g1"></div><div class="layer g2"></div><div class="noise"></div>
<div class="wrap">{mark}</div><div class="kicker">{kicker}</div>
<div class="frame"></div></body></html>"""


def director(e, key):
    tw = TWEAKS.get(key, {})
    films = " · ".join(esc(f) for f in (e.get("films") or [])[:3])
    parts = e["title"].split(" ")
    first, last = (" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else ("", parts[0])
    if e["title"] in ("Bong Joon Ho", "Wong Kar-wai", "Park Chan-wook", "S. S. Rajamouli", "Guillermo del Toro",
                      "Paul Thomas Anderson", "Sanjay Leela Bhansali"):
        first, last = {"Bong Joon Ho": ("Bong", "Joon Ho"), "Wong Kar-wai": ("Wong", "Kar-wai"),
                       "Park Chan-wook": ("Park", "Chan-wook"), "S. S. Rajamouli": ("S. S.", "Rajamouli"),
                       "Guillermo del Toro": ("Guillermo", "del Toro"),
                       "Paul Thomas Anderson": ("Paul Thomas", "Anderson"),
                       "Sanjay Leela Bhansali": ("Sanjay Leela", "Bhansali")}[e["title"]]
    lsize = 128 if len(last) <= 9 else (108 if len(last) <= 12 else 92)
    portrait = e.get("portrait")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
.bg{{filter:grayscale(1) brightness(.34) contrast(1.1) blur(1px);transform:scale(1.02)}}
.tint{{background:linear-gradient(90deg,rgba(8,8,10,.96) 0%,rgba(8,8,10,.8) 40%,rgba(8,8,10,.2) 100%)}}
.portrait{{position:absolute;right:0;top:0;height:100%;width:62%;background-size:cover;background-position:{tw.get('pos', 'center 22%')};
  filter:grayscale(1) contrast(1.12) brightness(.95);
  -webkit-mask-image:linear-gradient(90deg,transparent 0%,rgba(0,0,0,.55) 22%,#000 48%);}}
.glow{{background:radial-gradient(70% 90% at 78% 40%,rgba(255,255,255,.07),transparent 70%)}}
.text{{position:absolute;left:104px;bottom:100px;width:56%}}
.kicker{{font-size:26px;font-weight:700;letter-spacing:.34em;text-transform:uppercase;color:rgba(255,255,255,.6);margin-bottom:22px}}
.first{{font-family:"New York","Iowan Old Style",Georgia,serif;font-size:62px;font-weight:400;font-style:italic;color:rgba(255,255,255,.86);line-height:1}}
.last{{font-family:"New York","Iowan Old Style",Georgia,serif;font-size:{lsize}px;font-weight:600;letter-spacing:-.01em;line-height:1.02}}
.films{{margin-top:26px;font-size:28px;font-weight:500;color:rgba(255,255,255,.62);letter-spacing:.01em;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.rule{{width:72px;height:3px;background:#fff;opacity:.7;margin:28px 0 0}}
</style></head><body>
<div class="bg" style="background-image:url('{url(e['bg'])}')"></div><div class="layer tint"></div>
<div class="portrait" style="background-image:url('{url(portrait) if portrait else ''}')"></div>
<div class="layer glow"></div><div class="noise"></div>
<div class="text"><div class="kicker">A film by</div><div class="first">{esc(first)}</div><div class="last">{esc(last)}</div>
<div class="rule"></div><div class="films">{films}</div></div>
<div class="frame"></div></body></html>"""


def brand(e, key):
    tw = TWEAKS.get(key, {})
    lg = logos.get(e["logo_key"]) or {}
    mode = lg.get("mode", "color")
    posters = e.get("posters", [])
    while posters and len(posters) < 21:
        posters = posters + posters
    posters = posters[:21]
    tiles = "".join(f'<div class="p" style="background-image:url(\'{url(p)}\')"></div>' for p in posters)
    scale = tw.get("logoScale", 1.0)
    if mode == "icon":
        name = e["title"].replace(" India", "")
        mark = (f'<div class="iconrow"><img class="icon" src="{url(lg["path"])}">'
                f'<div class="iname">{esc(name)}</div></div>')
    elif mode == "text":
        mark = f'<div class="tname">{esc(lg.get("text") or e["title"])}</div>'
    else:
        flt = {"white": "brightness(0) invert(1)", "invert": "invert(1)", "color": "none"}[mode]
        mark = (f'<img class="logo" src="{url(lg["path"])}" style="filter:{flt} drop-shadow(0 10px 36px rgba(0,0,0,.7));'
                f'width:{int(760 * scale)}px;height:{int(250 * scale)}px">')
    badge = f'<div class="badge">{esc(e["badge"])}</div>' if e.get("badge") else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
body{{background:#09090d}}
.wall{{position:absolute;left:50%;top:50%;width:2350px;display:grid;grid-template-columns:repeat(7,1fr);gap:22px;
  transform:translate(-50%,-50%) rotate(-11deg) scale(1.02)}}
.p{{aspect-ratio:2/3;border-radius:14px;background-size:cover;background-position:center;
  filter:saturate(.95) brightness(.62);box-shadow:0 18px 40px rgba(0,0,0,.5)}}
.shade{{background:radial-gradient(58% 62% at 50% 50%,rgba(6,6,9,.86) 0%,rgba(6,6,9,.62) 55%,rgba(6,6,9,.35) 100%)}}
.edge{{background:linear-gradient(0deg,rgba(6,6,9,.6),rgba(6,6,9,0) 30%,rgba(6,6,9,0) 70%,rgba(6,6,9,.5))}}
.center{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}}
.logo{{object-fit:contain}}
.iconrow{{display:flex;align-items:center;gap:44px}}
.icon{{width:{int(210 * scale)}px;height:{int(210 * scale)}px;border-radius:24%;box-shadow:0 18px 50px rgba(0,0,0,.6)}}
.iname{{font-size:{int(112 * scale)}px;font-weight:800;letter-spacing:-.03em}}
.tname{{font-size:120px;font-weight:800;letter-spacing:-.03em}}
.badge{{margin-top:34px;font-size:30px;font-weight:700;letter-spacing:.45em;text-transform:uppercase;padding:12px 26px 12px 38px;
  border:2px solid rgba(255,255,255,.55);border-radius:999px;color:#fff}}
</style></head><body>
<div class="wall">{tiles}</div><div class="layer shade"></div><div class="layer edge"></div><div class="noise"></div>
<div class="center">{mark}{badge}</div><div class="frame"></div></body></html>"""


TEMPLATES = {"scene": scene, "franchise": franchise, "director": director, "brand": brand}


def main(only=None):
    os.makedirs(PAGES, exist_ok=True)
    os.makedirs(PNG, exist_ok=True)
    jobs = []
    for key, e in plan.items():
        if only and not any(key.startswith(o) for o in only):
            continue
        page = os.path.join(PAGES, key.replace("/", "__") + ".html")
        open(page, "w").write(TEMPLATES[e["kind"]](e, key))
        jobs.append({"html": page, "out": os.path.join(PNG, key.replace("/", "__") + ".png"), "width": W, "height": H})
    jf = os.path.join(HERE, "jobs_covers.json")
    json.dump(jobs, open(jf, "w"))
    subprocess.run(["node", os.path.join(HERE, "render.cjs"), jf], check=True)

    def to_webp(j):
        key = os.path.basename(j["out"])[:-4]
        col, slug = key.split("__")
        os.makedirs(os.path.join(OUT, col), exist_ok=True)
        subprocess.run(["cwebp", "-quiet", "-q", "84", "-m", "6", "-sharp_yuv", j["out"], "-o",
                        os.path.join(OUT, col, slug + ".webp")], check=True)
    with ThreadPoolExecutor(8) as ex:
        list(ex.map(to_webp, jobs))
    print("webp done", len(jobs))


if __name__ == "__main__":
    main(sys.argv[1:] or None)
