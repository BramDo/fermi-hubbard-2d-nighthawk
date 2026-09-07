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
OUT = ROOT / "output" / "medium_2d_cuprate_series"
SERIES_URL = f"{SITE}/fermi-hubbard-2d-cuprate-series/"


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
        if ":" not in line:
            continue
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


def strip_initial_h1(lines: list[str]) -> list[str]:
    out = list(lines)
    while out and not out[0].strip():
        out.pop(0)
    if out and out[0].startswith("# "):
        out.pop(0)
    while out and not out[0].strip():
        out.pop(0)
    return out


def markdown_for_medium(meta: dict[str, Any], body: list[str], total_parts: int) -> str:
    title = str(meta["title"])
    part = int(meta["part"])
    url = article_url(str(meta["slug"]))
    lines: list[str] = [
        f"# {title}",
        "",
        "Originally published at:",
        url,
        "",
        f"Part {part} of {total_parts} in the Fermi-Hubbard 2D cuprate series.",
        f"Series page: {SERIES_URL}",
        "",
    ]
    lines.extend(convert_latex_shortcodes_to_fences(strip_initial_h1(body)))
    return "\n".join(lines).rstrip() + "\n"


def convert_latex_shortcodes_to_fences(lines: list[str]) -> list[str]:
    out: list[str] = []
    i = 0
    while i < len(lines):
        stripped = lines[i].strip()
        if stripped.startswith("[latex"):
            formula: list[str] = []
            i += 1
            while i < len(lines) and "[/latex]" not in lines[i]:
                formula.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            out.extend(["```text", *formula, "```"])
            continue
        out.append(lines[i])
        i += 1
    return out


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


def render_markdown(lines: list[str]) -> str:
    out: list[str] = []
    i = 0
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
        if stripped.startswith("|") and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            table_lines = [lines[i], lines[i + 1]]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i])
                i += 1
            out.append(render_table(table_lines))
            continue
        heading = re.match(r"^(#{1,6})\s+(.+)$", stripped)
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
            if (
                not nxt
                or nxt.startswith("#")
                or nxt.startswith("|")
                or nxt.startswith("```")
                or re.match(r"^\s*(?:-|\d+\.)\s+", lines[i])
            ):
                break
            para.append(nxt)
            i += 1
        out.append(f"<p>{render_inline(' '.join(para))}</p>\n")
    return "".join(out)


def plain_text_from_markdown(markdown: str) -> str:
    text = re.sub(r"```text\n(.*?)\n```", lambda m: "\n" + m.group(1) + "\n", markdown, flags=re.S)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)", r"\1 (\2)", text)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    return text.rstrip() + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--src", type=Path, default=SRC)
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    src = args.src if args.src.is_absolute() else ROOT / args.src
    out = args.out if args.out.is_absolute() else ROOT / args.out

    md_dir = out / "md"
    html_dir = out / "html"
    txt_dir = out / "txt"
    for directory in (md_dir, html_dir, txt_dir):
        directory.mkdir(parents=True, exist_ok=True)

    sources = []
    for path in sorted(src.glob("[0-9][0-9]_*.md")):
        if path.name.startswith("00_"):
            continue
        meta, body = parse_front_matter(path)
        sources.append((path, meta, body))

    total_parts = len(sources)
    manifest: dict[str, Any] = {
        "series_url": SERIES_URL,
        "articles": [],
        "format_note": (
            "Medium does not reliably render WordPress MathJax shortcodes. "
            "LaTeX display blocks are converted to plain text code blocks."
        ),
    }

    for path, meta, body in sources:
        part = int(meta["part"])
        stem = f"{part:02d}_{Path(path).stem[3:]}"
        markdown = markdown_for_medium(meta, body, total_parts)
        html_content = render_markdown(markdown.splitlines())
        plain = plain_text_from_markdown(markdown)

        md_path = md_dir / f"{stem}.md"
        html_path = html_dir / f"{stem}.html"
        txt_path = txt_dir / f"{stem}.txt"
        md_path.write_text(markdown, encoding="utf-8")
        html_path.write_text(html_content, encoding="utf-8")
        txt_path.write_text(plain, encoding="utf-8")
        manifest["articles"].append(
            {
                "part": part,
                "title": meta["title"],
                "source": path.as_posix(),
                "canonical_url": article_url(str(meta["slug"])),
                "markdown": md_path.relative_to(out).as_posix(),
                "html": html_path.relative_to(out).as_posix(),
                "plain_text": txt_path.relative_to(out).as_posix(),
            }
        )

    manifest_path = out / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
    write_index(out, manifest)
    write_readme(out, manifest)
    print(manifest_path)


def write_index(out: Path, manifest: dict[str, Any]) -> None:
    rows = []
    for item in manifest["articles"]:
        rows.append(
            "<tr>"
            f"<td>{int(item['part'])}</td>"
            f"<td>{html.escape(str(item['title']))}</td>"
            f"<td><a href=\"{html.escape(item['html'], quote=True)}\">HTML</a></td>"
            f"<td><a href=\"{html.escape(item['markdown'], quote=True)}\">Markdown</a></td>"
            f"<td><a href=\"{html.escape(item['plain_text'], quote=True)}\">Text</a></td>"
            f"<td><a href=\"{html.escape(item['canonical_url'], quote=True)}\">Canonical</a></td>"
            "</tr>"
        )
    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Medium 2D cuprate package</title>
  <style>
    body {{ font-family: system-ui, sans-serif; max-width: 980px; margin: 40px auto; line-height: 1.5; }}
    table {{ border-collapse: collapse; width: 100%; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; vertical-align: top; }}
    th {{ text-align: left; background: #f6f6f6; }}
    code {{ background: #f6f6f6; padding: 1px 4px; }}
  </style>
</head>
<body>
  <h1>Medium 2D cuprate package</h1>
  <p>{html.escape(str(manifest["format_note"]))}</p>
  <p>Series canonical URL: <a href="{html.escape(str(manifest["series_url"]), quote=True)}">{html.escape(str(manifest["series_url"]))}</a></p>
  <table>
    <thead><tr><th>Part</th><th>Title</th><th>HTML</th><th>Markdown</th><th>Text</th><th>Canonical</th></tr></thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""
    (out / "index.html").write_text(content, encoding="utf-8")


def write_readme(out: Path, manifest: dict[str, Any]) -> None:
    lines = [
        "# Medium 2D cuprate package",
        "",
        "This folder contains Medium-friendly versions of the Edukaizen 2D cuprate series.",
        "",
        "Medium does not reliably render the WordPress MathJax shortcodes, so display formulas are converted to plain text code blocks.",
        "",
        f"Series canonical URL: {manifest['series_url']}",
        "",
        "Files per article:",
        "",
        "- `html/` is the best source for browser copy/paste into Medium.",
        "- `md/` is the editable source with headings, links, tables, and formula code blocks.",
        "- `txt/` is a plain-text fallback.",
        "",
        "Articles:",
        "",
    ]
    for item in manifest["articles"]:
        lines.append(f"{item['part']}. {item['title']}")
        lines.append(f"   - HTML: `{item['html']}`")
        lines.append(f"   - Markdown: `{item['markdown']}`")
        lines.append(f"   - Plain text: `{item['plain_text']}`")
        lines.append(f"   - Canonical: {item['canonical_url']}")
    (out / "README.md").write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
