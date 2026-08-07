#!/usr/bin/env python3
import html
import json
import os
import subprocess
import sys
import urllib.error
import urllib.request

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
API = "https://api.github.com"
HEADERS = {
    "Accept": "application/vnd.github+json",
    "User-Agent": "top-langs-generator",
}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"


def api_get(path):
    req = urllib.request.Request(f"{API}{path}", headers=HEADERS)
    with urllib.request.urlopen(req, timeout=60) as resp:
        return json.loads(resp.read().decode())


def api_get_all(path):
    items = []
    page = 1
    while True:
        sep = "&" if "?" in path else "?"
        batch = api_get(f"{path}{sep}per_page=100&page={page}")
        if not batch:
            break
        items.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return items


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "top-langs.svg"
    try:
        repos = api_get_all(
            "/user/repos?affiliation=owner,collaborator,organization_member&sort=updated"
        )
    except urllib.error.HTTPError:
        # fallback public-only
        user = os.environ.get("GITHUB_ACTOR", "harshvardhanrajdan")
        repos = api_get_all(f"/users/{user}/repos?type=owner&sort=updated")

    totals = {}
    for r in repos:
        if r.get("fork"):
            continue
        full = r["full_name"]
        try:
            langs = api_get(f"/repos/{full}/languages")
        except urllib.error.HTTPError:
            continue
        for lang, nbytes in langs.items():
            totals[lang] = totals.get(lang, 0) + nbytes

    if not totals:
        raise SystemExit("no language data")

    ranked = sorted(totals.items(), key=lambda x: -x[1])[:10]
    total = sum(v for _, v in ranked)

    bg, title, text, bar_track = "#141321", "#fe428e", "#a9fef7", "#2a2a40"
    palette = [
        "#fe428e", "#f8d847", "#a9fef7", "#c792ea", "#82aaff",
        "#c3e88d", "#ffcb6b", "#f78c6c", "#89ddff", "#c792ea",
    ]

    rows = []
    y0, row_h = 50, 22
    for i, (lang, nbytes) in enumerate(ranked):
        pct = nbytes / total * 100
        bar_w = 200 * (nbytes / total)
        color = palette[i % len(palette)]
        y = y0 + i * row_h
        name = html.escape(lang)
        rows.append(
            f'<circle cx="20" cy="{y}" r="5" fill="{color}"/>'
            f'<text x="32" y="{y + 4}" class="lang">{name}</text>'
            f'<rect x="150" y="{y - 5}" width="200" height="10" rx="5" fill="{bar_track}"/>'
            f'<rect x="150" y="{y - 5}" width="{bar_w:.2f}" height="10" rx="5" fill="{color}"/>'
            f'<text x="360" y="{y + 4}" class="pct" text-anchor="end">{pct:.1f}%</text>'
        )

    height = y0 + len(ranked) * row_h + 20
    width = 380
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img">
  <title>Most Used Languages</title>
  <style>
    .title {{ font: 600 16px 'Segoe UI', Ubuntu, Sans-Serif; fill: {title}; }}
    .lang {{ font: 400 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: {text}; }}
    .pct {{ font: 600 12px 'Segoe UI', Ubuntu, Sans-Serif; fill: {text}; }}
  </style>
  <rect width="100%" height="100%" rx="8" fill="{bg}"/>
  <text x="20" y="28" class="title">Most Used Languages</text>
  {"".join(rows)}
</svg>
'''
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    print(f"wrote {out_path} from {len(repos)} repos; top={ranked}")


if __name__ == "__main__":
    main()
