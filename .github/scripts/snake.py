"""Contribution snake that sweeps the graph column by column without ever leaving it.

Usage: GITHUB_TOKEN=... GITHUB_REPOSITORY_OWNER=... python snake.py <out_dir>
Writes snake-dark.svg and snake-light.svg (SMIL animation, no JS).
"""
import json
import os
import sys
import urllib.request
from pathlib import Path

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { weeks { contributionDays { weekday contributionLevel } } } } } }"""
LEVELS = ["NONE", "FIRST_QUARTILE", "SECOND_QUARTILE", "THIRD_QUARTILE", "FOURTH_QUARTILE"]

# Cipher palette: blue snake eating gold coins. Dots go from empty to busiest day.
THEMES = {
    "dark": ("#4A86E8", ["#161b22", "#5c4a24", "#8a6a2c", "#c09341", "#e5b95c"]),
    "light": ("#2457B8", ["#ebedf0", "#f3e3b8", "#e5c77a", "#c99a3d", "#a8782a"]),
}
PITCH, DOT, PAD = 16, 12, 4
STEP, PAUSE, LENGTH = 0.05, 2.0, 5  # seconds per cell, pause at the end, segments


def fetch(login, token):
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}"},
    )
    weeks = json.load(urllib.request.urlopen(req))["data"]["user"]["contributionsCollection"][
        "contributionCalendar"]["weeks"]
    cells = {(x, d["weekday"]): LEVELS.index(d["contributionLevel"])
             for x, w in enumerate(weeks) for d in w["contributionDays"]}
    return cells, len(weeks)


def render(cells, cols, snake, dots):
    # Down the even columns, up the odd ones: every cell is visited once, in order.
    path = [(x, y if x % 2 == 0 else 6 - y) for x in range(cols) for y in range(7)]
    while path[0] not in cells:  # first and current weeks are partial
        path.pop(0)
    while path[-1] not in cells:
        path.pop()
    dur = STEP * (len(path) - 1) + PAUSE
    end = STEP * (len(path) - 1) / dur  # fraction of the loop spent moving
    c = lambda v: PAD + v * PITCH + PITCH / 2  # noqa: E731 - cell centre
    w, h = 2 * PAD + cols * PITCH, 2 * PAD + 7 * PITCH
    loop = f'dur="{dur:.2f}s" repeatCount="indefinite"'

    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">']
    for i, (x, y) in enumerate(path):
        if (x, y) not in cells:
            continue
        lvl = cells[x, y]
        rect = f'<rect x="{c(x) - DOT / 2}" y="{c(y) - DOT / 2}" width="{DOT}" height="{DOT}" rx="2" fill="{dots[lvl]}"'
        if lvl:  # eaten when the head reaches it, back at the start of the next loop
            rect += (f'><animate attributeName="fill" values="{dots[lvl]};{dots[0]}" '
                     f'keyTimes="0;{i * STEP / dur:.5f}" calcMode="discrete" {loop}/></rect>')
        else:
            rect += "/>"
        out.append(rect)

    d = "M" + " L".join(f"{c(x)} {c(y)}" for x, y in path)
    for s in range(LENGTH):  # each segment replays the head's path one cell later
        size = DOT - s * 1.5
        begin = f'begin="{s * STEP:.2f}s"'
        out.append(
            f'<rect x="{-size / 2}" y="{-size / 2}" width="{size}" height="{size}" rx="{size / 3:.1f}" '
            f'fill="{snake}" opacity="0">'
            f'<animate attributeName="opacity" values="1;0" keyTimes="0;{end:.5f}" calcMode="discrete" {begin} {loop}/>'
            f'<animateMotion path="{d}" keyPoints="0;1;1" keyTimes="0;{end:.5f};1" calcMode="linear" {begin} {loop}/>'
            f"</rect>")
    out.append("</svg>")
    return "\n".join(out)


def main():
    out_dir = Path(sys.argv[1])
    out_dir.mkdir(parents=True, exist_ok=True)
    cells, cols = fetch(os.environ["GITHUB_REPOSITORY_OWNER"], os.environ["GITHUB_TOKEN"])
    for name, (snake, dots) in THEMES.items():
        (out_dir / f"snake-{name}.svg").write_text(render(cells, cols, snake, dots), encoding="utf-8")
    print(f"{cols} weeks, {sum(1 for v in cells.values() if v)} active days")


if __name__ == "__main__":
    main()
