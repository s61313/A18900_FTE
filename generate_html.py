#!/usr/bin/env python3
import csv, os, glob, json
from datetime import datetime

DATA_DIR = "data"
REPORT_DIR = "reports"
OUTPUT_FILE = "index.html"


def find_sorted_files():
    files = glob.glob(os.path.join(DATA_DIR, "49YTW_portfolio_????????.csv"))
    files.sort()
    return files


def parse_date_str(filepath):
    return os.path.basename(filepath).replace("49YTW_portfolio_", "").replace(".csv", "")


def load_all_csvs():
    """Return {date_str: {code: {name, shares, weight}}} sorted by date asc."""
    history = {}
    for f in find_sorted_files():
        date = parse_date_str(f)
        day = {}
        with open(f, newline="", encoding="utf-8-sig") as fp:
            for row in csv.DictReader(fp):
                code = row["股票代號"].strip()
                try:
                    shares = int(row["股數"].strip().replace(",", ""))
                    weight = float(row["持股權重"].strip().replace("%", ""))
                except ValueError:
                    continue
                day[code] = {"name": row["股票名稱"].strip(), "shares": shares, "weight": weight}
        history[date] = day
    return history


def get_latest_date_label(history):
    dates = sorted(history.keys())
    if not dates:
        return ""
    d = dates[-1]
    return f"{d[:4]}/{d[4:6]}/{d[6:]}"


def build_html(history):
    dates = sorted(history.keys())
    latest = dates[-1] if dates else ""
    date_label = f"{latest[:4]}/{latest[4:6]}/{latest[6:]}" if latest else ""
    history_json = json.dumps(history, ensure_ascii=False)
    dates_json = json.dumps(dates)

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>49YTW 持股追蹤</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }}
    header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 1px solid #334155; padding: 20px 32px; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
    header h1 {{ font-size: 1.4rem; font-weight: 700; color: #f8fafc; }}
    header p {{ color: #94a3b8; font-size: 0.82rem; margin-left: auto; }}
    .badge {{ display: inline-block; background: #1e40af; color: #93c5fd; font-size: 0.68rem; padding: 2px 8px; border-radius: 999px; margin-left: 8px; vertical-align: middle; }}
    main {{ max-width: 1280px; margin: 0 auto; padding: 24px 20px; }}

    /* Controls */
    .controls {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; padding: 14px 20px; margin-bottom: 20px; display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
    .controls label {{ font-size: 0.8rem; color: #94a3b8; }}
    .controls select {{ background: #0f172a; border: 1px solid #334155; color: #e2e8f0; border-radius: 6px; padding: 5px 10px; font-size: 0.82rem; cursor: pointer; }}
    .controls select:focus {{ outline: none; border-color: #3b82f6; }}
    .controls .sep {{ color: #475569; font-size: 1rem; }}
    .mode-badge {{ font-size: 0.72rem; padding: 3px 10px; border-radius: 999px; font-weight: 600; }}
    .mode-single {{ background: #1e3a5f; color: #60a5fa; }}
    .mode-multi {{ background: #1a3a2a; color: #4ade80; }}

    /* Summary cards */
    .cards {{ display: flex; gap: 12px; flex-wrap: wrap; margin-bottom: 20px; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 14px 18px; min-width: 120px; flex: 1; }}
    .card .label {{ font-size: 0.7rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 5px; }}
    .card .value {{ font-size: 1.7rem; font-weight: 700; color: #f1f5f9; }}
    .card .value.pos {{ color: #4ade80; }}
    .card .value.neg {{ color: #f87171; }}
    .card .value.warn {{ color: #fbbf24; }}

    /* Sections */
    section {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; margin-bottom: 20px; overflow: hidden; }}
    .sec-header {{ padding: 14px 20px; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }}
    .sec-header h2 {{ font-size: 0.95rem; font-weight: 600; color: #f1f5f9; }}
    .count {{ background: #334155; color: #94a3b8; font-size: 0.7rem; padding: 2px 8px; border-radius: 999px; }}
    .hint {{ color: #475569; font-size: 0.75rem; margin-left: auto; }}

    /* Streak section */
    .streak-body {{ padding: 14px 20px; display: flex; flex-direction: column; gap: 10px; }}
    .streak-row {{ display: flex; align-items: flex-start; gap: 10px; flex-wrap: wrap; }}
    .streak-label {{ font-size: 0.78rem; color: #94a3b8; white-space: nowrap; padding-top: 2px; min-width: 60px; }}
    .streak-chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
    .chip {{ display: inline-flex; align-items: center; gap: 5px; border-radius: 6px; padding: 3px 10px; font-size: 0.78rem; font-weight: 600; }}
    .chip-buy {{ background: #14532d; color: #4ade80; }}
    .chip-sell {{ background: #450a0a; color: #f87171; }}
    .chip .chip-code {{ font-family: monospace; }}
    .chip .chip-name {{ color: inherit; opacity: 0.8; font-weight: 400; }}
    .streak-empty {{ color: #475569; font-style: italic; font-size: 0.82rem; padding: 8px 0; }}

    /* Table */
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.84rem; }}
    thead tr {{ background: #0f172a; }}
    th {{ padding: 10px 13px; text-align: left; color: #64748b; font-weight: 500; font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; user-select: none; cursor: pointer; }}
    th:hover {{ color: #94a3b8; }}
    th .si {{ display: inline-block; margin-left: 3px; opacity: 0.25; font-style: normal; font-size: 0.65rem; }}
    th.asc .si, th.desc .si {{ opacity: 1; }}
    th.desc .si {{ display: inline-block; transform: rotate(180deg); }}
    td {{ padding: 8px 13px; border-top: 1px solid #1e293b; color: #cbd5e1; white-space: nowrap; }}
    tbody tr:hover {{ background: #1e3248; }}
    .code {{ font-family: monospace; color: #93c5fd; font-size: 0.84rem; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .pos {{ color: #4ade80; font-weight: 600; }}
    .neg {{ color: #f87171; font-weight: 600; }}
    .zero {{ color: #475569; }}
    .hidden {{ display: none !important; }}

    /* Weight bar */
    .w-wrap {{ display: flex; align-items: center; gap: 7px; }}
    .w-bar {{ height: 5px; background: linear-gradient(90deg, #3b82f6, #6366f1); border-radius: 3px; min-width: 2px; flex-shrink: 0; }}
    .w-lbl {{ color: #93c5fd; font-variant-numeric: tabular-nums; font-size: 0.8rem; }}

    /* Streak badges in table */
    .streak-tag {{ display: inline-block; font-size: 0.65rem; font-weight: 700; padding: 1px 5px; border-radius: 4px; margin-left: 5px; vertical-align: middle; }}
    .streak-tag.buy {{ background: #14532d; color: #4ade80; }}
    .streak-tag.sell {{ background: #450a0a; color: #f87171; }}
    .badge-new {{ font-size: 0.68rem; background: #1e3a5f; color: #60a5fa; border-radius: 4px; padding: 1px 6px; }}

    .empty {{ color: #475569; padding: 14px 20px; font-style: italic; font-size: 0.82rem; }}
    footer {{ text-align: center; padding: 20px; color: #475569; font-size: 0.75rem; }}

    /* 名稱點擊選單 */
    td.name-cell {{ cursor: pointer; }}
    td.name-cell:hover {{ color: #e2e8f0; text-decoration: underline dotted #475569; }}
    #stock-menu {{ position: fixed; z-index: 9999; background: #1e293b; border: 1px solid #334155;
      border-radius: 10px; box-shadow: 0 8px 28px rgba(0,0,0,.6); padding: 6px 0; min-width: 248px;
      display: none; }}
    #stock-menu.show {{ display: block; }}
    #stock-menu .menu-header {{ padding: 8px 14px 6px; font-size: 0.78rem; font-weight: 600;
      color: #e2e8f0; border-bottom: 1px solid #334155; }}
    #stock-menu a {{ display: flex; align-items: center; gap: 8px; padding: 8px 14px;
      color: #cbd5e1; font-size: 0.84rem; text-decoration: none; white-space: nowrap; }}
    #stock-menu a:hover {{ background: #263148; color: #e2e8f0; }}
    #stock-menu a .menu-icon {{ font-size: 1rem; width: 20px; text-align: center; }}
    #stock-menu .menu-links {{ border-top: 1px solid #334155; }}

    /* 走勢圖 */
    .spark-wrap {{ padding: 10px 14px 6px; }}
    .spark-meta {{ display: flex; justify-content: space-between; font-size: 0.7rem;
      color: #64748b; margin-bottom: 6px; }}
    .spark-meta .diff-pos {{ color: #4ade80; font-weight: 600; }}
    .spark-meta .diff-neg {{ color: #f87171; font-weight: 600; }}
    .spark-meta .diff-flat {{ color: #64748b; }}
    .spark-svg {{ display: block; overflow: visible; }}
    .spark-empty {{ color: #475569; font-size: 0.75rem; padding: 8px 0; font-style: italic; }}

    /* 權重變化 mini bar */
    .wc-wrap {{ display: flex; align-items: center; gap: 6px; }}
    .wc-txt {{ min-width: 50px; text-align: right; font-variant-numeric: tabular-nums; font-size: 0.82rem; }}
    .wc-track {{ width: 50px; height: 5px; background: #0f172a; border-radius: 3px; overflow: hidden; flex-shrink: 0; }}
    .wc-fill {{ height: 100%; border-radius: 3px; }}

    /* 代號複製提示 */
    td.code {{ cursor: pointer; position: relative; }}
    td.code:hover {{ color: #bfdbfe; }}
    .copy-toast {{ position: fixed; bottom: 28px; left: 50%; transform: translateX(-50%);
      background: #1e3a5f; color: #93c5fd; font-size: 0.8rem; padding: 6px 16px;
      border-radius: 999px; pointer-events: none; opacity: 0; transition: opacity .2s;
      z-index: 9999; }}

    @media (max-width: 640px) {{
      header {{ padding: 14px 16px; }}
      .cards {{ gap: 8px; }}
      .card .value {{ font-size: 1.4rem; }}
      th, td {{ padding: 6px 9px; }}
      .controls {{ gap: 8px; }}
    }}
  </style>
</head>
<body>
<header>
  <h1>49YTW 持股追蹤 <span class="badge">自動更新</span></h1>
  <p id="hdr-date">最新資料：{date_label}</p>
</header>
<main>

  <!-- 比較區間控制 -->
  <div class="controls">
    <label>比較區間：</label>
    <select id="sel-start"></select>
    <span class="sep">→</span>
    <select id="sel-end"></select>
    <span id="mode-badge" class="mode-badge mode-single">單日</span>
  </div>

  <!-- 摘要卡片 -->
  <div class="cards">
    <div class="card"><div class="label">持股總數</div><div class="value" id="c-total">—</div></div>
    <div class="card"><div class="label">新增</div><div class="value pos" id="c-add">—</div></div>
    <div class="card"><div class="label">刪除</div><div class="value neg" id="c-del">—</div></div>
    <div class="card"><div class="label">比較區間</div><div class="value" id="c-range" style="font-size:0.85rem;line-height:1.4">—</div></div>
  </div>

  <!-- 連續動態 -->
  <section id="streak-sec">
    <div class="sec-header">
      <h2>🔥 連續動態</h2>
      <span class="hint">依全部歷史資料計算</span>
    </div>
    <div class="streak-body" id="streak-body"></div>
  </section>

  <!-- 主表格 -->
  <section>
    <div class="sec-header">
      <h2>📋 今日持股 &amp; 異動</h2>
      <span class="count" id="tbl-count">—</span>
      <span class="hint">點擊欄位標題排序</span>
    </div>
    <div class="table-wrap">
      <table id="main-table">
        <thead>
          <tr>
            <th data-col="0">代號<i class="si">▲</i></th>
            <th data-col="1">名稱<i class="si">▲</i></th>
            <th data-col="2" class="num">今日張數<i class="si">▲</i></th>
            <th data-col="3">持股權重<i class="si">▲</i></th>
            <th data-col="4" class="num" id="th-chg"><span>張數變化</span><i class="si">▲</i></th>
            <th data-col="5" class="num" id="th-pw">前日權重<i class="si">▲</i></th>
            <th data-col="6" id="th-wc"><span>權重變化</span><i class="si">▲</i></th>
          </tr>
        </thead>
        <tbody id="main-tbody"></tbody>
      </table>
    </div>
  </section>

  <!-- 刪除股票 -->
  <section id="removed-sec">
    <div class="sec-header">
      <h2>🔴 刪除股票</h2>
      <span class="count" id="del-count">0 檔</span>
    </div>
    <div id="removed-body"></div>
  </section>

</main>
<footer>資料來源：49YTW 基金 &nbsp;·&nbsp; 每個交易日 18:00 自動更新 &nbsp;·&nbsp; 張數 = 股數 ÷ 1,000</footer>

<!-- 股票名稱浮動選單 -->
<div id="stock-menu">
  <div class="menu-header" id="menu-title"></div>
  <div class="spark-wrap" id="menu-sparkline"></div>
  <div class="menu-links">
    <a id="menu-overview" href="#" target="_blank" rel="noopener">
      <span class="menu-icon">📊</span>概況
    </a>
    <a id="menu-major" href="#" target="_blank" rel="noopener">
      <span class="menu-icon">🏦</span>大戶籌碼
    </a>
    <a id="menu-trend" href="#" target="_blank" rel="noopener">
      <span class="menu-icon">📈</span>主力動向
    </a>
  </div>
</div>

<!-- 複製提示 toast -->
<div class="copy-toast" id="copy-toast"></div>

<script>
(function () {{
  // ── 歷史資料（Python 嵌入）──────────────────────────────
  const HISTORY = {history_json};
  const DATES   = {dates_json};  // ascending

  // ── 工具函式 ─────────────────────────────────────────────
  function dateLabel(d) {{
    return d.slice(0,4) + '/' + d.slice(4,6) + '/' + d.slice(6,8);
  }}
  function toZhang(shares) {{ return Math.floor(shares / 1000); }}
  function fmtN(n) {{ return n.toLocaleString('zh-TW'); }}
  function fmtDiff(n) {{
    if (n === 0) return '—';
    return (n > 0 ? '+' : '') + fmtN(n);
  }}
  function fmtW(w) {{
    if (w === null || w === undefined) return '—';
    return w.toFixed(2) + '%';
  }}
  function fmtWDiff(w) {{
    if (w === 0) return '—';
    return (w > 0 ? '+' : '') + w.toFixed(2) + '%';
  }}
  function cls(n) {{
    if (n > 0) return 'pos'; if (n < 0) return 'neg'; return 'zero';
  }}

  // ── 連續買賣計算（全歷史）───────────────────────────────
  function computeStreaks() {{
    const all = {{}};
    DATES.forEach(d => Object.keys(HISTORY[d] || {{}}).forEach(c => (all[c] = true)));
    const streaks = {{}};
    for (const code of Object.keys(all)) {{
      let count = 0, dir = null;
      for (let i = 1; i < DATES.length; i++) {{
        const p = HISTORY[DATES[i-1]]?.[code];
        const c = HISTORY[DATES[i]]?.[code];
        if (!p || !c) {{ count = 0; dir = null; continue; }}
        const diff = c.shares - p.shares;
        const d = diff > 0 ? 'buy' : diff < 0 ? 'sell' : null;
        if (!d) {{ count = 0; dir = null; }}
        else if (d === dir) {{ count++; }}
        else {{ count = 1; dir = d; }}
      }}
      if (count >= 1 && dir) streaks[code] = {{ dir, count }};
    }};
    return streaks;
  }}

  // ── 比較兩個日期 ─────────────────────────────────────────
  function compare(startDate, endDate) {{
    const start = HISTORY[startDate] || {{}};
    const end   = HISTORY[endDate]   || {{}};
    const allCodes = new Set([...Object.keys(start), ...Object.keys(end)]);
    const result = {{ added: [], removed: [], rows: [] }};

    for (const code of allCodes) {{
      const s = start[code], e = end[code];
      if (!s && e)  {{ result.added.push({{ code, ...e }}); continue; }}
      if (s && !e)  {{ result.removed.push({{ code, ...s }}); continue; }}
      const sharesDiff = e.shares - s.shares;
      const weightDiff = parseFloat((e.weight - s.weight).toFixed(2));
      result.rows.push({{
        code, name: e.name,
        shares: e.shares, weight: e.weight,
        prevShares: s.shares, prevWeight: s.weight,
        sharesDiff, weightDiff,
        changed: sharesDiff !== 0 || weightDiff !== 0,
      }});
    }}
    return result;
  }}

  // ── 渲染連續動態 ─────────────────────────────────────────
  function renderStreaks(streaks) {{
    const buys  = Object.entries(streaks).filter(([,v]) => v.dir==='buy' && v.count>=2)
                    .sort((a,b) => b[1].count - a[1].count);
    const sells = Object.entries(streaks).filter(([,v]) => v.dir==='sell' && v.count>=2)
                    .sort((a,b) => b[1].count - a[1].count);

    const body = document.getElementById('streak-body');
    const lastDay = HISTORY[DATES[DATES.length-1]] || {{}};

    function chips(list, cls) {{
      if (!list.length) return `<span class="streak-empty">無</span>`;
      return list.map(([code, v]) => {{
        const name = lastDay[code]?.name || HISTORY[DATES[0]]?.[code]?.name || '';
        const label = v.dir==='buy' ? `連${{v.count}}買` : `連${{v.count}}賣`;
        return `<span class="chip chip-${{v.dir==='buy'?'buy':'sell'}}">
          <span class="chip-code">${{code}}</span>
          <span class="chip-name">${{name}}</span>
          <strong>${{label}}</strong>
        </span>`;
      }}).join('');
    }}

    body.innerHTML = `
      <div class="streak-row">
        <span class="streak-label">📈 連續買進</span>
        <div class="streak-chips">${{chips(buys,'buy')}}</div>
      </div>
      <div class="streak-row">
        <span class="streak-label">📉 連續賣出</span>
        <div class="streak-chips">${{chips(sells,'sell')}}</div>
      </div>`;
  }}

  // ── 渲染主表格 ───────────────────────────────────────────
  let sortCol = 3, sortAsc = false;

  function renderTable(cmp, streaks, isMulti) {{
    // 欄位可見性
    document.getElementById('th-chg').querySelector('span').textContent = isMulti ? '累計張數變化' : '張數變化';
    document.getElementById('th-pw').classList.toggle('hidden', isMulti);
    document.getElementById('th-wc').querySelector('span').textContent = isMulti ? '累計權重變化' : '權重變化';

    // 組合所有行：added + rows（含 changed 與 unchanged）
    const lastDay = HISTORY[DATES[DATES.length-1]] || {{}};
    const addedCodes = new Set(cmp.added.map(r => r.code));
    const allRows = [
      ...cmp.added.map(r => ({{ ...r, isAdded: true, sharesDiff: r.shares, weightDiff: r.weight }})),
      ...cmp.rows,
    ];

    // 排序
    function getVal(row) {{
      switch (sortCol) {{
        case 0: return row.code;
        case 1: return row.name;
        case 2: return toZhang(row.shares);
        case 3: return row.weight;
        case 4: return row.isAdded ? 1e9 : row.sharesDiff;
        case 5: return row.isAdded ? 1e9 : (row.prevWeight ?? 0);
        case 6: return row.isAdded ? 1e9 : row.weightDiff;
        default: return 0;
      }}
    }}
    allRows.sort((a, b) => {{
      const va = getVal(a), vb = getVal(b);
      if (typeof va === 'string') return sortAsc ? va.localeCompare(vb,'zh-Hant') : vb.localeCompare(va,'zh-Hant');
      return sortAsc ? va - vb : vb - va;
    }});

    const tbody = document.getElementById('main-tbody');
    tbody.innerHTML = allRows.map(row => {{
      const zhang = toZhang(row.shares);
      const barW  = Math.min(Math.floor(row.weight * 8), 100);
      const stk   = streaks[row.code];
      const stkTag = (stk && stk.count >= 2)
        ? `<span class="streak-tag ${{stk.dir==='buy'?'buy':'sell'}}">連${{stk.count}}${{stk.dir==='buy'?'買':'賣'}}</span>`
        : '';

      // 張數變化欄
      let chgCell;
      if (row.isAdded) {{
        chgCell = `<td class="num" data-sort="1000000"><span class="badge-new">新增</span></td>`;
      }} else {{
        const zdiff = toZhang(Math.abs(row.sharesDiff)) * Math.sign(row.sharesDiff);
        const zdiffTxt = fmtDiff(zdiff);
        chgCell = `<td class="num ${{cls(zdiff)}}" data-sort="${{zdiff}}">${{zdiffTxt}}${{stkTag}}</td>`;
      }}

      // 前日權重（單日才顯示）& 權重變化/累計權重變化（兩模式皆顯示）
      const pwCell = `<td class="num ${{isMulti?'hidden':''}}" data-sort="${{row.prevWeight??0}}">${{row.isAdded ? '—' : fmtW(row.prevWeight)}}</td>`;
      const wcCell = `<td data-sort="${{row.weightDiff??0}}">${{row.isAdded ? '—' : wcBar(row.weightDiff)}}</td>`;

      return `<tr>
        <td class="code" data-sort="${{row.code}}" data-code="${{row.code}}">${{row.code}}</td>
        <td class="name-cell" data-sort="${{row.name}}" data-code="${{row.code}}" data-name="${{row.name}}">${{row.name}}</td>
        <td class="num" data-sort="${{zhang}}">${{fmtN(zhang)}}</td>
        <td data-sort="${{row.weight}}">
          <div class="w-wrap">
            <div class="w-bar" style="width:${{barW}}%"></div>
            <span class="w-lbl">${{row.weight.toFixed(2)}}%</span>
          </div>
        </td>
        ${{chgCell}}${{pwCell}}${{wcCell}}
      </tr>`;
    }}).join('');

    document.getElementById('tbl-count').textContent = allRows.length + ' 檔';
    updateSortHeaders();
  }}

  // ── 渲染刪除區塊 ─────────────────────────────────────────
  function renderRemoved(removed) {{
    const el = document.getElementById('removed-body');
    document.getElementById('del-count').textContent = removed.length + ' 檔';
    if (!removed.length) {{ el.innerHTML = "<p class='empty'>無刪除股票</p>"; return; }}
    el.innerHTML = `<div class="table-wrap"><table>
      <thead><tr><th>代號</th><th>名稱</th><th>原張數</th><th>原權重</th></tr></thead>
      <tbody>${{removed.map(r => `<tr>
        <td class="code" data-code="${{r.code}}">${{r.code}}</td>
        <td class="name-cell" data-code="${{r.code}}" data-name="${{r.name}}">${{r.name}}</td>
        <td class="num neg">${{fmtN(toZhang(r.shares))}}</td>
        <td class="neg">${{r.weight.toFixed(2)}}%</td>
      </tr>`).join('')}}</tbody>
    </table></div>`;
  }}

  // ── 排序邏輯 ─────────────────────────────────────────────
  function updateSortHeaders() {{
    document.querySelectorAll('#main-table th').forEach((th, i) => {{
      th.classList.remove('asc','desc');
      if (i === sortCol) th.classList.add(sortAsc ? 'asc' : 'desc');
    }});
  }}

  document.getElementById('main-table').addEventListener('click', e => {{
    const th = e.target.closest('th');
    if (!th) return;
    const col = parseInt(th.dataset.col);
    if (isNaN(col)) return;
    if (sortCol === col) sortAsc = !sortAsc;
    else {{ sortCol = col; sortAsc = col <= 1; }}  // 文字欄預設升冪，數值欄降冪
    refresh();
  }});

  // ── 主流程 ───────────────────────────────────────────────
  const streaks = computeStreaks();

  function populateSelects() {{
    const ss = document.getElementById('sel-start');
    const se = document.getElementById('sel-end');
    DATES.forEach(d => {{
      ss.appendChild(Object.assign(document.createElement('option'), {{ value: d, textContent: dateLabel(d) }}));
      se.appendChild(Object.assign(document.createElement('option'), {{ value: d, textContent: dateLabel(d) }}));
    }});
    // 預設：前一天 → 最新
    if (DATES.length >= 2) ss.value = DATES[DATES.length - 2];
    se.value = DATES[DATES.length - 1];
  }}

  function refresh() {{
    const sd = document.getElementById('sel-start').value;
    const ed = document.getElementById('sel-end').value;
    const isMulti = DATES.indexOf(ed) - DATES.indexOf(sd) > 1;
    const cmp = compare(sd, ed);

    // mode badge
    const mb = document.getElementById('mode-badge');
    mb.textContent = isMulti ? '多日累計' : '單日';
    mb.className = 'mode-badge ' + (isMulti ? 'mode-multi' : 'mode-single');

    // cards
    const total = cmp.rows.length + cmp.added.length;
    document.getElementById('c-total').textContent = total;
    document.getElementById('c-add').textContent   = cmp.added.length;
    document.getElementById('c-del').textContent   = cmp.removed.length;
    document.getElementById('c-range').textContent = dateLabel(sd) + ' → ' + dateLabel(ed);

    renderTable(cmp, streaks, isMulti);
    renderRemoved(cmp.removed);
  }}

  document.getElementById('sel-start').addEventListener('change', refresh);
  document.getElementById('sel-end').addEventListener('change', refresh);

  populateSelects();
  renderStreaks(streaks);
  refresh();

  // ── 權重變化 mini bar ────────────────────────────────────
  function wcBar(wc) {{
    if (wc === 0) return '<span class="zero">—</span>';
    const scale = Math.min(Math.abs(wc) / 1.5 * 100, 100);
    const color = wc > 0 ? '#4ade80' : '#f87171';
    const txtCls = wc > 0 ? 'pos' : 'neg';
    return `<div class="wc-wrap">
      <span class="wc-txt ${{txtCls}}">${{fmtWDiff(wc)}}</span>
      <div class="wc-track"><div class="wc-fill" style="width:${{scale.toFixed(1)}}%;background:${{color}}"></div></div>
    </div>`;
  }}

  // ── 走勢圖 SVG ───────────────────────────────────────────
  function buildSparkline(code) {{
    const pts = DATES.map(d => {{
      const s = HISTORY[d]?.[code];
      return s ? {{ d, z: Math.floor(s.shares / 1000) }} : null;
    }}).filter(Boolean);

    if (pts.length < 2) return '<p class="spark-empty">歷史資料不足</p>';

    const W = 220, H = 58;
    const pad = {{ t: 6, r: 8, b: 18, l: 8 }};
    const pw = W - pad.l - pad.r, ph = H - pad.t - pad.b;
    const vals = pts.map(p => p.z);
    const minV = Math.min(...vals), maxV = Math.max(...vals);
    const range = maxV - minV || 1;

    const px = i => pad.l + (pts.length < 2 ? pw/2 : i * pw / (pts.length - 1));
    const py = v => pad.t + ph - (v - minV) / range * ph;

    const polyPts = pts.map((p, i) => `${{px(i).toFixed(1)}},${{py(p.z).toFixed(1)}}`).join(' ');
    const dots = pts.map((p, i) => {{
      const isLast = i === pts.length - 1;
      return `<circle cx="${{px(i).toFixed(1)}}" cy="${{py(p.z).toFixed(1)}}" r="${{isLast ? 3.5 : 2.5}}"
        fill="${{isLast ? '#60a5fa' : '#334155'}}" stroke="${{isLast ? '#1e293b' : 'none'}}" stroke-width="1.5"/>`;
    }}).join('');
    const labels = [
      `<text x="${{pad.l}}" y="${{H}}" font-size="9" fill="#475569" text-anchor="start">${{pts[0].d.slice(4,6)}}/${{pts[0].d.slice(6,8)}}</text>`,
      pts.length > 2 ? `<text x="${{(W/2).toFixed(0)}}" y="${{H}}" font-size="9" fill="#334155" text-anchor="middle">${{pts[Math.floor(pts.length/2)].d.slice(4,6)}}/${{pts[Math.floor(pts.length/2)].d.slice(6,8)}}</text>` : '',
      `<text x="${{W - pad.r}}" y="${{H}}" font-size="9" fill="#475569" text-anchor="end">${{pts[pts.length-1].d.slice(4,6)}}/${{pts[pts.length-1].d.slice(6,8)}}</text>`,
    ].join('');

    const diff = pts[pts.length-1].z - pts[0].z;
    const diffCls = diff > 0 ? 'diff-pos' : diff < 0 ? 'diff-neg' : 'diff-flat';
    const diffTxt = diff === 0 ? '持平' : (diff > 0 ? `+${{diff.toLocaleString()}}` : diff.toLocaleString()) + ' 張';

    return `
      <div class="spark-meta">
        <span>${{pts[0].z.toLocaleString()}} 張</span>
        <span class="${{diffCls}}">${{diffTxt}}</span>
        <span>${{pts[pts.length-1].z.toLocaleString()}} 張</span>
      </div>
      <svg class="spark-svg" viewBox="0 0 ${{W}} ${{H}}" width="${{W}}" height="${{H}}">
        <polyline points="${{polyPts}}" fill="none" stroke="#3b82f6" stroke-width="2"
          stroke-linejoin="round" stroke-linecap="round"/>
        ${{dots}}
        ${{labels}}
      </svg>`;
  }}

  // ── 名稱欄：浮動選單 ─────────────────────────────────────
  const menu = document.getElementById('stock-menu');
  function openMenu(code, name, x, y) {{
    const base = `https://www.wantgoo.com/stock/${{code}}`;
    document.getElementById('menu-title').textContent        = `${{code}}　${{name}}`;
    document.getElementById('menu-sparkline').innerHTML      = buildSparkline(code);
    document.getElementById('menu-overview').href            = base;
    document.getElementById('menu-major').href               = base + '/major-investors/concentration';
    document.getElementById('menu-trend').href               = base + '/major-investors/main-trend';
    // 定位：避免跑出視窗右側/下方
    menu.style.left = '0'; menu.style.top = '0';
    menu.classList.add('show');
    const mw = menu.offsetWidth, mh = menu.offsetHeight;
    const vw = window.innerWidth, vh = window.innerHeight;
    menu.style.left = (x + mw > vw ? vw - mw - 8 : x) + 'px';
    menu.style.top  = (y + mh > vh ? y - mh - 4  : y + 4) + 'px';
  }}
  function closeMenu() {{ menu.classList.remove('show'); }}

  document.body.addEventListener('click', e => {{
    const td = e.target.closest('td.name-cell');
    if (!td) return;
    e.stopPropagation();
    openMenu(td.dataset.code, td.dataset.name, e.clientX, e.clientY);
  }});
  document.addEventListener('click', e => {{
    if (!menu.contains(e.target)) closeMenu();
  }});
  document.addEventListener('keydown', e => {{ if (e.key === 'Escape') closeMenu(); }});

  // ── 代號欄：複製到剪貼簿 ─────────────────────────────────
  const toast = document.getElementById('copy-toast');
  let toastTimer;
  document.body.addEventListener('click', e => {{
    const td = e.target.closest('td.code');
    if (!td) return;
    const code = td.dataset.code;
    navigator.clipboard.writeText(code).then(() => {{
      clearTimeout(toastTimer);
      toast.textContent = `已複製 ${{code}}`;
      toast.style.opacity = '1';
      toastTimer = setTimeout(() => {{ toast.style.opacity = '0'; }}, 1800);
    }});
  }});
}})();
</script>
</body>
</html>"""


def main():
    history = load_all_csvs()
    if not history:
        print("找不到持股 CSV，跳過。")
        return
    html = build_html(history)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已產生 {OUTPUT_FILE}（{len(history)} 個日期）")


if __name__ == "__main__":
    main()
