# 業務モニター

従業員PCのスクリーンショット＋操作ログをAIで分析し、業務改善レポートを生成するツール。

## 全体構成

```
従業員PC                    Google Drive                管理者PC（Ryuta）
┌──────────┐              ┌──────────────┐            ┌───────────────┐
│recorder.py│─自動同期──→│work_monitor/ │←──読取──│ analyzer.py   │
│(バックグラウンド)│              │  田中美咲/   │            │ dashboard.py  │
└──────────┘              │  鈴木健太/   │            └───────────────┘
                          │  _reports/   │
                          └──────────────┘
```

## ファイル一覧

| ファイル | 配置先 | 役割 |
|---------|--------|------|
| `recorder.py` | 各従業員PC | スクショ＋ログ記録（バックグラウンド動作） |
| `analyzer.py` | 管理者PC | Claude APIで全従業員のデータを分析 |
| `dashboard.py` | 管理者PC | Webダッシュボードを表示 |

## セットアップ

### 1. 共通：パッケージインストール

```
# 従業員PC
pip install Pillow pynput

# 管理者PC
pip install anthropic
```

### 2. Google Driveのフォルダ構成

Google Driveに以下のフォルダを作成：
```
マイドライブ/
  work_monitor/
    _reports/       ← 分析レポート（自動生成）
```
従業員ごとのフォルダ（田中美咲/ 等）は recorder.py が自動作成します。

### 3. 従業員PCの設定

`recorder.py` の冒頭を従業員ごとに変更：

```python
EMPLOYEE_NAME = "田中美咲"          # ← 従業員名
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")  # ← Google Driveのパス
```

### 4. 従業員PCの自動起動設定

1. `Win + R` → `shell:startup` でスタートアップフォルダを開く
2. ショートカットを作成：
   - 対象: `pythonw.exe "C:\path\to\recorder.py"`
   - pythonw.exe を使うことで完全バックグラウンド動作（画面に何も表示されない）

### 5. 管理者PCの設定

環境変数にAPIキーを設定：
```
set ANTHROPIC_API_KEY=sk-ant-xxxxx
```

## 日常の使い方

### 記録（自動）
従業員PCの起動時に recorder.py が自動で動き始めます。特に操作不要。

### 分析（1日1回）
業務終了後に管理者PCで実行：

```bash
# 今日の全従業員を分析
python analyzer.py

# 特定の日・特定の従業員を分析
python analyzer.py --date 2026-02-16
python analyzer.py --employee 田中美咲
python analyzer.py --date 2026-02-16 --employee 田中美咲
```

### ダッシュボード確認
```bash
python dashboard.py
```
ブラウザが自動で開きます（http://localhost:8080）

## コスト目安

- スクショ: JPEG保存（1枚約100-200KB）
- Google Drive: 1人1日あたり約5-10MB
- Claude API (Sonnet): 1人1日あたり約30-80円
- 5人で月間約5,000〜12,000円程度

## カスタマイズ

### 記録間隔を変更
`recorder.py`:
```python
INTERVAL_MINUTES = 10  # 5, 15, 20 などに変更可能
```

### Google Driveのパスを変更
各ファイルの `GDRIVE_BASE` を環境に合わせて変更：
```python
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")
# または
GDRIVE_BASE = Path("D:/Google Drive/マイドライブ/work_monitor")
```

## トラブルシューティング

### recorder.py が動いているか確認
タスクマネージャー → 詳細 → python.exe または pythonw.exe が存在するか確認

### エラーログ
各従業員のGoogle Driveフォルダに `error.log` が出力されます

### Google Driveの同期が遅い
JPEG保存で軽量化済み。同期が追いつかない場合は記録間隔を15分に変更。
