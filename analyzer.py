"""
Work Monitor - Analyzer (Admin PC)
Analyzes employee data using Claude API (text logs only, no screenshots)

Usage:
python analyzer.py
python analyzer.py --date 2026-02-16
python analyzer.py --employee 池田龍太
"""

import os
import sys
import json
import argparse
from datetime import date
from pathlib import Path

# ============================================================
# Settings
# ============================================================
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")
REPORT_DIR = GDRIVE_BASE / "_reports"
MODEL = "claude-sonnet-4-5-20250929"
# ============================================================

ANALYSIS_PROMPT = """あなたは業務改善コンサルタントです。
司法書士事務所の従業員の1日の業務データ（PCアクティビティログ＋ウィンドウ切り替えログ）を分析してください。

## データの説明
- activity_log: 10分ごとのスナップショット。KB=キーボード操作回数、Mouse=マウス操作回数、Chars=入力文字数、Del=削除回数
- window_log: アクティブウィンドウが切り替わるたびの記録

## 分析ルール
- 操作なし（KB:0, Mouse:0）→ 電話対応、来客、打合せの可能性。サボりと断定しない
- キーボード操作多い＋文字数多い → 文書作成に集中
- 削除回数が多い → 修正・推敲が多い（効率の問題 or 慎重な作業）
- ウィンドウ切り替えログから、どのアプリ・サイトをどれくらい使ったか正確に把握する
- 司法書士業務のアプリ（申請用総合ソフト、登記ねっと、法務局オンライン等）を考慮
- ブラウザのタイトルから、業務関連の調べものか私的利用かを判断する

## 出力フォーマット（JSON）

以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

{
  "summary": {
    "total_hours": "7h 42m",
    "focus_score": 82,
    "top_app": "申請用総合ソフト",
    "top_app_pct": 38,
    "total_chars": 12500
  },
  "time_breakdown": [
    {"label": "登記申請書作成", "pct": 38, "color": "#4f46e5"},
    {"label": "メール対応", "pct": 22, "color": "#0891b2"}
  ],
  "timeline": [
    {
      "time": "09:00",
      "label": "メール確認・返信",
      "desc": "Outlook - 受信トレイ確認",
      "category": "email"
    }
  ],
  "activity_bars": {
    "09": [40, 60, 0, 0, 0],
    "10": [65, 0, 25, 10, 0]
  },
  "focus_hours": [9, 23],
  "focus_data": [],
  "suggestions": [
    {
      "level": "high",
      "title": "メール対応を時間帯で集約",
      "desc": "改善の詳細説明"
    }
  ]
}

## フィールド説明
- time_breakdown: アプリ/作業カテゴリごとの時間配分。color は #4f46e5(業務), #0891b2(メール), #10b981(オンライン申請), #f59e0b(Excel等), #9ca3af(その他) を使用
- timeline: 主要な作業の切り替わりポイント。category は work/email/meeting/idle/browse のいずれか
- activity_bars: 時間帯ごとの[業務, メール, 電話/打合せ, 離席, ブラウザ]の割合（合計100）。データがある時間帯のみ含める
- focus_hours: [開始時刻, 終了時刻] データに基づいて実際の稼働時間帯を設定
- focus_data: focus_hoursで指定した時間帯の各時間の集中度（0-100）。要素数は終了時刻-開始時刻と同じにする
- suggestions: 改善提案。level は high/mid/low。最大3件
- total_chars: 1日の総入力文字数
"""


def load_log(employee_dir: Path, date_str: str) -> list[dict]:
    log_file = employee_dir / date_str / "activity_log.jsonl"
    if not log_file.exists():
        return []
    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_window_log(employee_dir: Path, date_str: str) -> list[dict]:
    log_file = employee_dir / date_str / "window_log.jsonl"
    if not log_file.exists():
        return []
    entries = []
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def get_screenshot_files(employee_dir: Path, date_str: str, log_entries: list[dict]) -> list[dict]:
    files = []
    for entry in log_entries:
        if entry.get("screenshot_file"):
            ss_path = employee_dir / date_str / entry["screenshot_file"]
            if ss_path.exists():
                files.append({
                    "timestamp": entry["timestamp"],
                    "filename": entry["screenshot_file"],
                })
    return files


def analyze_employee(client, employee_name: str, employee_dir: Path, date_str: str) -> dict | None:
    log_entries = load_log(employee_dir, date_str)
    window_entries = load_window_log(employee_dir, date_str)

    if not log_entries and not window_entries:
        print(f"  [SKIP] {employee_name}: No data")
        return None

    print(f"  [INFO] {employee_name}: Activity log: {len(log_entries)}, Window log: {len(window_entries)}")

    content = []

    # Activity log with char count
    log_text = f"## {employee_name} Activity Log ({date_str})\n\n"
    for entry in log_entries:
        t = entry["timestamp"].split("T")[1][:5]
        chars = entry.get('char_count', '-')
        dels = entry.get('delete_count', '-')
        log_text += (
            f"[{t}] {entry.get('process_name','')} | "
            f"{entry.get('active_window','')[:80]} | "
            f"KB:{entry.get('keyboard_events',0)} Mouse:{entry.get('mouse_events',0)} "
            f"Chars:{chars} Del:{dels}\n"
        )
    content.append({"type": "text", "text": log_text})

    # Window switch log
    if window_entries:
        window_text = f"\n## Window Switch Log\n\n"
        for entry in window_entries:
            t = entry["timestamp"].split("T")[1][:8]
            window_text += f"[{t}] {entry.get('process_name','')} | {entry.get('active_window','')[:80]}\n"
        content.append({"type": "text", "text": window_text})

    print(f"  [INFO] {employee_name}: Analyzing with Claude API...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=ANALYSIS_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    text = response.content[0].text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        print(f"  [WARN] {employee_name}: JSON parse failed")
        result = {"raw_text": text}

    result["screenshot_files"] = get_screenshot_files(employee_dir, date_str, log_entries)

    result["window_log"] = [
        {
            "timestamp": entry["timestamp"],
            "active_window": entry.get("active_window", ""),
            "process_name": entry.get("process_name", ""),
        }
        for entry in window_entries
    ]

    inp = response.usage.input_tokens
    out = response.usage.output_tokens
    cost = (inp * 3 + out * 15) / 1_000_000
    print(f"  [COST] {employee_name}: {inp:,} + {out:,} tokens = ${cost:.3f}")

    return result


def get_employees(date_str: str, filter_employee: str = None) -> list[tuple[str, Path]]:
    employees = []
    if not GDRIVE_BASE.exists():
        print(f"[ERROR] Google Drive path not found: {GDRIVE_BASE}")
        sys.exit(1)

    for d in GDRIVE_BASE.iterdir():
        if d.is_dir() and not d.name.startswith("_"):
            if filter_employee and d.name != filter_employee:
                continue
            employees.append((d.name, d))

    return sorted(employees)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default=date.today().strftime("%Y-%m-%d"))
    parser.add_argument("--employee", default=None)
    args = parser.parse_args()

    try:
        import anthropic
    except ImportError:
        print("[ERROR] Run: pip install anthropic")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] Set ANTHROPIC_API_KEY environment variable")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"{'='*50}")
    print(f"  Work Monitor Analysis - {args.date}")
    print(f"{'='*50}\n")

    employees = get_employees(args.date, args.employee)
    if not employees:
        print("[ERROR] No employee data found")
        sys.exit(1)

    print(f"Employees: {', '.join(name for name, _ in employees)}\n")

    all_results = {}
    for name, path in employees:
        result = analyze_employee(client, name, path, args.date)
        if result:
            all_results[name] = result
        print()

    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = REPORT_DIR / f"data_{args.date}.json"
    dashboard_data = {
        "date": args.date,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "employees": all_results,
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=2)

    print(f"[OK] Dashboard data: {output_file}")
    print(f"[DONE] {len(all_results)} employee(s) analyzed")


if __name__ == "__main__":
    main()
