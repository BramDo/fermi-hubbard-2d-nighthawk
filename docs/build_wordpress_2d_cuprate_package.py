from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
SITE = "https://edukaizen.nl"
SRC = ROOT / "output" / "wordpress_2d_cuprate_series" / "en_md"
OUT = ROOT / "output" / "wordpress_2d_cuprate_series" / "wp_package"
SERIES_SLUG = "fermi-hubbard-2d-cuprate-series"
SERIES_URL = f"{SITE}/{SERIES_SLUG}/"
FIRST_SERIES_URL = f"{SITE}/fermi-hubbard-quantum-simulation-project/"


def parse_front_matter(path: Path) -> tuple[dict[str, Any], list[str]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0].strip() != "---":
        return {}, lines
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}, lines
    meta: dict[str, Any] = {}
    key: str | None = None
    for line in lines[1:end]:
        if not line.strip():
            continue
        if line.startswith("  - ") and key:
            meta.setdefault(key, []).append(line[4:].strip())
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            elif value.isdigit():
                meta[key] = int(value)
                continue
            elif value == "":
                meta[key] = []
                continue
            meta[key] = value
    return meta, lines[end + 1 :]


def article_url(slug: str) -> str:
    return f"{SITE}/{slug}/"


def render_inline(text: str) -> str:
    pattern = re.compile(r"`([^`]+)`|\[([^\]]+)\]\((https?://[^)]+)\)")
    out: list[str] = []
    pos = 0
    for match in pattern.finditer(text):
        out.append(html.escape(text[pos : match.start()]))
        if match.group(1) is not None:
            out.append(f"<code>{html.escape(match.group(1))}</code>")
        else:
            label = html.escape(match.group(2))
            url = html.escape(match.group(3), quote=True)
            out.append(f'<a href="{url}">{label}</a>')
        pos = match.end()
    out.append(html.escape(text[pos:]))
    return "".join(out)


def split_table_row(line: str) -> list[str]:
    text = line.strip()
    if text.startswith("|"):
        text = text[1:]
    if text.endswith("|"):
        text = text[:-1]
    return [cell.strip() for cell in text.split("|")]


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell or "") for cell in cells)


def render_table(lines: list[str]) -> str:
    header = split_table_row(lines[0])
    rows = [split_table_row(line) for line in lines[2:]]
    out = ["<table>\n<thead><tr>"]
    out.extend(f"<th>{render_inline(cell)}</th>" for cell in header)
    out.append("</tr></thead>\n<tbody>\n")
    for row in rows:
        out.append("<tr>")
        for cell in row:
            out.append(f"<td>{render_inline(cell)}</td>")
        out.append("</tr>\n")
    out.append("</tbody>\n</table>\n")
    return "".join(out)


def render_list(lines: list[str], ordered: bool) -> str:
    tag = "ol" if ordered else "ul"
    marker = re.compile(r"^\s*(?:-\s+|\d+\.\s+)")
    out = [f"<{tag}>\n"]
    for line in lines:
        item = marker.sub("", line).strip()
        out.append(f"<li>{render_inline(item)}</li>\n")
    out.append(f"</{tag}>\n")
    return "".join(out)


def render_markdown(lines: list[str], *, skip_h1: bool = True) -> str:
    out: list[str] = []
    i = 0
    if skip_h1:
        while i < len(lines) and not lines[i].strip():
            i += 1
        if i < len(lines) and lines[i].startswith("# "):
            i += 1
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue
        if stripped.startswith("```"):
            code: list[str] = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            out.append(f"<pre><code>{html.escape(chr(10).join(code))}</code></pre>\n")
            continue
        if stripped.startswith("[latex"):
            shortcode = [stripped]
            i += 1
            while i < len(lines) and "[/latex]" not in lines[i]:
                shortcode.append(lines[i])
                i += 1
            if i < len(lines):
                shortcode.append(lines[i].strip())
                i += 1
            out.append("\n".join(shortcode) + "\n")
            continue
        if stripped.startswith("|") and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            table_lines = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(render_table(table_lines))
            continue
        heading = re.match(r"^(#{2,6})\s+(.+)$", stripped)
        if heading:
            level = min(len(heading.group(1)), 4)
            out.append(f"<h{level}>{render_inline(heading.group(2))}</h{level}>\n")
            i += 1
            continue
        if re.match(r"^\s*-\s+", line):
            list_lines: list[str] = []
            while i < len(lines) and re.match(r"^\s*-\s+", lines[i]):
                list_lines.append(lines[i])
                i += 1
            out.append(render_list(list_lines, ordered=False))
            continue
        if re.match(r"^\s*\d+\.\s+", line):
            list_lines = []
            while i < len(lines) and re.match(r"^\s*\d+\.\s+", lines[i]):
                list_lines.append(lines[i])
                i += 1
            out.append(render_list(list_lines, ordered=True))
            continue
        para = [stripped]
        i += 1
        while i < len(lines):
            nxt = lines[i].strip()
            if not nxt or nxt.startswith("#") or nxt.startswith("|") or nxt.startswith("```"):
                break
            if re.match(r"^\s*(?:-|\d+\.)\s+", lines[i]):
                break
            para.append(nxt)
            i += 1
        out.append(f"<p>{render_inline(' '.join(para))}</p>\n")
    return "".join(out)


def nav_html(part: int, articles: list[dict[str, Any]]) -> str:
    links = [
        "<strong>English</strong>",
        f'<a href="{SERIES_URL}">2D project page</a>',
        f'<a href="{FIRST_SERIES_URL}">1D project page</a>',
    ]
    if part > 1:
        prev = articles[part - 2]
        links.append(f'<a href="{article_url(prev["slug"])}">Previous</a>')
    if part < len(articles):
        nxt = articles[part]
        links.append(f'<a href="{article_url(nxt["slug"])}">Next</a>')
    return (
        '<nav class="fh-series-nav" style="margin:1rem 0;padding:.75rem 0;'
        'border-top:1px solid #ddd;border-bottom:1px solid #ddd;">'
        + " | ".join(links)
        + "</nav>\n"
    )


def build_series_page(meta: dict[str, Any], article_items: list[dict[str, Any]]) -> str:
    rows = "\n".join(
        f'<li><a href="{article_url(item["slug"])}">{html.escape(item["short_title"])}</a></li>'
        for item in article_items
    )
    return f"""<p>This project follows a concrete 2D Fermi-Hubbard simulation route: from the earlier 1D IBM/TDVP validation series, through a cuprate-oriented square-lattice Hubbard model, to exact 3x3 validation, IBM and Fire Opal diagnostics, and tensor-network baselines up to the current 6x6 diagnostic step.</p>
<p>The claim boundary is practical and cautious. The current 2D results are diagnostic validation data. They are not a claim of d-wave superconductivity, not material evidence for cuprates, and not a quantum-advantage claim.</p>
<h2>Article series</h2>
<ol>
{rows}
</ol>
<h2>Project links</h2>
<ul>
<li><a href="https://github.com/BramDo/fermi-hubbard-60q-tdvp">Project repository</a></li>
<li><a href="{FIRST_SERIES_URL}">First Fermi-Hubbard project page</a></li>
<li><a href="https://arxiv.org/abs/2510.26845">Google/Willow 2D Fermi-Hubbard paper</a></li>
<li><a href="https://zenodo.org/records/17881822">Google/Willow dataset</a></li>
<li><a href="https://arxiv.org/abs/2605.04025">Q-CTRL 1D Fermi-Hubbard paper</a></li>
</ul>
"""


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=SRC)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    src = args.src if args.src.is_absolute() else ROOT / args.src
    out = args.out if args.out.is_absolute() else ROOT / args.out
    out.mkdir(parents=True, exist_ok=True)
    article_dir = out / "articles"
    article_dir.mkdir(parents=True, exist_ok=True)

    series_meta, _series_lines = parse_front_matter(src / "00_series_page.md")
    article_items: list[dict[str, Any]] = []
    article_sources: list[tuple[dict[str, Any], list[str], Path]] = []
    for path in sorted(src.glob("[0-9][0-9]_*.md")):
        if path.name.startswith("00_"):
            continue
        meta, body = parse_front_matter(path)
        part = int(meta["part"])
        short_title = str(meta["title"]).split(": ", 1)[-1]
        item = {
            "part": part,
            "title": meta["title"],
            "short_title": f"Part {part}: {short_title}",
            "slug": meta["slug"],
            "post_type": meta.get("post_type", "post"),
            "excerpt": meta.get("excerpt", ""),
            "source": path.as_posix(),
        }
        article_items.append(item)
        article_sources.append((meta, body, path))

    article_items.sort(key=lambda item: int(item["part"]))
    for meta, body, path in article_sources:
        part = int(meta["part"])
        content = nav_html(part, article_items) + render_markdown(body) + nav_html(part, article_items)
        html_path = article_dir / f"{part:02d}.html"
        html_path.write_text(content, encoding="utf-8")
        article_items[part - 1]["file"] = html_path.relative_to(out).as_posix()

    series_content = build_series_page(series_meta, article_items)
    series_path = out / "series_page.html"
    series_path.write_text(series_content, encoding="utf-8")
    manifest = {
        "site": SITE,
        "series": {
            "title": series_meta["title"],
            "slug": series_meta["slug"],
            "post_type": series_meta.get("post_type", "page"),
            "excerpt": series_meta.get("excerpt", ""),
            "file": series_path.relative_to(out).as_posix(),
            "url": SERIES_URL,
        },
        "articles": article_items,
    }
    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    print(manifest_path)


if __name__ == "__main__":
    main()
