"""Write the Nuvio import files from collections.full.json (after build.py validated and pruned it)."""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# Order of the rows on Home (all pinned above addon catalogs).
HOME_ORDER = [
    "Streaming Services", "Indian Streaming", "Genres", "Franchises & Universes", "Indian Cinema",
    "Moods & Themes", "Directors", "Indian Universes", "Studios", "World Cinema", "Networks",
    "Critics' Picks", "Decades",
]


def main():
    full = json.load(open(os.path.join(HERE, "collections.full.json")))
    by_title = {c["title"]: c for c in full}
    assert set(by_title) == set(HOME_ORDER), set(by_title) ^ set(HOME_ORDER)
    out = []
    for title in HOME_ORDER:
        c = dict(by_title[title])
        c["folders"] = [{k: v for k, v in f.items() if not k.startswith("_")} for f in c["folders"]]
        out.append(c)
    with open(os.path.join(ROOT, "nuvio-collections.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
        f.write("\n")
    with open(os.path.join(ROOT, "nuvio-collections.min.json"), "w") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    folders = sum(len(c["folders"]) for c in out)
    sources = sum(len(f["sources"]) for c in out for f in c["folders"])
    print(f"exported {len(out)} collections, {folders} folders, {sources} sources")


if __name__ == "__main__":
    main()
