"""
Work Monitor - Export to GitHub Pages
Copies analyzer report JSON files to docs/data/ for static dashboard hosting.

Usage:
  python export_to_pages.py                    # Export all available dates
  python export_to_pages.py --date 2026-02-16  # Export specific date
  python export_to_pages.py --days 7           # Export last N days
"""

import json
import shutil
import argparse
from datetime import date, timedelta
from pathlib import Path

# ============================================================
# Settings - match your analyzer.py config
# ============================================================
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")
REPORT_DIR = GDRIVE_BASE / "_reports"
DOCS_DATA_DIR = Path(__file__).parent / "docs" / "data"
# ============================================================


def find_report_files(date_filter: str = None, days: int = None) -> list[Path]:
    """Find data_YYYY-MM-DD.json files in the report directory."""
    if not REPORT_DIR.exists():
        print(f"[ERROR] Report directory not found: {REPORT_DIR}")
        return []

    files = sorted(REPORT_DIR.glob("data_*.json"))

    if date_filter:
        target = f"data_{date_filter}.json"
        files = [f for f in files if f.name == target]
    elif days:
        cutoff = date.today() - timedelta(days=days)
        cutoff_str = cutoff.strftime("%Y-%m-%d")
        files = [f for f in files if f.stem.replace("data_", "") >= cutoff_str]

    return files


def strip_screenshots(data: dict) -> dict:
    """Remove screenshot_files from employee data (not available on GitHub Pages)."""
    if "employees" in data:
        for emp_data in data["employees"].values():
            emp_data["screenshot_files"] = []
    return data


def export_files(files: list[Path]):
    """Copy report files to docs/data/ and update the index."""
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    exported = []
    for src in files:
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)

        data = strip_screenshots(data)

        dst = DOCS_DATA_DIR / src.name
        with open(dst, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        date_str = src.stem.replace("data_", "")
        exported.append(date_str)
        print(f"  [OK] {src.name} -> docs/data/{src.name}")

    # Merge with existing index
    index_file = DOCS_DATA_DIR / "index.json"
    existing_dates = set()
    if index_file.exists():
        with open(index_file, "r", encoding="utf-8") as f:
            existing = json.load(f)
            existing_dates = set(existing.get("dates", []))

    # Also scan docs/data/ for any data files already present
    for p in DOCS_DATA_DIR.glob("data_*.json"):
        d = p.stem.replace("data_", "")
        existing_dates.add(d)

    all_dates = sorted(existing_dates | set(exported), reverse=True)

    index = {
        "dates": all_dates,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
    }
    with open(index_file, "w", encoding="utf-8") as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f"\n[DONE] Exported {len(exported)} file(s), {len(all_dates)} date(s) in index")
    print(f"[INFO] Next: git add docs/data/ && git commit && git push")


def main():
    parser = argparse.ArgumentParser(description="Export work monitor data to GitHub Pages")
    parser.add_argument("--date", default=None, help="Export specific date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=None, help="Export last N days")
    args = parser.parse_args()

    print(f"{'='*50}")
    print(f"  Work Monitor - Export to GitHub Pages")
    print(f"  Source: {REPORT_DIR}")
    print(f"  Dest:   {DOCS_DATA_DIR}")
    print(f"{'='*50}\n")

    files = find_report_files(date_filter=args.date, days=args.days)
    if not files:
        print("[WARN] No report files found to export")
        return

    print(f"Found {len(files)} report file(s):\n")
    export_files(files)


if __name__ == "__main__":
    main()
