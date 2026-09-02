#!/usr/bin/env python3
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone

TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or ""
USER = (
    os.environ.get("GITHUB_USERNAME")
    or os.environ.get("GITHUB_REPOSITORY_OWNER")
    or "harshvardhanrajdan"
)
DAYS = 31
WIDTH, HEIGHT = 850, 320
PAD_L, PAD_R, PAD_T, PAD_B = 48, 20, 52, 38

# radical theme (github-readme-activity-graph)
BG = "#141321"
TITLE = "#a9fef7"
TEXT = "#a9fef7"
LINE = "#fe428e"
POINT = "#f8d847"
AREA = "#fe428e"
GRID = "#2a2a40"


def graphql(query, variables):
    body = json.dumps({"query": query, "variables": variables}).encode()
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "User-Agent": "activity-graph-generator",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    req = urllib.request.Request("https://api.github.com/graphql", data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=60) as resp:
        payload = json.loads(resp.read().decode())
    if payload.get("errors"):
        raise RuntimeError(payload["errors"])
    return payload["data"]


def fetch_days():
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=DAYS - 1)
    query = """
    query($login: String!, $from: DateTime!, $to: DateTime!) {
      user(login: $login) {
        contributionsCollection(from: $from, to: $to) {
          contributionCalendar {
            weeks {
              contributionDays { date contributionCount }
            }
          }
        }
      }
    }
    """
    data = graphql(
        query,
        {
            "login": USER,
            "from": start.replace(hour=0, minute=0, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        },
    )
    user = data.get("user")
    if not user:
        raise SystemExit(f"user not found: {USER}")
    days = []
    for week in user["contributionsCollection"]["contributionCalendar"]["weeks"]:
        days.extend(week["contributionDays"])
    days.sort(key=lambda d: d["date"])
    return days[-DAYS:]


def nice_max(value):
    if value <= 0:
        return 1
    for step in (1, 2, 4, 5, 8, 10, 15, 20, 25, 30, 40, 50, 75, 100, 150, 200, 250, 500, 1000):
        if value <= step:
            return step
    return ((value + 9) // 10) * 10


def catmull_rom_path(points, y_min, y_max):
    if len(points) == 1:
        x, y = points[0]
        return f"M{x:.2f},{y:.2f}"
    if len(points) == 2:
        (x0, y0), (x1, y1) = points
        return f"M{x0:.2f},{y0:.2f} L{x1:.2f},{y1:.2f}"

    def clamp_y(y):
        return min(y_max, max(y_min, y))

    pts = [points[0]] + points + [points[-1]]
    parts = [f"M{points[0][0]:.2f},{points[0][1]:.2f}"]
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        c1x = p1[0] + (p2[0] - p0[0]) / 6
        c1y = clamp_y(p1[1] + (p2[1] - p0[1]) / 6)
        c2x = p2[0] - (p3[0] - p1[0]) / 6
        c2y = clamp_y(p2[1] - (p3[1] - p1[1]) / 6)
        parts.append(f"C{c1x:.2f},{c1y:.2f} {c2x:.2f},{c2y:.2f} {p2[0]:.2f},{p2[1]:.2f}")
    return " ".join(parts)


def label_for(date_str):
    dt = datetime.strptime(date_str, "%Y-%m-%d")
    return dt.strftime("%b %d")


def render(days):
    counts = [d["contributionCount"] for d in days]
    ymax = nice_max(max(counts) if counts else 0)
    chart_w = WIDTH - PAD_L - PAD_R
    chart_h = HEIGHT - PAD_T - PAD_B
    n = max(len(days) - 1, 1)

    def xy(i, count):
        x = PAD_L + chart_w * i / n
        y = PAD_T + chart_h * (1 - count / ymax)
        return x, y

    points = [xy(i, c) for i, c in enumerate(counts)]
    line = catmull_rom_path(points, PAD_T, PAD_T + chart_h)
    bottom = PAD_T + chart_h
    area = (
        f"{line} L{points[-1][0]:.2f},{bottom:.2f} L{points[0][0]:.2f},{bottom:.2f} Z"
        if points
        else ""
    )

    ticks = 4
    grid = []
    for i in range(ticks + 1):
        val = ymax * i / ticks
        y = PAD_T + chart_h * (1 - i / ticks)
        grid.append(
            f'<line x1="{PAD_L}" y1="{y:.2f}" x2="{WIDTH - PAD_R}" y2="{y:.2f}" stroke="{GRID}" stroke-width="1"/>'
            f'<text x="{PAD_L - 8}" y="{y + 4:.2f}" class="axis" text-anchor="end">{int(round(val))}</text>'
        )

    xlabel_idxs = sorted(set([0, len(days) // 4, len(days) // 2, (3 * len(days)) // 4, len(days) - 1]))
    xlabels = []
    for i in xlabel_idxs:
        x, _ = xy(i, 0)
        xlabels.append(
            f'<text x="{x:.2f}" y="{HEIGHT - 12}" class="axis" text-anchor="middle">{label_for(days[i]["date"])}</text>'
        )

    dots = [
        f'<circle cx="{x:.2f}" cy="{y:.2f}" r="3.2" fill="{POINT}" stroke="{BG}" stroke-width="1"/>'
        for x, y in points
    ]

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" viewBox="0 0 {WIDTH} {HEIGHT}" role="img">
  <title>Contribution graph</title>
  <style>
    .title {{ font: 600 18px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TITLE}; }}
    .axis {{ font: 400 11px 'Segoe UI', Ubuntu, Sans-Serif; fill: {TEXT}; }}
  </style>
  <rect width="100%" height="100%" rx="8" fill="{BG}"/>
  <text x="{WIDTH / 2:.0f}" y="28" class="title" text-anchor="middle">Contribution graph</text>
  {''.join(grid)}
  <path d="{area}" fill="{AREA}" fill-opacity="0.28"/>
  <path d="{line}" fill="none" stroke="{LINE}" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
  {''.join(dots)}
  {''.join(xlabels)}
</svg>
'''


def main():
    out_path = sys.argv[1] if len(sys.argv) > 1 else "activity-graph.svg"
    try:
        days = fetch_days()
    except urllib.error.HTTPError as err:
        raise SystemExit(f"github api error: {err.code} {err.reason}") from err
    if not days:
        raise SystemExit("no contribution days returned")
    svg = render(days)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(svg)
    total = sum(d["contributionCount"] for d in days)
    print(f"wrote {out_path} days={len(days)} total={total} range={days[0]['date']}..{days[-1]['date']}")


if __name__ == "__main__":
    main()
