#!/usr/bin/env python3
import csv, os, glob, re
from datetime import datetime

DATA_DIR = "data"
REPORT_DIR = "reports"
OUTPUT_FILE = "index.html"


def load_csv(filepath):
    result = []
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            result.append({
                "code": row["股票代號"].strip(),
                "name": row["股票名稱"].strip(),
                "shares": row["股數"].strip(),
                "weight": row["持股權重"].strip(),
            })
    return result


def find_sorted_files():
    files = glob.glob(os.path.join(DATA_DIR, "49YTW_portfolio_????????.csv"))
    files.sort(reverse=True)
    return files


def parse_date_label(date_str):
    return f"{date_str[:4]}/{date_str[4:6]}/{date_str[6:]}"


def load_latest_diff_md():
    path = os.path.join(REPORT_DIR, "latest_diff.md")
    if not os.path.exists(path):
        return None, None, None, [], [], []
    with open(path, encoding="utf-8") as f:
        content = f.read()

    date_match = re.search(r"比較區間：\*\*\s*([\d/]+)\s*→\s*([\d/]+)", content)
    time_match = re.search(r"產生時間：\*\*\s*(.+)", content)
    prev_date = date_match.group(1) if date_match else ""
    today_date = date_match.group(2) if date_match else ""
    gen_time = time_match.group(1).strip() if time_match else ""

    added_rows = []
    added_block = re.search(r"新增股票.*?\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if added_block:
        for m in re.finditer(r"\|\s*(\S+)\s*\|\s*(.+?)\s*\|\s*([\d,]+)\s*\|\s*([\d.]+%)\s*\|", added_block.group(1)):
            added_rows.append({"code": m.group(1), "name": m.group(2).strip(), "shares": m.group(3), "weight": m.group(4)})

    removed_rows = []
    removed_block = re.search(r"刪除股票.*?\n\n(.*?)(?=\n## |\Z)", content, re.DOTALL)
    if removed_block:
        for m in re.finditer(r"\|\s*(\S+)\s*\|\s*(.+?)\s*\|\s*([\d,]+)\s*\|\s*([\d.]+%)\s*\|", removed_block.group(1)):
            removed_rows.append({"code": m.group(1), "name": m.group(2).strip(), "shares": m.group(3), "weight": m.group(4)})

    changed_rows = []
    changed_block = re.search(r"持股異動.*?\n\n(.*?)(?=\Z)", content, re.DOTALL)
    if changed_block:
        for m in re.finditer(
            r"\|\s*(\S+)\s*\|\s*(.+?)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([+\-\d,]+)\s*\|\s*([\d.]+%)\s*\|\s*([\d.]+%)\s*\|\s*([+\-\d.]+%)\s*\|",
            changed_block.group(1)
        ):
            wc_str = m.group(8).replace("%", "").strip()
            try:
                wc = float(wc_str)
            except ValueError:
                wc = 0.0
            changed_rows.append({
                "code": m.group(1),
                "name": m.group(2).strip(),
                "prev_shares": m.group(3),
                "today_shares": m.group(4),
                "shares_diff": m.group(5),
                "prev_weight": m.group(6),
                "today_weight": m.group(7),
                "weight_change": m.group(8),
                "wc_val": wc,
            })

    return prev_date, today_date, gen_time, added_rows, removed_rows, changed_rows


def to_num(s):
    """Parse a possibly-formatted number string to float for data-sort."""
    try:
        return float(s.replace(",", "").replace("%", "").replace("+", ""))
    except (ValueError, AttributeError):
        return 0.0


def build_html(portfolio, prev_date, today_date, gen_time, added_rows, removed_rows, changed_rows):
    date_label = today_date or parse_date_label(datetime.now().strftime("%Y%m%d"))
    total = len(portfolio)

    # Build change lookup by code
    changed_by_code = {r["code"]: r for r in changed_rows}
    # Codes that are newly added
    added_codes = {r["code"] for r in added_rows}

    # Merge portfolio + change data
    merged_rows = ""
    for row in portfolio:
        code = row["code"]
        chg = changed_by_code.get(code)
        w = to_num(row["weight"])
        bar_width = min(int(w * 8), 100)

        # shares diff cell
        if chg:
            sd_raw = to_num(chg["shares_diff"])
            sd_cls = "pos" if sd_raw > 0 else ("neg" if sd_raw < 0 else "zero")
            shares_diff_cell = f'<td class="num {sd_cls}" data-sort="{sd_raw}">{chg["shares_diff"]}</td>'
            prev_w_raw = to_num(chg["prev_weight"])
            prev_weight_cell = f'<td class="num" data-sort="{prev_w_raw}">{chg["prev_weight"]}</td>'
            wc_raw = chg["wc_val"]
            wc_cls = "pos" if wc_raw > 0 else ("neg" if wc_raw < 0 else "zero")
            weight_change_cell = f'<td class="{wc_cls}" data-sort="{wc_raw}">{chg["weight_change"]}</td>'
        elif code in added_codes:
            shares_diff_cell = '<td class="pos badge-new" data-sort="999999">新增</td>'
            prev_weight_cell = '<td data-sort="0">—</td>'
            weight_change_cell = '<td class="pos" data-sort="999999">新增</td>'
        else:
            shares_diff_cell = '<td class="zero" data-sort="0">—</td>'
            prev_weight_cell = f'<td class="num" data-sort="{to_num(row["weight"])}">{row["weight"]}</td>'
            weight_change_cell = '<td class="zero" data-sort="0">0%</td>'

        merged_rows += f"""
        <tr>
          <td class="code" data-sort="{code}">{code}</td>
          <td data-sort="{row['name']}">{row['name']}</td>
          <td class="num" data-sort="{to_num(row['shares'])}">{row['shares']}</td>
          <td class="weight-cell" data-sort="{w}">
            <div class="weight-bar-wrap">
              <div class="weight-bar" style="width:{bar_width}%"></div>
              <span class="weight-label">{row['weight']}</span>
            </div>
          </td>
          {shares_diff_cell}
          {prev_weight_cell}
          {weight_change_cell}
        </tr>"""

    def removed_table(rows):
        if not rows:
            return "<p class='empty'>無刪除股票</p>"
        s = "<table><thead><tr><th>代號</th><th>名稱</th><th>原股數</th><th>原權重</th></tr></thead><tbody>"
        for r in rows:
            s += f"<tr><td class='code'>{r['code']}</td><td>{r['name']}</td><td class='num'>{r['shares']}</td><td class='neg'>{r['weight']}</td></tr>"
        return s + "</tbody></table>"

    return f"""<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>49YTW 持股追蹤</title>
  <style>
    *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; background: #0f1117; color: #e2e8f0; min-height: 100vh; }}
    header {{ background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%); border-bottom: 1px solid #334155; padding: 24px 32px; }}
    header h1 {{ font-size: 1.6rem; font-weight: 700; color: #f8fafc; letter-spacing: -0.02em; }}
    header p {{ color: #94a3b8; font-size: 0.85rem; margin-top: 4px; }}
    .badge {{ display: inline-block; background: #1e40af; color: #93c5fd; font-size: 0.7rem; padding: 2px 8px; border-radius: 999px; margin-left: 10px; vertical-align: middle; }}
    main {{ max-width: 1200px; margin: 0 auto; padding: 28px 20px; }}
    .cards {{ display: flex; gap: 14px; flex-wrap: wrap; margin-bottom: 28px; }}
    .card {{ background: #1e293b; border: 1px solid #334155; border-radius: 10px; padding: 16px 22px; min-width: 140px; flex: 1; }}
    .card .label {{ font-size: 0.72rem; color: #64748b; text-transform: uppercase; letter-spacing: 0.06em; margin-bottom: 6px; }}
    .card .value {{ font-size: 1.8rem; font-weight: 700; color: #f1f5f9; }}
    .card .value.pos {{ color: #4ade80; }}
    .card .value.neg {{ color: #f87171; }}
    .card .value.warn {{ color: #fbbf24; }}
    section {{ background: #1e293b; border: 1px solid #334155; border-radius: 12px; margin-bottom: 24px; overflow: hidden; }}
    section .sec-header {{ padding: 16px 22px; border-bottom: 1px solid #334155; display: flex; align-items: center; gap: 10px; }}
    section .sec-header h2 {{ font-size: 1rem; font-weight: 600; color: #f1f5f9; }}
    section .sec-header .count {{ background: #334155; color: #94a3b8; font-size: 0.72rem; padding: 2px 8px; border-radius: 999px; }}
    .table-wrap {{ overflow-x: auto; }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.85rem; }}
    thead tr {{ background: #0f172a; }}
    th {{ padding: 10px 14px; text-align: left; color: #64748b; font-weight: 500; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; user-select: none; }}
    th.sortable {{ cursor: pointer; }}
    th.sortable:hover {{ color: #94a3b8; }}
    th .sort-icon {{ display: inline-block; margin-left: 4px; opacity: 0.3; font-style: normal; }}
    th.asc .sort-icon {{ opacity: 1; }}
    th.desc .sort-icon {{ opacity: 1; transform: rotate(180deg); display: inline-block; }}
    td {{ padding: 9px 14px; border-top: 1px solid #1e293b; color: #cbd5e1; white-space: nowrap; }}
    tbody tr:hover {{ background: #263148; }}
    .code {{ font-family: monospace; color: #93c5fd; font-size: 0.85rem; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .pos {{ color: #4ade80; font-weight: 600; }}
    .neg {{ color: #f87171; font-weight: 600; }}
    .zero {{ color: #475569; }}
    .badge-new {{ font-size: 0.72rem; background: #14532d; color: #4ade80; border-radius: 4px; padding: 1px 6px; text-align: center; }}
    .weight-cell {{ min-width: 120px; }}
    .weight-bar-wrap {{ display: flex; align-items: center; gap: 8px; }}
    .weight-bar {{ height: 6px; background: linear-gradient(90deg, #3b82f6, #6366f1); border-radius: 3px; min-width: 2px; flex-shrink: 0; }}
    .weight-label {{ color: #93c5fd; font-variant-numeric: tabular-nums; font-size: 0.82rem; }}
    .empty {{ color: #475569; padding: 16px 22px; font-style: italic; font-size: 0.85rem; }}
    footer {{ text-align: center; padding: 24px; color: #475569; font-size: 0.78rem; }}
    @media (max-width: 600px) {{
      .cards {{ gap: 10px; }}
      .card .value {{ font-size: 1.4rem; }}
      th, td {{ padding: 7px 10px; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>49YTW 持股追蹤 <span class="badge">自動更新</span></h1>
    <p>資料日期：{date_label} &nbsp;·&nbsp; 產生時間：{gen_time or datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
  </header>
  <main>
    <div class="cards">
      <div class="card"><div class="label">持股總數</div><div class="value">{total} <span style="font-size:1rem;color:#64748b">檔</span></div></div>
      <div class="card"><div class="label">新增</div><div class="value pos">{len(added_rows)}</div></div>
      <div class="card"><div class="label">刪除</div><div class="value neg">{len(removed_rows)}</div></div>
      <div class="card"><div class="label">異動</div><div class="value warn">{len(changed_rows)}</div></div>
      <div class="card"><div class="label">比較區間</div><div class="value" style="font-size:0.9rem;padding-top:4px">{prev_date}<br>→ {today_date}</div></div>
    </div>

    <section>
      <div class="sec-header">
        <h2>📋 今日持股 &amp; 異動</h2>
        <span class="count">{total} 檔</span>
        <span style="color:#475569;font-size:0.78rem;margin-left:auto">點擊欄位標題排序</span>
      </div>
      <div class="table-wrap">
        <table id="main-table">
          <thead>
            <tr>
              <th class="sortable" data-col="0">代號<i class="sort-icon">▲</i></th>
              <th class="sortable" data-col="1">名稱<i class="sort-icon">▲</i></th>
              <th class="sortable num" data-col="2">今日股數<i class="sort-icon">▲</i></th>
              <th class="sortable" data-col="3" data-default-desc="true">持股權重<i class="sort-icon">▲</i></th>
              <th class="sortable num" data-col="4">股數變化<i class="sort-icon">▲</i></th>
              <th class="sortable num" data-col="5">前日權重<i class="sort-icon">▲</i></th>
              <th class="sortable" data-col="6">權重變化<i class="sort-icon">▲</i></th>
            </tr>
          </thead>
          <tbody>{merged_rows}</tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="sec-header"><h2>🔴 刪除股票</h2><span class="count">{len(removed_rows)} 檔</span></div>
      <div class="table-wrap">{removed_table(removed_rows)}</div>
    </section>
  </main>
  <footer>資料來源：49YTW 基金 &nbsp;·&nbsp; 每個交易日自動更新</footer>

  <script>
    (function () {{
      const table = document.getElementById('main-table');
      const tbody = table.querySelector('tbody');
      let sortCol = 3, sortAsc = false; // 預設：持股權重 降冪

      function getVal(row, col) {{
        const cell = row.cells[col];
        const v = cell.getAttribute('data-sort');
        if (v !== null) return isNaN(+v) ? v : +v;
        return cell.textContent.trim();
      }}

      function sortTable(col, asc) {{
        const rows = Array.from(tbody.rows);
        rows.sort((a, b) => {{
          const va = getVal(a, col), vb = getVal(b, col);
          if (typeof va === 'number' && typeof vb === 'number') return asc ? va - vb : vb - va;
          return asc ? String(va).localeCompare(String(vb), 'zh-Hant') : String(vb).localeCompare(String(va), 'zh-Hant');
        }});
        rows.forEach(r => tbody.appendChild(r));
      }}

      function updateHeaders(activeCol, asc) {{
        table.querySelectorAll('th.sortable').forEach((th, i) => {{
          th.classList.remove('asc', 'desc');
          if (i === activeCol) th.classList.add(asc ? 'asc' : 'desc');
        }});
      }}

      table.querySelectorAll('th.sortable').forEach((th, i) => {{
        th.addEventListener('click', () => {{
          if (sortCol === i) {{
            sortAsc = !sortAsc;
          }} else {{
            sortCol = i;
            sortAsc = th.dataset.defaultDesc !== 'true';
          }}
          sortTable(sortCol, sortAsc);
          updateHeaders(sortCol, sortAsc);
        }});
      }});

      // Apply initial sort (持股權重 降冪)
      sortTable(sortCol, sortAsc);
      updateHeaders(sortCol, sortAsc);
    }})();
  </script>
</body>
</html>"""


def main():
    files = find_sorted_files()
    if not files:
        print("找不到持股 CSV，跳過。")
        return
    portfolio = load_csv(files[0])
    prev_date, today_date, gen_time, added, removed, changed = load_latest_diff_md()
    html = build_html(portfolio, prev_date, today_date, gen_time, added, removed, changed)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已產生 {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
