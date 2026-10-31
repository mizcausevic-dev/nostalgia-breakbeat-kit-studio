"""Kit map. Static HTML, no external assets. Not a storefront."""

from __future__ import annotations

import json
from pathlib import Path


def write_collection_page(builds: dict, delivery: dict, path: Path) -> None:
    cards = []
    rendered = delivery.get("kits") or {}
    for kit_id, build in builds.items():
        spec = build["spec"]
        files = {item.get("variant"): item for item in rendered.get(kit_id, {}).get("files", []) if item.get("kind") == "wav"}
        # Variant keys collide across roles. Pick by role and variant.
        demo = _find(rendered, kit_id, "demo", "Main")
        core = _find(rendered, kit_id, "core", "V01")
        bass = _find(rendered, kit_id, "bass", "V01")
        cells = []
        for region_index, region in enumerate(build["arrangement"]["sections"]):
            for bar in range(region["start_bar"], region["end_bar"]):
                cells.append(
                    f'<i class="sec sec-{region_index}" title="Bar {bar + 1}: {region["name"]}"></i>'
                )
        harmony = []
        for region in build["arrangement"]["harmony"]:
            harmony.append(
                f'<li>Bars {region["start_bar"] + 1}–{region["end_bar"]}: root class {region["root_pc"]} {region["quality"]} ({region["function"]})</li>'
            )
        players = []
        for label, record in (("Demo mix", demo), ("Core break V01", core), ("Bass V01", bass)):
            if record:
                href = "../" + record["path"]
                players.append(f'<label>{label}<audio controls preload="none" src="{href}"></audio></label>')
            else:
                players.append(f"<label>{label}<span>Not rendered in this delivery.</span></label>")
        cards.append(
            f"""
            <article class="kit" id="{kit_id}">
              <header>
                <p class="kicker">{spec["direction"]}</p>
                <h2>{kit_id} {spec["name"]}</h2>
                <p class="meta">{spec["bpm"]} BPM requested · {spec["key_label"]} · 4/4 · 64 bars</p>
              </header>
              <div class="timeline" aria-label="64 bar arrangement">{''.join(cells)}</div>
              <ol class="regions">{''.join(f'<li>Bars {region["start_bar"] + 1}–{region["end_bar"]}: {region["name"]}</li>' for region in build["arrangement"]["sections"])}</ol>
              <h3>Harmony</h3>
              <ol>{''.join(harmony)}</ol>
              <div class="players">{''.join(players)}</div>
            </article>
            """
        )
    html = _HTML.replace("__CARDS__", "\n".join(cards)).replace("__COUNT__", str(len(builds)))
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(html, encoding="utf-8")
    # Keep a machine copy of the section list beside the page for the validator.
    path.with_suffix(".json").write_text(
        json.dumps({"kits": list(builds), "complete": bool(delivery.get("complete"))}, indent=2) + "\n",
        encoding="utf-8",
    )


def _find(rendered: dict, kit_id: str, role: str, variant: str) -> dict | None:
    kit = rendered.get(kit_id) or {}
    for item in kit.get("files") or []:
        if item.get("kind") == "wav" and item.get("role") == role and item.get("variant") == variant:
            return item
    return None


_HTML = r"""<!DOCTYPE html>
<html lang="en" data-theme="cosmic" data-mode="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Nostalgia kit map</title>
<style>
:root {
  --bg:#07060f; --bg2:#100c18; --panel:#171327; --text:#f4f1ea; --muted:#b7b0c9;
  --accent:#66fcf1; --accent2:#8b5cff; --line:rgba(255,255,255,.12);
  --s0:#66fcf1; --s1:#8b5cff; --s2:#d6ff3f; --s3:#ff2d55; --s4:#2fd57a; --s5:#00e0ff; --s6:#f4f1ea; --s7:#45a29e;
  --font:ui-sans-serif, system-ui, sans-serif; --mono:ui-monospace, monospace;
  --radius:16px; --shadow:0 18px 50px rgba(0,0,0,.35);
}
* { box-sizing:border-box; }
body { margin:0; background:var(--bg); color:var(--text); font-family:var(--font); }
body::before { content:""; position:fixed; inset:0; pointer-events:none;
  background-image:linear-gradient(var(--line) 1px, transparent 1px), linear-gradient(90deg, var(--line) 1px, transparent 1px);
  background-size:44px 44px; opacity:.35; }
header.top, main { position:relative; }
header.top { display:flex; flex-wrap:wrap; gap:16px; justify-content:space-between; align-items:end; padding:28px 6vw 8px; }
h1 { font-size:clamp(2.2rem, 6vw, 4.5rem); line-height:.9; margin:0; letter-spacing:-.04em; }
.lede { max-width:62ch; color:var(--muted); }
.controls { display:flex; flex-wrap:wrap; gap:8px; }
button, select { background:var(--panel); color:var(--text); border:1px solid var(--line); border-radius:999px; padding:8px 12px; font:inherit; }
button[aria-pressed="true"] { outline:2px solid var(--accent); }
main { padding:12px 6vw 64px; display:grid; gap:18px; }
.kit { background:var(--panel); border:1px solid var(--line); border-radius:var(--radius); box-shadow:var(--shadow); padding:18px; }
.kicker { color:var(--accent); text-transform:uppercase; letter-spacing:.14em; font-size:.75rem; margin:0; }
.meta, .kit li { color:var(--muted); }
.timeline { display:grid; grid-template-columns:repeat(64, 1fr); gap:2px; margin:12px 0; }
.sec { display:block; height:28px; border-radius:3px; }
.sec-0{background:var(--s0)} .sec-1{background:var(--s1)} .sec-2{background:var(--s2)} .sec-3{background:var(--s3)}
.sec-4{background:var(--s4)} .sec-5{background:var(--s5)} .sec-6{background:var(--s6)} .sec-7{background:var(--s7)}
.players { display:grid; gap:8px; }
audio { width:min(100%, 420px); }
@media (max-width:720px) { .timeline { grid-template-columns:repeat(32, 1fr); } }
@media (prefers-reduced-motion: reduce) { * { transition:none !important; animation:none !important; } }
</style>
</head>
<body>
<header class="top">
  <div>
    <p class="kicker">Construction kits</p>
    <h1>Nostalgia</h1>
    <p class="lede">Eight original breakbeat sessions for a DAW. Each kit is one tempo, one meter, and a 64-bar demonstration. The page is a map of those assets. It is not a finished master and it does not collect listeners.</p>
  </div>
  <div class="controls">
    <select id="theme" aria-label="Theme">
      <option value="bento">Bento Grid</option>
      <option value="cosmic" selected>Cosmic Cyber</option>
      <option value="swiss">Swiss Architect</option>
      <option value="aqua">Aqua Web 2.0</option>
      <option value="brutal">Pop Brutalist</option>
      <option value="steel">Steel Tactical</option>
      <option value="parchment">Parchment</option>
    </select>
    <button type="button" id="mode" aria-pressed="true">Dark</button>
  </div>
</header>
<main>
__CARDS__
</main>
<script>
const THEMES = {
  bento: { dark:["#101114","#1c1f27","#f5f7fb","#9aa3b2","#7CFF6B","#6B8CFF"], light:["#f4f6f8","#ffffff","#16181d","#5c6570","#0b7a3b","#2746c7"] },
  cosmic:{ dark:["#07060f","#171327","#f4f1ea","#b7b0c9","#66fcf1","#8b5cff"], light:["#f6f3ff","#ffffff","#1b1430","#5c5670","#0e7c86","#5b35d5"] },
  swiss:{ dark:["#111111","#1a1a1a","#f2f2f2","#bdbdbd","#ff3b30","#f2f2f2"], light:["#f7f7f5","#ffffff","#111111","#5f5f5f","#d90429","#111111"] },
  aqua: { dark:["#041820","#0b2c36","#e7fff8","#9fd8cc","#7dffe1","#3d8bfd"], light:["#e7fbf6","#ffffff","#08343c","#3d6b66","#0a8f7a","#1554d6"] },
  brutal:{ dark:["#140806","#2a1218","#fff4ea","#e7b8a8","#ff4d6d","#ffe66d"], light:["#fff1e6","#fffaf5","#1a0b10","#7a4b3a","#e10600","#111111"] },
  steel:{ dark:["#0d1110","#1a2420","#e6efe9","#9aab9f","#b6f25c","#d0d6d2"], light:["#eef2ef","#f8faf8","#121614","#4d5a52","#3d6b12","#1c1c1c"] },
  parchment:{ dark:["#1c1610","#2a241c","#f3e6d0","#cbbba2","#e2b15a","#8c4a32"], light:["#f3e6d0","#fff8ec","#2a2118","#6d5c48","#8c3f22","#2f5d50"] }
};
const root = document.documentElement;
const themeEl = document.getElementById("theme");
const modeEl = document.getElementById("mode");
function apply(theme, mode) {
  const row = THEMES[theme][mode];
  const keys = ["--bg","--panel","--text","--muted","--accent","--accent2"];
  keys.forEach((key, index) => root.style.setProperty(key, row[index]));
  root.dataset.theme = theme;
  root.dataset.mode = mode;
  localStorage.setItem("nostalgia-theme", theme);
  localStorage.setItem("nostalgia-mode", mode);
  modeEl.textContent = mode === "dark" ? "Dark" : "Light";
  modeEl.setAttribute("aria-pressed", mode === "dark" ? "true" : "false");
}
themeEl.addEventListener("change", () => apply(themeEl.value, root.dataset.mode || "dark"));
modeEl.addEventListener("click", () => apply(themeEl.value, (root.dataset.mode === "dark") ? "light" : "dark"));
const savedTheme = localStorage.getItem("nostalgia-theme");
const savedMode = localStorage.getItem("nostalgia-mode");
if (savedTheme && THEMES[savedTheme]) themeEl.value = savedTheme;
apply(themeEl.value, savedMode === "light" ? "light" : "dark");
</script>
</body>
</html>
"""
