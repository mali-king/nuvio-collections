"""Render every collection cover (1600x900 WebP) from art_plan.json + prep.json with HTML templates + Playwright.

Nuvio draws a folder tile about 288pt wide on the Mac and 206pt on a phone, so one canvas pixel is 0.13-0.18pt.
Nothing here is smaller than ~70px for that reason: type that would land under ~9pt on the phone is left out.
"""
import html
import json
import math
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
PAGES = os.path.join(HERE, "pages")
PNG = os.path.join(HERE, "png")
OUT = os.environ.get("COVERS_OUT") or os.path.join(HERE, "..", "covers")
W, H = 1600, 900

plan = json.load(open(os.path.join(HERE, "art_plan.json")))
logos = json.load(open(os.path.join(HERE, "logos.json")))
prep = json.load(open(os.path.join(HERE, "prep.json")))

ACCENT = {
    "genres": "#F5B841", "indian-cinema": "#FF9F43", "world-cinema": "#4FD1C5",
    "moods-and-themes": "#B794F4", "decades": "#E8C170", "critics-picks": "#F6E05E",
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
# Brand tint behind the logo. Measured from the logo's own colour unless set here; None = neutral grey.
TINT = {
    "streaming-services/apple-tv": "#8e9bb0", "streaming-services/disney-plus": "#1f4fe0",
    "streaming-services/hbo-max": "#6a2cf0", "streaming-services/mubi": "#3550ff",
    "streaming-services/amc-plus": None, "streaming-services/criterion-channel": None,
    "indian-streaming/sonyliv": "#7b3fe4", "indian-streaming/zee5": "#8230c6",
    "indian-streaming/amazon-mx-player": "#2f8cff", "indian-streaming/sun-nxt": "#e8432d",
    "indian-streaming/lionsgate-play": None, "indian-streaming/shemaroome": "#ff8a00",
    "studios/pixar": "#3b82f6", "studios/walt-disney-animation": "#2f6fe0", "studios/walt-disney-pictures": "#2f6fe0",
    "studios/dreamworks-animation": "#4a90e2", "studios/illumination": "#f5c518", "studios/studio-ghibli": "#3a86d8",
    "studios/20th-century": "#d9a53a", "studios/neon": "#ff3ec8", "studios/blumhouse": "#c0392b",
    "studios/searchlight": "#d9a53a", "studios/toho": "#d0303a", "studios/mappa": None,
    "studios/hombale-films": "#d9a53a",
    "networks/cbs": "#2f6fe0", "networks/disney-channel": "#2f6fe0", "networks/discovery": "#2f6fe0",
    "networks/cartoon-network": None,
}
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


def exposure(bg, base, target=0.34):
    """Brightness that brings a still's average luminance near the target, so dark and bright stills read alike."""
    st = prep["stills"].get(bg) or {}
    mean = max(st.get("mean", target), 0.05)
    return round(base * min(1.45, max(0.78, (target / mean) ** 0.6)), 3)


def fit(w, h, area, max_w, max_h, cov=None):
    """Size a mark by area rather than by box, so wide and square logos read at the same optical weight.

    cov is the share of the box that is ink: airy marks (thin type, outlines) get up to 1.7x the area, solid blocks a little less."""
    if cov:
        area *= min(1.7, max(0.8, (0.42 / cov) ** 0.6))
    ar = w / max(h, 1)
    fw, fh = math.sqrt(area * ar), math.sqrt(area / ar)
    k = min(1.0, max_w / fw, max_h / fh)
    return int(fw * k), int(fh * k)


def logo_meta(path):
    return prep["logos"].get(path) or {}


# Fit the title in the browser: one line as large as fits (down to 150px), else two balanced lines up to 176px.
FIT_JS = """<script>
(function () {
  const t = document.querySelector('.title');
  const w = t.parentElement.clientWidth;
  t.classList.add('one');
  for (let s = 200; s >= 150; s -= 2) { t.style.fontSize = s + 'px'; if (t.scrollWidth <= w) return; }
  t.classList.remove('one');
  for (let s = 176; s >= 96; s -= 2) {
    t.style.fontSize = s + 'px';
    const words = t.textContent.split(' ');
    const lines = Math.round(t.getBoundingClientRect().height / (s * 0.92));
    const probe = document.createElement('span');
    probe.style.cssText = 'position:absolute;visibility:hidden;white-space:nowrap;font:inherit;letter-spacing:inherit';
    t.appendChild(probe);
    const widest = Math.max(...words.map(x => { probe.textContent = x; return probe.getBoundingClientRect().width; }));
    probe.remove();
    if (lines <= 2 && widest <= w) return;
  }
})();
</script>"""


def title_size(t, sizes=(200, 172, 150, 132, 120)):
    n = len(t)
    return sizes[0] if n <= 8 else sizes[1] if n <= 12 else sizes[2] if n <= 16 else sizes[3] if n <= 22 else sizes[4]


def scene(e, key):
    tw = TWEAKS.get(key, {})
    accent = ACCENT.get(e["collection"], "#fff")
    native = NATIVE.get(key)
    size = tw.get("size") or title_size(e["title"])
    bright = exposure(e["bg"], tw.get("bright", 0.9))
    native_html = f'<div class="native">{esc(native)}</div>' if native else ""
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
.bg{{filter:saturate({tw.get('sat', 1)}) contrast(1.06) brightness({bright})}}
.g1{{background:linear-gradient(90deg,rgba(6,6,9,.9) 0%,rgba(6,6,9,.62) 32%,rgba(6,6,9,.12) 62%,rgba(6,6,9,0) 76%)}}
.g2{{background:linear-gradient(0deg,rgba(6,6,9,.9) 0%,rgba(6,6,9,.35) 40%,rgba(6,6,9,0) 64%)}}
.g3{{background:radial-gradient(120% 90% at 100% 0%,rgba(0,0,0,0) 45%,rgba(0,0,0,.3) 100%)}}
.text{{position:absolute;left:96px;bottom:92px;width:64%}}
.bar{{width:120px;height:14px;border-radius:7px;background:{accent};margin-bottom:34px;box-shadow:0 0 32px {accent}99}}
.title{{font-size:{size}px;font-weight:800;letter-spacing:-.035em;line-height:.92;text-wrap:balance;
  text-shadow:0 6px 50px rgba(0,0,0,.5)}}
.title.one{{white-space:nowrap}}
.native{{margin-top:26px;font-size:84px;font-weight:700;color:{accent};letter-spacing:.005em;line-height:1.1;
  text-shadow:0 4px 30px rgba(0,0,0,.5)}}
</style></head><body>
<div class="bg" style="background-image:url('{url(e['bg'])}');--pos:{tw.get('pos', 'center')}"></div>
<div class="layer g1"></div><div class="layer g2"></div><div class="layer g3"></div><div class="noise"></div>
<div class="text"><div class="bar"></div><div class="title">{esc(e['title'])}</div>{native_html}</div>
<div class="frame"></div>{FIT_JS if not tw.get('size') else ''}</body></html>"""


def franchise_mark(e, tw):
    opts = e.get("logo_opts") or {}
    white = "brightness(0) invert(1) " if opts.get("white") else ""
    flt = f"{tw.get('logoFilter', '')} {white}drop-shadow(0 10px 50px rgba(0,0,0,.75))"
    scale = tw.get("logoScale", 1.0)
    if opts.get("typeset"):
        first, second = opts["typeset"]
        fs = 168 if len(first) <= 8 else 140 if len(first) <= 12 else 118
        return (f'<div class="ts"><div class="ts1" style="font-size:{fs}px">{esc(first)}</div>'
                f'<div class="ts2">{esc(second)}</div></div>')
    if e.get("logo") and e.get("logo2"):
        m1, m2 = logo_meta(e["logo"]), logo_meta(e["logo2"])
        w1, h1 = fit(m1["w"], m1["h"], 95000 * scale, 720, 220, m1.get("cov"))
        w2, h2 = fit(m2["w"], m2["h"], 95000 * scale, 720, 220, m2.get("cov"))
        return (f'<img class="logo" src="{url(m1["png"])}" style="width:{w1}px;height:{h1}px;filter:{flt}">'
                f'<div class="amp">&amp;</div>'
                f'<img class="logo" src="{url(m2["png"])}" style="width:{w2}px;height:{h2}px;filter:{flt}">')
    if e.get("logo"):
        m = logo_meta(e["logo"])
        w, h = fit(m["w"], m["h"], 210000 * scale, 860, 400, m.get("cov"))
        return f'<img class="logo" src="{url(m["png"])}" style="width:{w}px;height:{h}px;filter:{flt}">'
    return f'<div class="ts"><div class="ts1" style="font-size:{title_size(e["title"], (176, 150, 128, 112, 100))}px">{esc(e["title"])}</div></div>'


def franchise(e, key):
    tw = TWEAKS.get(key, {})
    bright = exposure(e["bg"], tw.get("bright", 0.88), target=0.32)
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
.bg{{filter:saturate(1.04) contrast(1.05) brightness({bright})}}
.g1{{background:linear-gradient(90deg,rgba(5,5,8,.88) 0%,rgba(5,5,8,.6) 34%,rgba(5,5,8,.08) 64%,rgba(5,5,8,0) 78%)}}
.g2{{background:linear-gradient(0deg,rgba(5,5,8,.7) 0%,rgba(5,5,8,0) 42%)}}
.wrap{{position:absolute;left:96px;top:0;bottom:0;width:56%;display:flex;flex-direction:column;justify-content:center;
  align-items:flex-start;gap:6px;padding-top:{tw.get('logoY', 20)}px}}
.logo{{display:block;object-fit:contain;object-position:left center}}
.amp{{font-family:"New York","Iowan Old Style",Georgia,serif;font-style:italic;font-size:92px;line-height:1;
  color:rgba(255,255,255,.85);margin:4px 0 8px 6px;text-shadow:0 4px 30px rgba(0,0,0,.6)}}
.ts1{{font-weight:800;letter-spacing:-.035em;line-height:.92;text-wrap:balance;text-shadow:0 6px 50px rgba(0,0,0,.55)}}
.ts2{{margin-top:20px;font-size:64px;font-weight:700;letter-spacing:.22em;text-transform:uppercase;color:#FF9F43;
  text-shadow:0 4px 30px rgba(0,0,0,.5)}}
</style></head><body>
<div class="bg" style="background-image:url('{url(e['bg'])}');--pos:{tw.get('pos', 'center')}"></div>
<div class="layer g1"></div><div class="layer g2"></div><div class="noise"></div>
<div class="wrap">{franchise_mark(e, tw)}</div>
<div class="frame"></div></body></html>"""


SPLIT = {"Bong Joon Ho": ("Bong", "Joon Ho"), "Wong Kar-wai": ("Wong", "Kar-wai"),
         "Park Chan-wook": ("Park", "Chan-wook"), "S. S. Rajamouli": ("S. S.", "Rajamouli"),
         "Guillermo del Toro": ("Guillermo", "del Toro"), "Paul Thomas Anderson": ("Paul Thomas", "Anderson"),
         "Sanjay Leela Bhansali": ("Sanjay Leela", "Bhansali")}


def director(e, key):
    tw = TWEAKS.get(key, {})
    parts = e["title"].split(" ")
    first, last = SPLIT.get(e["title"]) or ((" ".join(parts[:-1]), parts[-1]) if len(parts) > 1 else ("", parts[0]))
    lsize = 176 if len(last) <= 7 else 156 if len(last) <= 9 else 132 if len(last) <= 11 else 116
    cut = prep["cutouts"].get(key)
    bright = exposure(e["bg"], tw.get("bright", 0.5), target=0.3)
    person = (f'<img class="cut" src="{url(cut)}">' if cut else
              f'<div class="portrait" style="background-image:url(\'{url(e.get("portrait", ""))}\')"></div>')
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
.bg{{filter:saturate(.7) contrast(1.05) brightness({bright}) blur(3px);transform:scale(1.06)}}
.tint{{background:linear-gradient(90deg,rgba(8,8,10,.94) 0%,rgba(8,8,10,.7) 38%,rgba(8,8,10,.15) 72%,rgba(8,8,10,.35) 100%)}}
.floor{{background:linear-gradient(0deg,rgba(8,8,10,.55) 0%,rgba(8,8,10,0) 30%)}}
.cut{{position:absolute;right:{tw.get('cutRight', 40)}px;bottom:0;height:{tw.get('cutH', 100)}%;max-width:62%;object-fit:contain;
  object-position:right bottom;filter:grayscale(1) contrast(1.12) brightness(1.04) drop-shadow(-40px 0 70px rgba(0,0,0,.7))}}
.portrait{{position:absolute;right:0;top:0;height:100%;width:60%;background-size:cover;background-position:center 22%;
  filter:grayscale(1) contrast(1.1);-webkit-mask-image:linear-gradient(90deg,transparent 0%,#000 45%)}}
.text{{position:absolute;left:96px;bottom:96px;width:54%}}
.first{{font-family:"New York","Iowan Old Style",Georgia,serif;font-size:84px;font-weight:400;font-style:italic;
  color:rgba(255,255,255,.88);line-height:1.05}}
.last{{font-family:"New York","Iowan Old Style",Georgia,serif;font-size:{lsize}px;font-weight:600;letter-spacing:-.015em;
  line-height:.98;white-space:nowrap}}
.rule{{width:120px;height:8px;border-radius:4px;background:#fff;opacity:.85;margin-bottom:36px}}
</style></head><body>
<div class="bg" style="background-image:url('{url(e['bg'])}')"></div><div class="layer tint"></div>
{person}<div class="layer floor"></div><div class="noise"></div>
<div class="text"><div class="rule"></div><div class="first">{esc(first)}</div><div class="last">{esc(last)}</div></div>
<div class="frame"></div></body></html>"""


def brand(e, key):
    tw = TWEAKS.get(key, {})
    lg = logos.get(e["logo_key"]) or {}
    mode = lg.get("mode", "color")
    meta = logo_meta(lg.get("path"))
    tint = TINT[key] if key in TINT else meta.get("colour")
    posters = e.get("posters", [])
    while posters and len(posters) < 21:
        posters = posters + posters
    posters = posters[:21]
    tiles = "".join(f'<div class="p" style="background-image:url(\'{url(p)}\')"></div>' for p in posters)
    scale = tw.get("logoScale", 1.0)
    if mode == "icon":
        name = e["title"].replace(" India", "")
        fs = 116 if len(name) <= 10 else 100 if len(name) <= 14 else 88
        mark = (f'<div class="iconrow"><img class="icon" src="{url(meta.get("png", lg["path"]))}">'
                f'<div class="iname" style="font-size:{int(fs * scale)}px">{esc(name)}</div></div>')
    elif mode == "text" or not meta:
        mark = f'<div class="tname">{esc(lg.get("text") or e["title"])}</div>'
    else:
        flt = {"white": "brightness(0) invert(1)", "invert": "invert(1)", "color": ""}[mode]
        w, h = fit(meta["w"], meta["h"], 230000 * scale ** 2, 1000, 380, meta.get("cov"))
        mark = (f'<img class="logo" src="{url(meta["png"])}" style="filter:{flt} drop-shadow(0 12px 40px rgba(0,0,0,.75));'
                f'width:{w}px;height:{h}px">')
    badge = f'<div class="badge">{esc(e["badge"])}</div>' if e.get("badge") else ""
    glow = (f".tint{{background:radial-gradient(52% 62% at 50% 50%,{tint}66 0%,{tint}26 48%,{tint}00 78%)}}"
            f".hue{{background:{tint};mix-blend-mode:color;opacity:.32}}") if tint else (
        ".tint{background:radial-gradient(52% 62% at 50% 50%,rgba(170,180,200,.16) 0%,rgba(170,180,200,0) 75%)}"
        ".hue{display:none}")
    return f"""<!doctype html><html><head><meta charset="utf-8"><style>{BASE_CSS}
body{{background:#09090d}}
.wall{{position:absolute;left:50%;top:50%;width:2350px;display:grid;grid-template-columns:repeat(7,1fr);gap:22px;
  transform:translate(-50%,-50%) rotate(-11deg) scale(1.02)}}
.p{{aspect-ratio:2/3;border-radius:14px;background-size:cover;background-position:center;
  filter:saturate(.9) brightness(.6);box-shadow:0 18px 40px rgba(0,0,0,.5)}}
.shade{{background:radial-gradient(58% 64% at 50% 50%,rgba(6,6,9,.82) 0%,rgba(6,6,9,.6) 55%,rgba(6,6,9,.4) 100%)}}
.edge{{background:linear-gradient(0deg,rgba(6,6,9,.65),rgba(6,6,9,0) 32%,rgba(6,6,9,0) 68%,rgba(6,6,9,.55))}}
{glow}
.center{{position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center}}
.logo{{object-fit:contain}}
.iconrow{{display:flex;align-items:center;gap:48px}}
.icon{{width:{int(230 * scale)}px;height:{int(230 * scale)}px;border-radius:24%;box-shadow:0 18px 50px rgba(0,0,0,.6)}}
.iname{{font-weight:800;letter-spacing:-.03em;line-height:1}}
.tname{{font-size:140px;font-weight:800;letter-spacing:-.03em}}
.badge{{margin-top:44px;font-size:46px;font-weight:800;letter-spacing:.4em;text-transform:uppercase;padding:14px 30px 14px 48px;
  border:4px solid rgba(255,255,255,.7);border-radius:999px;color:#fff;background:rgba(0,0,0,.25)}}
</style></head><body>
<div class="wall">{tiles}</div><div class="layer hue"></div><div class="layer shade"></div><div class="layer edge"></div>
<div class="layer tint"></div><div class="noise"></div>
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
