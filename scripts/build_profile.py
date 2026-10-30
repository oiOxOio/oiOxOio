#!/usr/bin/env python3
"""Render original, self-contained SVG profile cards from editable local data.

No network access, external fonts, bitmap images, or third-party Python packages.
Run --check to compare all expected cards with their committed versions.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from html import escape
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
SVG_NS = "http://www.w3.org/2000/svg"
PALETTES = {
    "dark": {
        "bg": "#0d1117", "panel": "#121923", "border": "#283341",
        "text": "#e6edf3", "muted": "#9aaabd", "quiet": "#7d8da1",
        "accent": "#7dd3fc", "purple": "#c4b5fd", "green": "#7ee0ba",
        "chip": "#192331", "grid": "#253342", "empty": "#1b2735",
        "dots": ["#173b50", "#20637c", "#3998b5", "#7dd3fc"],
    },
    "light": {
        "bg": "#ffffff", "panel": "#f6f8fc", "border": "#dce4ee",
        "text": "#1f2937", "muted": "#586980", "quiet": "#697b91",
        "accent": "#087ea4", "purple": "#7652bd", "green": "#16805c",
        "chip": "#edf2f8", "grid": "#dfe8f2", "empty": "#edf2f7",
        "dots": ["#c7e9f5", "#8acde5", "#43aacd", "#087ea4"],
    },
}


def text(x, y, value, size=14, fill="text", weight=400, mono=False, **attrs):
    family = "mono" if mono else "sans"
    extra = " ".join(f'{k.replace("_", "-")}="{escape(str(v), quote=True)}"' for k, v in attrs.items())
    return (f'<text x="{x}" y="{y}" class="{family}" font-size="{size}" '
            f'font-weight="{weight}" fill="{escape(str(fill))}" {extra}>{escape(str(value))}</text>')


def label(x, y, value, p, **attrs):
    return text(x, y, value, 11, p["accent"], mono=True, letter_spacing=1.4, **attrs)


def rect(x, y, width, height, fill, stroke="none", radius=12, **attrs):
    extra = " ".join(f'{k.replace("_", "-")}="{escape(str(v), quote=True)}"' for k, v in attrs.items())
    return f'<rect x="{x}" y="{y}" width="{width}" height="{height}" rx="{radius}" fill="{fill}" stroke="{stroke}" {extra}/>'


def line(x1, y1, x2, y2, p):
    return f'<path d="M{x1} {y1}H{x2}" fill="none" stroke="{p["border"]}"/>'


def document(width, height, title, description, body, p, defs=""):
    return (f'<svg xmlns="{SVG_NS}" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            'role="img" aria-labelledby="title desc">\n'
            f'<title id="title">{escape(title)}</title>\n<desc id="desc">{escape(description)}</desc>\n'
            '<defs><style>'
            '.sans{font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","Noto Sans CJK SC","Noto Sans SC","Microsoft YaHei",sans-serif}'
            '.mono{font-family:ui-monospace,SFMono-Regular,Consolas,"DejaVu Sans Mono",monospace}'
            '@keyframes blink{0%,48%{opacity:1}49%,100%{opacity:0}}'
            '.cursor{animation:blink 1.2s step-end infinite}'
            '@media(prefers-reduced-motion:reduce){*{animation:none!important}}'
            '</style>' + defs + '</defs>\n'
            + rect(0.5, 0.5, width-1, height-1, p["bg"], p["border"], 18)
            + '\n' + '\n'.join(body) + '\n</svg>\n')


def pills(items, x, y, p, size=11, height=25):
    body = []
    for item in items:
        width = round(len(item) * size * 0.62 + 22)
        body += [rect(x, y, width, height, p["chip"], p["border"], height/2),
                 text(x+11, y+height/2+size*0.35, item, size, p["muted"], mono=True)]
        x += width+8
    return body


def hero(profile, p, mobile=False):
    width, height = (420, 455) if mobile else (880, 298)
    x = 26 if mobile else 36
    body = ['<rect x="1" y="1" width="99.7%" height="99.3%" rx="18" fill="url(#dots)"/>']
    body += [label(x, 45 if mobile else 51, "HELLO, I'M", p),
             text(x, 95 if mobile else 111, profile["username"], 44 if mobile else 52, p["text"], 700),
             text(x+228 if mobile else x+272, 94 if mobile else 109, profile["display_name"], 12, p["muted"], mono=True),
             rect(x, 109 if mobile else 128, 65, 3, "url(#accent)", radius=1.5),
             text(x, 144 if mobile else 166, profile["role"], 21, p["text"], 600),
             text(x, 175 if mobile else 197, profile["tagline"], 14 if mobile else 15, p["muted"])]
    if not mobile:
        body.append(text(x, 224, profile["intro"], 12.5, p["quiet"]))
    body += pills(profile["hero_tags"], x, 194 if mobile else 246, p, 10.5 if mobile else 11)
    tx, ty, tw, th = (26, 245, 368, 183) if mobile else (524, 39, 320, 220)
    body += [rect(tx, ty, tw, th, p["panel"], p["border"], 13)]
    for i, color in enumerate(["#ff6058", "#febc2e", "#28c840"]):
        body.append(f'<circle cx="{tx+19+15*i}" cy="{ty+20}" r="4.2" fill="{color}"/>')
    body.append(text(tx+tw-17, ty+24, "~/"+profile["username"], 10.5, p["quiet"], mono=True, text_anchor="end"))
    terminal = [("$ whoami", p["accent"]), ("  full-stack developer", p["text"]),
                ("$ cat focus.txt", p["accent"]), ("  "+profile["terminal_focus"], p["muted"]),
                ("$ status", p["accent"]), ("  building + learning", p["muted"])]
    step = 21 if mobile else 26
    for i, (value, color) in enumerate(terminal):
        body.append(text(tx+22, ty+51+i*step, value, 12.2, color, mono=True))
    body.append(rect(tx+181, ty+41+5*step, 7, 13, p["accent"], radius=0, **{"class": "cursor"}))
    defs = (f'<pattern id="dots" width="20" height="20" patternUnits="userSpaceOnUse">'
            f'<circle cx="10" cy="10" r="0.7" fill="{p["grid"]}"/></pattern>'
            f'<linearGradient id="accent"><stop stop-color="{p["accent"]}"/>'
            f'<stop offset="1" stop-color="{p["purple"]}"/></linearGradient>')
    return document(width, height, profile["username"]+" · 全栈开发", profile["tagline"]+profile["intro"], body, p, defs)


def skills(profile, p, mobile=False):
    width = 420 if mobile else 880
    row_step = 61 if mobile else 43
    height = (758 if mobile else 448) + max(0, len(profile["stack"])-2)*row_step
    margin = 24 if mobile else 32
    body = [label(margin, 37 if mobile else 40, "FOCUS & PRACTICE", p)]
    if not mobile:
        body.append(text(848, 40, "BUILD / LEARN / IMPROVE", 10.5, p["quiet"], mono=True, text_anchor="end"))
    for i, focus in enumerate(profile["focus"]):
        x = margin if mobile else margin+(i%2)*416
        y = 59+i*135 if mobile else 63+(i//2)*132
        cardw = 372 if mobile else 400
        body += [rect(x, y, cardw, 120, p["panel"], radius=10),
                 text(x+16, y+25, f'0{i+1}', 10.5, p["accent"], mono=True),
                 text(x+cardw-16, y+25, focus["status"], 10.5, p["quiet"], text_anchor="end"),
                 text(x+16, y+53, focus["title"], 16, p["text"], 600)]
        for j, value in enumerate(focus["lines"]):
            body.append(text(x+16, y+78+21*j, value, 13, p["muted"]))
    sy = 617 if mobile else 345
    body.append(line(margin, sy-22, width-margin, sy-22, p))
    for i, group in enumerate(profile["stack"]):
        gy = sy+i*row_step
        if mobile:
            body.append(label(margin, gy, group["label"], p))
            body += pills(group["items"], margin, gy+12, p, 10.5)
        else:
            body.append(label(margin, gy+10, group["label"], p))
            body += pills(group["items"], 187, gy-7, p, 11)
    body.append(text(margin, height-19, "AI 偏好："+profile["ai_preference"], 11, p["muted"]))
    description = "；".join(f["title"]+"："+"".join(f["lines"]) for f in profile["focus"])
    description += "。技术选择："+"；".join(" / ".join(group["items"]) for group in profile["stack"])
    description += "。AI 偏好："+profile["ai_preference"]
    return document(width, height, "技术方向与开发习惯", description, body, p)


def contributions(profile, p, source):
    original = ET.fromstring(source)
    if original.tag != f"{{{SVG_NS}}}svg":
        raise ValueError("Contribution source is not an SVG")
    viewbox = original.attrib["viewBox"]
    inner = re.sub(r"^\s*<svg\b[^>]*>", "", source, count=1).rsplit("</svg>", 1)[0]
    vars_ = (f'--cb:{p["border"]};--cs:{p["accent"]};--ce:{p["empty"]};--c0:{p["empty"]};'
             + ";".join(f'--c{i+1}:{c}' for i, c in enumerate(p["dots"])))
    inner, changed = re.subn(r":root\{[^}]*\}", ":root{"+vars_+"}", inner, count=1)
    if not changed:
        raise ValueError("Unexpected snake palette: refusing an unthemed output")
    # Keep the animation intact while also supporting SVG viewers that lack
    # CSS custom properties or CSS geometry attributes on rect elements.
    colors = {"--cb": p["border"], "--cs": p["accent"], "--ce": p["empty"], "--c0": p["empty"]}
    colors.update({f"--c{i+1}": color for i, color in enumerate(p["dots"])})
    def resolve_color(match):
        name = match.group(1)
        if name not in colors:
            raise ValueError(f"Unexpected snake color variable: {name}")
        return colors[name]
    inner = re.sub(r"var\((--[\w-]+)\)", resolve_color, inner)
    inner = re.sub(r":root\{[^}]*\}", "", inner, count=1)
    grid_style = re.search(r"\.c\{([^}]+)\}", inner)
    if grid_style is None:
        raise ValueError("Missing snake grid geometry")
    dimensions = {}
    for dimension in ("width", "height"):
        value = re.search(rf"(?:^|;)\s*{dimension}:([\d.]+)px(?:;|$)", grid_style.group(1))
        if value is None:
            raise ValueError(f"Missing snake grid {dimension}")
        dimensions[dimension] = value.group(1)
    def add_grid_geometry(match):
        element = match.group(0)
        classes = re.search(r'\bclass="([^"]*)"', element)
        if classes and "c" in classes.group(1).split():
            for dimension, value in dimensions.items():
                if not re.search(rf'\b{dimension}="', element):
                    element = element[:-2] + f' {dimension}="{value}"/>'
        return element
    inner = re.sub(r"<rect\b[^>]*/>", add_grid_geometry, inner)
    inner += '<style>@media(prefers-reduced-motion:reduce){*{animation:none!important}}</style>'
    body = [label(32, 40, "KEEP BUILDING", p),
            text(848, 40, "A LITTLE PROGRESS, EVERY DAY", 10.5, p["quiet"], mono=True, text_anchor="end"),
            f'<svg x="28" y="58" width="824" height="180" viewBox="{escape(viewbox, quote=True)}">{inner}</svg>']
    return document(880, 250, profile["username"]+" 的 GitHub 贡献图", "贡献日历贪吃蛇动画，来自 GitHub 个人主页贡献数据。", body, p)


def language_rows(stats):
    entries = sorted(stats.get("languages", []), key=lambda item: item["bytes"], reverse=True)
    total = sum(item["bytes"] for item in entries)
    if not total:
        return []
    top = entries[:4]
    rest = sum(item["bytes"] for item in entries[4:])
    if rest:
        top.append({"name": "Other", "bytes": rest, "color": "#8b98aa"})
    return [{**item, "percent": item["bytes"] / total * 100} for item in top]


def statistics(profile, stats, p, mobile=False):
    width, height = (420, 640) if mobile else (880, 350)
    margin = 24 if mobile else 32
    body = [label(margin, 40, "GITHUB / PUBLIC SNAPSHOT", p)]
    date = stats["updated_at"][:10]
    if not mobile:
        body.append(text(width-margin, 40, date, 10.5, p["quiet"], mono=True, text_anchor="end"))
    metrics = [("repositories", "公开仓库", "OWNED · NON-FORK"),
               ("stars", "获得 Stars", "PUBLIC · NON-FORK"),
               ("pull_requests", "公开 Pull Requests", "AUTHORED · ALL TIME"),
               ("merged_pull_requests", "已合并 PR", "AUTHORED · ALL TIME")]
    for i, (key, caption, note) in enumerate(metrics):
        mx = margin+(i%2)*192 if mobile else margin+i*208
        my = 62+(i//2)*118 if mobile else 64
        mw = 180 if mobile else 192
        body += [rect(mx, my, mw, 104, p["panel"], radius=10),
                 text(mx+16, my+39, f'{stats[key]:,}', 30, p["accent"] if i%2==0 else p["purple"], 650),
                 text(mx+16, my+64, caption, 13, p["text"]),
                 text(mx+16, my+86, note, 8.5, p["quiet"], mono=True)]
    divy = 305 if mobile else 189
    body.append(line(margin, divy, width-margin, divy, p))
    rows = language_rows(stats)
    if rows:
        body += [label(margin, divy+29, "LANGUAGES", p),
                 text(margin, divy+50, "公开非 Fork 仓库 · 按代码字节统计", 10.5, p["quiet"])]
        sx, by, barw = margin, divy+64, 372 if mobile else 376
        body.append(rect(sx, by, barw, 7, p["chip"], radius=3.5))
        body.append(f'<clipPath id="lang-clip"><rect x="{sx}" y="{by}" width="{barw}" height="7" rx="3.5"/></clipPath>')
        for row in rows:
            part = barw*row["percent"]/100
            color = row.get("color") or p["accent"]
            body.append(rect(round(sx, 3), by, round(part, 3), 7, color, radius=0, clip_path="url(#lang-clip)"))
            sx += part
        for i, row in enumerate(rows):
            lx, ly = margin+(i%2)*(192 if mobile else 190), by+28+(i//2)*21
            name = row["name"]
            short_name = name if len(name) <= 18 else name[:17]+"…"
            body.append(f'<g><title>{escape(name)} {row["percent"]:.1f}%</title>')
            body.append(f'<circle cx="{lx+3}" cy="{ly-4}" r="3" fill="{row.get("color") or p["accent"]}"/>')
            body.append(text(lx+13, ly, f'{short_name} {row["percent"]:.1f}%', 11, p["muted"]))
            body.append('</g>')
    else:
        body.append(label(margin, divy+29, "LANGUAGES", p))
        body.append(text(margin, divy+58, "语言数据暂未提供。", 13, p["muted"]))
    px, py = (margin, 493) if mobile else (464, divy+29)
    body.append(label(px, py, "WORKING PRINCIPLES", p))
    for i, principle in enumerate(profile["principles"]):
        yy = py+29+i*28
        body += [text(px, yy, "0"+str(i+1), 10, p["accent"], mono=True),
                 text(px+30, yy, principle, 13, p["muted"])]
    if mobile:
        body.append(text(width-margin, height-17, "UPDATED "+date, 9, p["quiet"], mono=True, text_anchor="end"))
    else:
        body.append(text(margin, height-15, "以 GitHub 公开数据为准 · 私有项目不计入此统计", 10, p["quiet"]))
    description = (f'公开非 Fork 仓库 {stats["repositories"]} 个，获得 {stats["stars"]} Stars，'
                   f'累计创建公开 PR {stats["pull_requests"]} 个，其中 {stats["merged_pull_requests"]} 个已合并。'
                   f'快照日期 {date}，私有项目不计入统计。')
    return document(width, height, "GitHub 公开数据", description, body, p)


def expected_assets():
    profile = json.loads((ROOT / "profile.json").read_text(encoding="utf-8"))
    stats = json.loads((ASSETS / "stats.json").read_text(encoding="utf-8"))
    if stats["username"].lower() != profile["username"].lower():
        raise ValueError("Profile and statistics usernames do not match")
    for key in ("repositories", "stars", "pull_requests", "merged_pull_requests"):
        if type(stats[key]) is not int or stats[key] < 0:
            raise ValueError(f"Invalid statistic: {key}")
    if stats["merged_pull_requests"] > stats["pull_requests"]:
        raise ValueError("Merged PR count exceeds authored PR count")
    source = (ROOT / "resource/github-contribution-grid-snake.svg").read_text(encoding="utf-8")
    assets = {}
    for theme, p in PALETTES.items():
        for mobile in (False, True):
            suffix = f'{theme}{"-mobile" if mobile else ""}.svg'
            assets["hero-"+suffix] = hero(profile, p, mobile)
            assets["skills-"+suffix] = skills(profile, p, mobile)
            assets["stats-"+suffix] = statistics(profile, stats, p, mobile)
        assets[f"contributions-{theme}.svg"] = contributions(profile, p, source)
    for name, content in assets.items():
        root = ET.fromstring(content)
        if root.tag != f"{{{SVG_NS}}}svg":
            raise ValueError(f"{name}: invalid SVG root")
        for element in root.iter():
            if element.tag.rsplit("}", 1)[-1] in {"script", "foreignObject", "image"}:
                raise ValueError(f"{name}: unexpected executable or external content")
        if re.search(r"\b(?:NaN|Infinity|undefined)\b", content):
            raise ValueError(f"{name}: invalid numeric output")
    return assets


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if any rendered asset is missing or stale")
    args = parser.parse_args()
    outputs = expected_assets()
    if args.check:
        stale = [name for name, content in outputs.items()
                 if not (ASSETS/name).is_file() or (ASSETS/name).read_text(encoding="utf-8") != content]
        if stale:
            print("Missing or stale cards: "+", ".join(stale), file=sys.stderr)
            return 1
        print(f"Verified {len(outputs)} profile cards.")
        return 0
    ASSETS.mkdir(parents=True, exist_ok=True)
    for name, content in outputs.items():
        target = ASSETS/name
        tmp = target.with_suffix(".tmp")
        tmp.write_text(content, encoding="utf-8")
        tmp.replace(target)
    print(f"Rendered {len(outputs)} profile cards.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
