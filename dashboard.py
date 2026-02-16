"""
業務モニター - ダッシュボードサーバー（管理者PC用）
analyzer.pyが生成したJSONデータを読み込んでWebダッシュボードを表示

=== 使い方 ===
python dashboard.py
→ ブラウザで http://localhost:8080 を開く
"""

import http.server
import json
import os
import urllib.parse
from pathlib import Path
from datetime import date

# ============================================================
# 設定
# ============================================================
GDRIVE_BASE = Path("G:/マイドライブ/work_monitor")
REPORT_DIR = GDRIVE_BASE / "_reports"
PORT = 8080
# ============================================================


DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>業務モニター</title>
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<script src="https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.min.js"></script>
<style>
  :root {
    --bg-primary: #f5f6f8;
    --bg-card: #ffffff;
    --bg-card-hover: #f0f1f4;
    --bg-elevated: #f0f1f5;
    --border: #e2e4ea;
    --border-light: #d0d3db;
    --text-primary: #1a1c24;
    --text-secondary: #5a5e6e;
    --text-muted: #8e92a2;
    --accent: #4f46e5;
    --accent-light: #4338ca;
    --accent-dim: rgba(79, 70, 229, 0.08);
    --green: #10b981;
    --green-dim: rgba(16, 185, 129, 0.08);
    --amber: #f59e0b;
    --amber-dim: rgba(245, 158, 11, 0.08);
    --red: #ef4444;
    --red-dim: rgba(239, 68, 68, 0.08);
    --cyan: #0891b2;
    --cyan-dim: rgba(8, 145, 178, 0.08);
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    font-family: 'Noto Sans JP', sans-serif;
    background: var(--bg-primary);
    color: var(--text-primary);
    min-height: 100vh;
    -webkit-font-smoothing: antialiased;
  }

  ::-webkit-scrollbar { width: 6px; }
  ::-webkit-scrollbar-track { background: transparent; }
  ::-webkit-scrollbar-thumb { background: var(--border-light); border-radius: 3px; }

  .app { display: grid; grid-template-columns: 240px 1fr; min-height: 100vh; }

  /* Sidebar */
  .sidebar {
    background: var(--bg-card);
    border-right: 1px solid var(--border);
    padding: 24px 0;
    display: flex;
    flex-direction: column;
    box-shadow: 1px 0 4px rgba(0,0,0,0.03);
  }

  .logo { padding: 0 24px 28px; border-bottom: 1px solid var(--border); margin-bottom: 20px; }
  .logo h1 { font-size: 16px; font-weight: 600; letter-spacing: 0.02em; display: flex; align-items: center; gap: 10px; }
  .logo-icon { width: 28px; height: 28px; background: var(--accent); border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 14px; color: white; }
  .logo span { font-size: 11px; color: var(--text-muted); display: block; margin-top: 4px; font-weight: 400; }

  .nav-section { padding: 0 12px; margin-bottom: 24px; }
  .nav-label { font-size: 10px; text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-muted); padding: 0 12px; margin-bottom: 8px; font-weight: 500; }
  .nav-item { display: flex; align-items: center; gap: 10px; padding: 9px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; color: var(--text-secondary); transition: all 0.15s; }
  .nav-item:hover { background: var(--bg-card-hover); color: var(--text-primary); }
  .nav-item.active { background: var(--accent-dim); color: var(--accent); font-weight: 500; }

  .employee-list { padding: 0 12px; flex: 1; }
  .employee-item { display: flex; align-items: center; gap: 10px; padding: 8px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; color: var(--text-secondary); transition: all 0.15s; }
  .employee-item:hover { background: var(--bg-card-hover); color: var(--text-primary); }
  .employee-item.active { background: var(--accent-dim); color: var(--accent); }
  .avatar { width: 28px; height: 28px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 600; flex-shrink: 0; }

  /* Main */
  .main { padding: 28px 32px; overflow-y: auto; max-height: 100vh; }
  .header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 28px; }
  .header-left h2 { font-size: 20px; font-weight: 600; }
  .header-left p { color: var(--text-muted); font-size: 13px; margin-top: 2px; }

  .date-nav { display: flex; align-items: center; gap: 8px; }
  .date-btn { background: var(--bg-card); border: 1px solid var(--border); color: var(--text-secondary); padding: 7px 12px; border-radius: 8px; cursor: pointer; font-size: 13px; font-family: inherit; transition: all 0.15s; }
  .date-btn:hover { border-color: var(--border-light); color: var(--text-primary); }
  .date-display { font-family: 'JetBrains Mono', monospace; font-size: 13px; min-width: 110px; text-align: center; }

  .stats-row { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 24px; }
  .stat-card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; padding: 18px 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
  .stat-label { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; font-weight: 500; margin-bottom: 8px; }
  .stat-value { font-size: 26px; font-weight: 700; font-family: 'JetBrains Mono', monospace; line-height: 1; }
  .stat-sub { font-size: 11px; color: var(--text-muted); margin-top: 6px; }
  .stat-badge { display: inline-block; padding: 2px 7px; border-radius: 4px; font-size: 11px; font-weight: 500; }

  .grid-2 { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 24px; }
  .grid-full { margin-bottom: 24px; }
  .card { background: var(--bg-card); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }
  .card-header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
  .card-title { font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; }
  .card-body { padding: 20px; }

  /* Timeline */
  .timeline-item { display: grid; grid-template-columns: 52px 12px 1fr; gap: 12px; align-items: start; margin-bottom: 4px; min-height: 48px; }
  .timeline-time { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-muted); text-align: right; padding-top: 2px; }
  .timeline-dot-col { display: flex; flex-direction: column; align-items: center; height: 100%; }
  .timeline-dot { width: 8px; height: 8px; border-radius: 50%; flex-shrink: 0; margin-top: 5px; }
  .timeline-line { width: 1px; flex: 1; background: var(--border); margin-top: 4px; }
  .timeline-content { padding-bottom: 12px; }
  .timeline-label { font-size: 13px; font-weight: 500; margin-bottom: 2px; }
  .timeline-desc { font-size: 12px; color: var(--text-muted); }

  /* Activity Bar */
  .activity-bar-container { display: flex; flex-direction: column; gap: 6px; }
  .activity-row { display: flex; align-items: center; gap: 10px; }
  .activity-label { font-size: 11px; color: var(--text-muted); width: 36px; text-align: right; font-family: 'JetBrains Mono', monospace; flex-shrink: 0; }
  .activity-bar-track { flex: 1; height: 22px; display: flex; border-radius: 3px; overflow: hidden; gap: 1px; }
  .activity-segment { height: 100%; transition: opacity 0.15s; cursor: pointer; }
  .activity-segment:hover { opacity: 0.75; }
  .seg-work { background: var(--accent); }
  .seg-email { background: var(--cyan); }
  .seg-meeting { background: var(--amber); }
  .seg-idle { background: #d1d5db; }
  .seg-browse { background: var(--red); opacity: 0.7; }
  .activity-legend { display: flex; gap: 16px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border); }
  .legend-item { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-secondary); }
  .legend-dot { width: 8px; height: 8px; border-radius: 2px; flex-shrink: 0; }

  /* Pie Chart */
  .chart-container { display: flex; align-items: center; gap: 24px; }
  .chart-canvas-wrap { width: 160px; height: 160px; flex-shrink: 0; }
  .chart-legend-item { display: flex; align-items: center; justify-content: space-between; padding: 6px 0; font-size: 13px; }
  .chart-legend-left { display: flex; align-items: center; gap: 8px; }
  .chart-legend-color { width: 10px; height: 10px; border-radius: 3px; flex-shrink: 0; }
  .chart-legend-pct { font-family: 'JetBrains Mono', monospace; font-size: 12px; color: var(--text-muted); }

  /* Suggestions */
  .suggestion { padding: 14px 16px; border-radius: 8px; margin-bottom: 10px; border-left: 3px solid; }
  .suggestion:last-child { margin-bottom: 0; }
  .suggestion-high { background: var(--accent-dim); border-color: var(--accent); }
  .suggestion-mid { background: var(--amber-dim); border-color: var(--amber); }
  .suggestion-low { background: var(--green-dim); border-color: var(--green); }
  .suggestion-tag { display: inline-block; font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 500; margin-bottom: 6px; }
  .suggestion-high .suggestion-tag { background: rgba(79,70,229,0.15); color: var(--accent); }
  .suggestion-mid .suggestion-tag { background: rgba(245,158,11,0.15); color: var(--amber); }
  .suggestion-low .suggestion-tag { background: rgba(16,185,129,0.15); color: var(--green); }
  .suggestion-title { font-size: 13px; font-weight: 600; margin-bottom: 4px; }
  .suggestion-desc { font-size: 12px; color: var(--text-secondary); line-height: 1.6; }

  /* Screenshots */
  .screenshots-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 10px; }
  .screenshot-thumb { aspect-ratio: 16/9; background: var(--bg-elevated); border-radius: 8px; border: 1px solid var(--border); overflow: hidden; cursor: pointer; transition: all 0.2s; }
  .screenshot-thumb:hover { border-color: var(--accent); transform: translateY(-2px); box-shadow: 0 4px 16px rgba(79,70,229,0.1); }
  .screenshot-thumb img { width: 100%; height: 100%; object-fit: cover; }
  .screenshot-placeholder { width: 100%; height: 100%; display: flex; flex-direction: column; align-items: center; justify-content: center; font-size: 11px; color: var(--text-muted); gap: 4px; background: linear-gradient(135deg, var(--bg-elevated) 0%, #e8e9ee 100%); }
  .screenshot-placeholder .time { font-family: 'JetBrains Mono', monospace; font-size: 13px; color: var(--text-secondary); font-weight: 500; }
  .screenshot-placeholder .app-name { font-size: 10px; padding: 2px 6px; background: var(--bg-card); border-radius: 4px; margin-top: 2px; }

  .focus-chart-wrap { height: 140px; }

  /* Modal */
  .modal-overlay { display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.35); z-index: 1000; align-items: center; justify-content: center; backdrop-filter: blur(4px); }
  .modal-overlay.active { display: flex; }
  .modal-content { background: var(--bg-card); border: 1px solid var(--border); border-radius: 16px; max-width: 900px; width: 90%; max-height: 85vh; overflow: hidden; box-shadow: 0 20px 60px rgba(0,0,0,0.15); }
  .modal-header { padding: 16px 20px; border-bottom: 1px solid var(--border); display: flex; align-items: center; justify-content: space-between; }
  .modal-close { background: none; border: none; color: var(--text-muted); cursor: pointer; font-size: 18px; padding: 4px; }
  .modal-body { padding: 20px; overflow-y: auto; max-height: calc(85vh - 60px); }
  .modal-screenshot { width: 100%; border-radius: 8px; background: var(--bg-elevated); margin-bottom: 16px; border: 1px solid var(--border); }
  .modal-screenshot img { width: 100%; border-radius: 8px; display: block; }
  .modal-screenshot-placeholder { width: 100%; aspect-ratio: 16/9; display: flex; align-items: center; justify-content: center; color: var(--text-muted); }
  .modal-info { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; }
  .modal-info-item { padding: 10px 14px; background: var(--bg-elevated); border-radius: 8px; }
  .modal-info-label { font-size: 10px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 4px; }
  .modal-info-value { font-size: 13px; font-weight: 500; }

  /* Loading & Empty */
  .loading, .empty-state { text-align: center; padding: 80px 0; color: var(--text-muted); }
  .loading::after { content: ''; display: inline-block; width: 20px; height: 20px; border: 2px solid var(--border); border-top-color: var(--accent); border-radius: 50%; animation: spin 0.8s linear infinite; margin-left: 8px; vertical-align: middle; }
  @keyframes spin { to { transform: rotate(360deg); } }

  @media (max-width: 1100px) { .grid-2 { grid-template-columns: 1fr; } .stats-row { grid-template-columns: repeat(2, 1fr); } }
  @media (max-width: 768px) { .app { grid-template-columns: 1fr; } .sidebar { display: none; } }
</style>
</head>
<body>
<div class="app">
  <aside class="sidebar">
    <div class="logo">
      <h1><div class="logo-icon">📊</div>業務モニター</h1>
      <span>Work Analytics Dashboard</span>
    </div>
    <div class="nav-section">
      <div class="nav-label">メニュー</div>
      <div class="nav-item active" onclick="showView('dashboard')">📋 ダッシュボード</div>
    </div>
    <div class="nav-section">
      <div class="nav-label">メンバー</div>
      <div class="employee-list" id="employeeList"></div>
    </div>
  </aside>
  <main class="main" id="mainContent">
    <div class="loading">データを読み込み中</div>
  </main>
</div>

<div class="modal-overlay" id="screenshotModal">
  <div class="modal-content">
    <div class="modal-header">
      <span class="card-title" id="modalTitle">スクリーンショット</span>
      <button class="modal-close" onclick="closeModal()">✕</button>
    </div>
    <div class="modal-body" id="modalBody"></div>
  </div>
</div>

<script>
const CATEGORY_COLORS = { work: '#4f46e5', email: '#0891b2', meeting: '#f59e0b', idle: '#d1d5db', browse: '#ef4444' };

let state = { date: new Date().toISOString().split('T')[0], employees: {}, currentEmployee: null, employeeNames: [] };
let charts = {};

async function loadData(dateStr) {
  try {
    const resp = await fetch('/api/data?date=' + dateStr);
    if (!resp.ok) { state.employees = {}; state.employeeNames = []; return; }
    const data = await resp.json();
    state.employees = data.employees || {};
    state.employeeNames = Object.keys(state.employees);
    if (state.employeeNames.length > 0 && !state.currentEmployee) {
      state.currentEmployee = state.employeeNames[0];
    }
  } catch (e) {
    state.employees = {};
    state.employeeNames = [];
  }
}

function renderEmployeeList() {
  const el = document.getElementById('employeeList');
  if (state.employeeNames.length === 0) {
    el.innerHTML = '<div style="padding:12px;font-size:12px;color:var(--text-muted)">データなし</div>';
    return;
  }
  el.innerHTML = state.employeeNames.map(name => {
    const initial = name.charAt(0);
    const colors = ['#4f46e5','#0891b2','#10b981','#f59e0b','#ef4444','#8b5cf6'];
    const color = colors[name.charCodeAt(0) % colors.length];
    return '<div class="employee-item ' + (name === state.currentEmployee ? 'active' : '') + '" onclick="selectEmployee(\\'' + name.replace(/'/g,"\\\\'") + '\\')">'
      + '<div class="avatar" style="background:' + color + '18;color:' + color + '">' + initial + '</div>'
      + name + '</div>';
  }).join('');
}

function selectEmployee(name) {
  state.currentEmployee = name;
  renderEmployeeList();
  renderDashboard();
}

function renderDashboard() {
  const main = document.getElementById('mainContent');
  destroyCharts();

  if (!state.currentEmployee || !state.employees[state.currentEmployee]) {
    main.innerHTML = '<div class="empty-state">選択された従業員のデータがありません<br><br>analyzer.py を実行してデータを生成してください</div>';
    return;
  }

  const data = state.employees[state.currentEmployee];
  const s = data.summary || {};

  main.innerHTML =
    '<div class="header"><div class="header-left"><h2>' + state.currentEmployee + 'の業務レポート</h2>'
    + '<p>日次業務分析ダッシュボード</p></div>'
    + '<div class="date-nav"><button class="date-btn" onclick="changeDate(-1)">◀</button>'
    + '<span class="date-display">' + state.date + '</span>'
    + '<button class="date-btn" onclick="changeDate(1)">▶</button></div></div>'

    + '<div class="stats-row">'
    + statCard('稼働時間', s.total_hours || '-', '')
    + statCard('集中スコア', s.focus_score || '-', '', 'var(--green)')
    + statCard('メインアプリ', s.top_app || '-', (s.top_app_pct ? s.top_app_pct+'%' : ''), null, true)
    + statCard('改善提案', (data.suggestions||[]).length, '')
    + '</div>'

    + '<div class="grid-2">'
    + '<div class="card"><div class="card-header"><span class="card-title">⏱ 時間帯別アクティビティ</span></div><div class="card-body"><div id="activityBars" class="activity-bar-container"></div>'
    + '<div class="activity-legend">'
    + legendItem('var(--accent)', '業務アプリ') + legendItem('var(--cyan)', 'メール') + legendItem('var(--amber)', '電話/打合せ') + legendItem('#d1d5db', '離席') + legendItem('var(--red)', 'ブラウザ')
    + '</div></div></div>'
    + '<div class="card"><div class="card-header"><span class="card-title">📊 時間配分</span></div><div class="card-body"><div class="chart-container"><div class="chart-canvas-wrap"><canvas id="pieChart"></canvas></div><div id="pieLegend" class="chart-legend"></div></div></div></div>'
    + '</div>'

    + '<div class="grid-2">'
    + '<div class="card"><div class="card-header"><span class="card-title">📋 タイムライン</span></div><div class="card-body"><div id="timeline" class="timeline"></div></div></div>'
    + '<div class="card"><div class="card-header"><span class="card-title">💡 AI改善提案</span></div><div class="card-body" id="suggestions"></div></div>'
    + '</div>'

    + '<div class="grid-full"><div class="card"><div class="card-header"><span class="card-title">🎯 集中度の推移</span></div><div class="card-body"><div class="focus-chart-wrap"><canvas id="focusChart"></canvas></div></div></div></div>'

    + '<div class="grid-full"><div class="card"><div class="card-header"><span class="card-title">🖥 スクリーンショット</span></div><div class="card-body"><div id="screenshotsGrid" class="screenshots-grid"></div></div></div></div>';

  renderActivityBars(data);
  renderPieChart(data);
  renderTimeline(data);
  renderSuggestions(data);
  renderFocusChart(data);
  renderScreenshots(data);
}

function statCard(label, value, sub, color, small) {
  return '<div class="stat-card"><div class="stat-label">' + label + '</div>'
    + '<div class="stat-value" style="' + (color?'color:'+color+';':'') + (small?'font-size:16px;padding-top:6px;':'') + '">' + value + '</div>'
    + (sub ? '<div class="stat-sub">' + sub + '</div>' : '') + '</div>';
}

function legendItem(bg, label) {
  return '<div class="legend-item"><div class="legend-dot" style="background:' + bg + '"></div>' + label + '</div>';
}

function renderActivityBars(data) {
  const bars = data.activity_bars || {};
  const el = document.getElementById('activityBars');
  const classes = ['seg-work','seg-email','seg-meeting','seg-idle','seg-browse'];
  el.innerHTML = Object.entries(bars).sort().map(([hour, segs]) => {
    const inner = segs.map((pct,i) => pct > 0 ? '<div class="activity-segment ' + classes[i] + '" style="width:' + pct + '%"></div>' : '').join('');
    return '<div class="activity-row"><span class="activity-label">' + hour + ':00</span><div class="activity-bar-track">' + inner + '</div></div>';
  }).join('');
}

function renderPieChart(data) {
  const tb = data.time_breakdown || [];
  if (!tb.length) return;
  const ctx = document.getElementById('pieChart');
  if (!ctx) return;
  charts.pie = new Chart(ctx, {
    type: 'doughnut',
    data: { labels: tb.map(d=>d.label), datasets: [{ data: tb.map(d=>d.pct), backgroundColor: tb.map(d=>d.color), borderWidth: 0, spacing: 2 }] },
    options: { responsive: true, maintainAspectRatio: true, cutout: '65%', plugins: { legend: { display: false } } }
  });
  document.getElementById('pieLegend').innerHTML = tb.map(d =>
    '<div class="chart-legend-item"><div class="chart-legend-left"><div class="chart-legend-color" style="background:' + d.color + '"></div>' + d.label + '</div><span class="chart-legend-pct">' + d.pct + '%</span></div>'
  ).join('');
}

function renderTimeline(data) {
  const tl = data.timeline || [];
  const el = document.getElementById('timeline');
  el.innerHTML = tl.map((item, i) => {
    const color = CATEGORY_COLORS[item.category] || '#9ca3af';
    return '<div class="timeline-item"><span class="timeline-time">' + item.time + '</span>'
      + '<div class="timeline-dot-col"><div class="timeline-dot" style="background:' + color + '"></div>'
      + (i < tl.length-1 ? '<div class="timeline-line"></div>' : '') + '</div>'
      + '<div class="timeline-content"><div class="timeline-label">' + item.label + '</div>'
      + '<div class="timeline-desc">' + (item.desc||'') + '</div></div></div>';
  }).join('');
}

function renderSuggestions(data) {
  const sg = data.suggestions || [];
  const el = document.getElementById('suggestions');
  if (!sg.length) { el.innerHTML = '<div style="color:var(--text-muted);font-size:13px">改善提案なし</div>'; return; }
  const levelLabels = { high: '優先度 高', mid: '優先度 中', low: '優先度 低' };
  el.innerHTML = sg.map(s =>
    '<div class="suggestion suggestion-' + s.level + '"><div class="suggestion-tag">' + (levelLabels[s.level]||s.level) + '</div>'
    + '<div class="suggestion-title">' + s.title + '</div><div class="suggestion-desc">' + s.desc + '</div></div>'
  ).join('');
}

function renderFocusChart(data) {
  const fd = data.focus_data || [];
  if (!fd.length) return;
  const ctx = document.getElementById('focusChart');
  if (!ctx) return;
  const labels = fd.map((_,i) => (9+i).toString().padStart(2,'0') + ':00');
  charts.focus = new Chart(ctx, {
    type: 'line',
    data: { labels, datasets: [{ data: fd, borderColor: '#4f46e5', backgroundColor: 'rgba(79,70,229,0.06)', borderWidth: 2, fill: true, tension: 0.4, pointRadius: 4, pointBackgroundColor: '#4f46e5', pointBorderColor: '#fff', pointBorderWidth: 2 }] },
    options: { responsive: true, maintainAspectRatio: false, scales: { y: { min:0, max:100, grid:{color:'#e2e4ea'}, ticks:{color:'#8e92a2',font:{size:11,family:'JetBrains Mono'},stepSize:25} }, x: { grid:{color:'#e2e4ea'}, ticks:{color:'#8e92a2',font:{size:11,family:'JetBrains Mono'}} } }, plugins: { legend: { display: false } } }
  });
}

function renderScreenshots(data) {
  const el = document.getElementById('screenshotsGrid');
  // スクショはAPI経由で取得可能な場合のみ表示
  // ここではログからタイムスタンプを表示
  const tl = data.timeline || [];
  el.innerHTML = tl.map((item, i) =>
    '<div class="screenshot-thumb" onclick="openScreenshotModal(' + i + ')"><div class="screenshot-placeholder"><span class="time">' + item.time + '</span><span class="app-name">' + item.label + '</span></div></div>'
  ).join('');
}

function openScreenshotModal(index) {
  const data = state.employees[state.currentEmployee];
  const item = (data.timeline || [])[index];
  if (!item) return;
  document.getElementById('modalTitle').textContent = 'スクリーンショット - ' + item.time;
  document.getElementById('modalBody').innerHTML =
    '<div class="modal-screenshot"><div class="modal-screenshot-placeholder" style="aspect-ratio:16/9">📸 ' + item.time + ' - 実データでは実際のスクリーンショットが表示されます</div></div>'
    + '<div class="modal-info"><div class="modal-info-item"><div class="modal-info-label">時刻</div><div class="modal-info-value">' + item.time + '</div></div>'
    + '<div class="modal-info-item"><div class="modal-info-label">作業内容</div><div class="modal-info-value">' + item.label + '</div></div></div>';
  document.getElementById('screenshotModal').classList.add('active');
}

function closeModal() { document.getElementById('screenshotModal').classList.remove('active'); }
document.getElementById('screenshotModal').addEventListener('click', e => { if (e.target === e.currentTarget) closeModal(); });

function destroyCharts() { Object.values(charts).forEach(c => c.destroy()); charts = {}; }

async function changeDate(delta) {
  const d = new Date(state.date);
  d.setDate(d.getDate() + delta);
  state.date = d.toISOString().split('T')[0];
  state.currentEmployee = null;
  await loadData(state.date);
  renderEmployeeList();
  renderDashboard();
}

// 初期化
(async () => {
  await loadData(state.date);
  renderEmployeeList();
  renderDashboard();
})();
</script>
</body>
</html>"""


class DashboardHandler(http.server.BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # ログを抑制

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)

        if parsed.path == "/" or parsed.path == "":
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.end_headers()
            self.wfile.write(DASHBOARD_HTML.encode("utf-8"))

        elif parsed.path == "/api/data":
            params = urllib.parse.parse_qs(parsed.query)
            date_str = params.get("date", [date.today().strftime("%Y-%m-%d")])[0]

            data_file = REPORT_DIR / f"data_{date_str}.json"
            if data_file.exists():
                with open(data_file, "r", encoding="utf-8") as f:
                    data = f.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.end_headers()
                self.wfile.write(data.encode("utf-8"))
            else:
                self.send_response(404)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"error": "not found"}')

        elif parsed.path.startswith("/api/screenshot"):
            # スクリーンショット画像を配信
            params = urllib.parse.parse_qs(parsed.query)
            emp = params.get("employee", [""])[0]
            date_str = params.get("date", [""])[0]
            filename = params.get("file", [""])[0]

            if emp and date_str and filename:
                img_path = GDRIVE_BASE / emp / date_str / filename
                if img_path.exists() and img_path.suffix.lower() in (".jpg", ".jpeg", ".png"):
                    self.send_response(200)
                    ct = "image/jpeg" if img_path.suffix.lower() in (".jpg", ".jpeg") else "image/png"
                    self.send_header("Content-Type", ct)
                    self.end_headers()
                    with open(img_path, "rb") as f:
                        self.wfile.write(f.read())
                    return

            self.send_response(404)
            self.end_headers()

        else:
            self.send_response(404)
            self.end_headers()


def main():
    REPORT_DIR.mkdir(parents=True, exist_ok=True)

    server = http.server.HTTPServer(("0.0.0.0", PORT), DashboardHandler)
    print(f"{'='*50}")
    print(f"  業務モニター ダッシュボード")
    print(f"  http://localhost:{PORT}")
    print(f"  データ: {REPORT_DIR}")
    print(f"  停止: Ctrl+C")
    print(f"{'='*50}")

    try:
        import webbrowser
        webbrowser.open(f"http://localhost:{PORT}")
    except Exception:
        pass

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[STOP] サーバーを停止しました")
        server.server_close()


if __name__ == "__main__":
    main()
