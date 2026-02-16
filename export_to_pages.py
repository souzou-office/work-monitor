"""
Work Monitor - Export to GitHub Pages
Copies analyzer report JSON files to docs/data/ for static dashboard hosting.

Usage:
  python export_to_pages.py                              # Export all available dates
  python export_to_pages.py --date 2026-02-16            # Export specific date
  python export_to_pages.py --days 7                     # Export last N days
  python export_to_pages.py --include-screenshots        # Include screenshot thumbnails
  python export_to_pages.py --protect 2026-02-16         # Protect date from auto-cleanup
"""

import json
import shutil
import base64
import argparse
from datetime import date, timedelta
from pathlib import Path
from io import BytesIO

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


SCREENSHOT_THUMB_WIDTH = 480   # thumbnail width for embedded screenshots


def strip_screenshots(data: dict) -> dict:
    """Remove screenshot_files from employee data (not available on GitHub Pages)."""
    if "employees" in data:
        for emp_data in data["employees"].values():
            emp_data["screenshot_files"] = []
    return data


def embed_screenshots(data: dict) -> dict:
    """Embed screenshot thumbnails as base64 data URIs in the JSON.

    Reads screenshot JPEGs from Google Drive, resizes to thumbnails,
    and adds them as data:image/jpeg;base64,... entries.
    """
    date_str = data.get("date", "")
    if not date_str or "employees" not in data:
        return data

    try:
        from PIL import Image
    except ImportError:
        print("  [WARN] Pillow not installed, skipping screenshot embedding")
        return data

    for emp_name, emp_data in data["employees"].items():
        day_dir = GDRIVE_BASE / emp_name / date_str
        if not day_dir.exists():
            emp_data["screenshots"] = []
            continue

        ss_files = sorted(day_dir.glob("ss_*.jpg"))
        screenshots = []
        for ss_file in ss_files:
            try:
                img = Image.open(ss_file)
                if img.width > SCREENSHOT_THUMB_WIDTH:
                    ratio = SCREENSHOT_THUMB_WIDTH / img.width
                    new_size = (SCREENSHOT_THUMB_WIDTH, int(img.height * ratio))
                    img = img.resize(new_size, Image.LANCZOS)

                buf = BytesIO()
                img.save(buf, "JPEG", quality=40, optimize=True)
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")

                time_str = ss_file.stem.replace("ss_", "").replace("-", ":")
                screenshots.append({
                    "time": time_str,
                    "data": f"data:image/jpeg;base64,{b64}",
                })
            except Exception as e:
                print(f"  [WARN] Failed to process {ss_file.name}: {e}")

        emp_data["screenshots"] = screenshots
        emp_data["screenshot_files"] = []
        if screenshots:
            print(f"  [SS] {emp_name}: {len(screenshots)} screenshot(s) embedded")

    return data


def sync_keep_files(protected_dates: list[str]):
    """Create .keep files in Google Drive date folders to prevent auto-cleanup.

    Call with dates marked as 'protected' on the dashboard.
    Usage: python export_to_pages.py --protect 2026-02-16 2026-02-13
    """
    for employee_dir in GDRIVE_BASE.iterdir():
        if not employee_dir.is_dir() or employee_dir.name.startswith("_"):
            continue
        for date_str in protected_dates:
            day_dir = employee_dir / date_str
            if day_dir.exists():
                keep_file = day_dir / ".keep"
                if not keep_file.exists():
                    keep_file.touch()
                    print(f"  [KEEP] {keep_file}")


def export_files(files: list[Path], include_screenshots: bool = False):
    """Copy report files to docs/data/ and update the index."""
    DOCS_DATA_DIR.mkdir(parents=True, exist_ok=True)

    exported = []
    for src in files:
        with open(src, "r", encoding="utf-8") as f:
            data = json.load(f)

        if include_screenshots:
            data = embed_screenshots(data)
        else:
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
    parser.add_argument("--include-screenshots", action="store_true", help="Embed screenshot thumbnails as base64 in JSON")
    parser.add_argument("--protect", nargs="+", default=None, help="Protect dates from auto-cleanup (create .keep files)")
    args = parser.parse_args()

    if args.protect:
        print("Protecting dates from auto-cleanup...")
        sync_keep_files(args.protect)
        if not args.date and not args.days:
            return

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
    export_files(files, include_screenshots=args.include_screenshots)


if __name__ == "__main__":
    main()
