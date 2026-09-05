#!/usr/bin/env python3
"""Rewrite the year in the bundled synthetic sample logs to the current year.

The datasets mix year-less BSD-syslog lines (which parse to "now's" year) with
formats that carry an explicit year (JSON `ts`, Apache `[dd/Mon/yyyy]`, vendor
`date=yyyy-mm-dd`). Keeping the explicit years equal to the current year keeps
cross-source correlation in the demo scenarios coherent.

Run this if you are demoing ULPF in a much later year:

    python sample_logs/refresh_dates.py
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
YEAR = datetime.now(timezone.utc).year

# only touch year tokens that sit in an obvious date context
PATTERNS = [
    re.compile(r"(?<=\D)(20\d\d)(?=-\d\d-\d\d)"),          # 2025-09-02
    re.compile(r"(?<=/)(20\d\d)(?=:\d\d:\d\d:\d\d)"),      # [02/Sep/2025:08:15:03
    re.compile(r"(?<=date=)(20\d\d)(?=-\d\d-\d\d)"),       # date=2025-09-02
]


def refresh(path: Path) -> bool:
    text = original = path.read_text(encoding="utf-8")
    for rx in PATTERNS:
        text = rx.sub(str(YEAR), text)
    if text != original:
        path.write_text(text, encoding="utf-8")
        return True
    return False


def main() -> None:
    changed = 0
    for path in sorted(ROOT.rglob("*")):
        if path.is_file() and path.suffix.lower() in {".log", ".jsonl", ".json", ".txt", ".syslog"}:
            if refresh(path):
                changed += 1
                print(f"updated {path.relative_to(ROOT)}")
    print(f"done - {changed} file(s) set to year {YEAR}")


if __name__ == "__main__":
    main()
