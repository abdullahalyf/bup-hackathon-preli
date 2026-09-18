#!/usr/bin/env python3
"""Build frontend/index.html from .puku/v4_*.py pieces, writing valid UTF-8.

Avoids PowerShell Set-Content which mangles em-dashes/en-dashes to Windows-1252.
"""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / ".puku"
OUT = ROOT / "frontend" / "index.html"

HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>GridWise \u2014 operator console</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;500;700;800&family=Special+Elite&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.7/chart.umd.min.js"></script>
<style>
"""

TAIL = """
</style>
</head>
<body>
__BODY__
<script>
__JS__
</script>
</body>
</html>
"""

def _load(name: str) -> str:
    g = {}
    exec((SRC / f"v4_{name}.py").read_text(encoding="utf-8"), g)
    return g[name.upper()]

def main():
    css = _load("css")
    body = _load("body")
    js = _load("js")
    out = HEAD + css + TAIL.replace("__BODY__", body).replace("__JS__", js)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(out, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(out):,} bytes, {out.count(chr(10)):,} lines)")

if __name__ == "__main__":
    main()
