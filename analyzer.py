"""
業務モニター - 分析スクリプト（管理者PC用）
Google Drive上の全従業員データをClaude APIで分析し、レポートを生成

=== セットアップ ===
1. pip install anthropic
2. 環境変数設定: set ANTHROPIC_API_KEY=sk-ant-xxxxx

=== 使い方 ===
python analyzer.py                          # 今日の全員分を分析
python analyzer.py --date 2026-02-16        # 指定日の全員分
python analyzer.py --employee 田中美咲       # 特定の従業員のみ
python analyzer.py --date 2026-02-16 --employee 田中美咲
"""

import os
import sys
import json
import base64
import argparse
from datetime import date
from pathlib import Path

# ============================================================
# 設定
# ============================================================
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")
REPORT_DIR = GDRIVE_BASE / "_reports"
MODEL = "claude-sonnet-4-5-20250514"
MAX_SCREENSHOTS = 30  # 1人あたりAPIに送るスクショの最大枚数
# ============================================================

ANALYSIS_PROMPT = """あなたは業務改善コンサルタントです。
司法書士事務所の従業員の1日の業務データ（スクリーンショット＋PCアクティビティログ）を分析してください。

## 分析ルール
- 画面変化なし＋操作なし → 電話対応、来客、打合せの可能性。サボりと断定しない
- 画面変化なし＋キーボード操作あり → 入力作業中
- 司法書士業務のアプリ（申請用総合ソフト、登記ねっと、法務局オンライン等）を考慮

## 出力フォーマット（JSON）

以下のJSON形式で出力してください。JSON以外のテキストは含めないでください。

{
  "summary": {
    "total_hours": "7h 42m",
    "focus_score": 82,
    "top_app": "申請用総合ソフト",
    "top_app_pct": 38
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
  "focus_data": [65, 78, 82, 75, 0, 80, 72, 85, 68],
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
- activity_bars: 時間帯ごとの[業務, メール, 電話/打合せ, 離席, ブラウザ]の割合（合計100）
- focus_data: 9時〜17時の各時間帯の集中度（0-100）。昼休憩は0
- suggestions: 改善提案。level は high/mid/low。最大3件
"""


def load_log(employee_dir: Path, date_str: str) -> list[dict]:
    """アクティビティログを読み込む"""
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


def load_screenshots(employee_dir: Path, date_str: str, log_entries: list[dict]) -> list[dict]:
    """スクリーンショットをBase64で読み込む"""
    day_dir = employee_dir / date_str
    screenshots = []

    entries_with_ss = [e for e in log_entries if e.get("screenshot_file")]

    # 間引き
    if len(entries_with_ss) > MAX_SCREENSHOTS:
        step = len(entries_with_ss) / MAX_SCREENSHOTS
        selected = [entries_with_ss[int(i * step)] for i in range(MAX_SCREENSHOTS)]
    else:
        selected = entries_with_ss

    for entry in selected:
        ss_path = day_dir / entry["screenshot_file"]
        if ss_path.exists():
            with open(ss_path, "rb") as f:
                b64 = base64.standard_b64encode(f.read()).decode("utf-8")

            # JPEGかPNGか判定
            ext = ss_path.suffix.lower()
            media_type = "image/jpeg" if ext in (".jpg", ".jpeg") else "image/png"

            screenshots.append({
                "timestamp": entry["timestamp"],
                "base64": b64,
                "media_type": media_type,
            })

    return screenshots


def analyze_employee(client, employee_name: str, employee_dir: Path, date_str: str) -> dict | None:
    """1人分のデータを分析"""
    log_entries = load_log(employee_dir, date_str)
    if not log_entries:
        print(f"  [SKIP] {employee_name}: データなし")
        return None

    print(f"  [INFO] {employee_name}: ログ{len(log_entries)}件")

    screenshots = load_screenshots(employee_dir, date_str, log_entries)
    print(f"  [INFO] {employee_name}: スクショ{len(screenshots)}枚")

    # APIリクエスト構築
    content = []

    # ログデータ
    log_text = f"## {employee_name} のアクティビティログ（{date_str}）\n\n"
    for entry in log_entries:
        t = entry["timestamp"].split("T")[1][:5]
        log_text += (
            f"[{t}] {entry['process_name']} | "
            f"{entry['active_window'][:80]} | "
            f"KB:{entry['keyboard_events']} Mouse:{entry['mouse_events']}\n"
        )
    content.append({"type": "text", "text": log_text})

    # スクリーンショット
    for ss in screenshots:
        t = ss["timestamp"].split("T")[1][:5]
        content.append({"type": "text", "text": f"\n--- {t} ---"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": ss["media_type"],
                "data": ss["base64"],
            },
        })

    # Claude API 呼び出し
    print(f"  [INFO] {employee_name}: Claude APIで分析中...")
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=ANALYSIS_PROMPT,
        messages=[{"role": "user", "content": content}],
    )

    # レスポンスのパース
    text = response.content[0].text.strip()
    # ```json ... ``` を除去
    if text.startswith("```"):
        text = text.split("\n", 1)[1]
        if text.endswith("```"):
            text = text[:-3]
        text = text.strip()

    try:
        result = json.loads(text)
    except json.JSONDecodeError:
        print(f"  [WARN] {employee_name}: JSONパース失敗、テキストで保存")
        result = {"raw_text": text}

    # コスト表示
    inp = response.usage.input_tokens
    out = response.usage.output_tokens
    cost = (inp * 3 + out * 15) / 1_000_000
    print(f"  [COST] {employee_name}: {inp:,} + {out:,} tokens = ${cost:.3f}")

    return result


def get_employees(date_str: str, filter_employee: str = None) -> list[tuple[str, Path]]:
    """従業員一覧を取得（Google Drive上のフォルダ構成から）"""
    employees = []
    if not GDRIVE_BASE.exists():
        print(f"[ERROR] Google Driveのパスが見つかりません: {GDRIVE_BASE}")
        sys.exit(1)

    for d in GDRIVE_BASE.iterdir():
        if d.is_dir() and not d.name.startswith("_"):
            if filter_employee and d.name != filter_employee:
                continue
            employees.append((d.name, d))

    return sorted(employees)


def save_dashboard_data(all_data: dict, date_str: str):
    """ダッシュボード用のJSONを保存"""
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    output_file = REPORT_DIR / f"data_{date_str}.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=2)
    print(f"\n[OK] ダッシュボード用データ: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="業務モニター分析")
    parser.add_argument("--date", default=date.today().strftime("%Y-%m-%d"), help="分析対象日 (YYYY-MM-DD)")
    parser.add_argument("--employee", default=None, help="特定の従業員のみ分析")
    args = parser.parse_args()

    # Anthropic クライアント
    try:
        import anthropic
    except ImportError:
        print("[ERROR] pip install anthropic を実行してください")
        sys.exit(1)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("[ERROR] 環境変数 ANTHROPIC_API_KEY を設定してください")
        sys.exit(1)

    client = anthropic.Anthropic(api_key=api_key)

    print(f"{'='*50}")
    print(f"  業務モニター分析 - {args.date}")
    print(f"{'='*50}\n")

    employees = get_employees(args.date, args.employee)
    if not employees:
        print("[ERROR] 従業員データが見つかりません")
        sys.exit(1)

    print(f"対象従業員: {', '.join(name for name, _ in employees)}\n")

    # 全従業員を分析
    all_results = {}
    total_cost = 0

    for name, path in employees:
        result = analyze_employee(client, name, path, args.date)
        if result:
            all_results[name] = result
        print()

    # ダッシュボード用JSON保存
    dashboard_data = {
        "date": args.date,
        "generated_at": __import__("datetime").datetime.now().isoformat(),
        "employees": all_results,
    }
    save_dashboard_data(dashboard_data, args.date)

    print(f"[DONE] {len(all_results)}名分の分析が完了しました")


if __name__ == "__main__":
    main()
