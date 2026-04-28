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
        return None, None, None, None, None, None
    with open(path, encoding="utf-8") as f:
        content = f.read()

    date_match = re.search(r"比較區間：\*\*\s*([\d/]+)\s*→\s*([\d/]+)", content)
    time_match = re.search(r"產生時間：\*\*\s*(.+)", content)
    prev_date = date_match.group(1) if date_match else ""
    today_date = date_match.group(2) if date_match else ""
    gen_time = time_match.group(1).strip() if time_match else ""

    counts = re.findall(r"\|\s*(.+?)\s*\|\s*(\d+)\s*檔\s*\|", content)
    summary = {k.strip(): v for k, v in counts}

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
            weight_change = m.group(8).replace("%", "").strip()
            try:
                wc = float(weight_change)
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


def weight_class(w_str):
    try:
        w = float(w_str.replace("%", "").replace("+", "").replace("-", ""))
        sign = -1 if w_str.startswith("-") else 1
        w = w * sign
    except ValueError:
        return ""
    if w > 0:
        return "pos"
    elif w < 0:
        return "neg"
    return ""


def build_html(portfolio, prev_date, today_date, gen_time, added_rows, removed_rows, changed_rows):
    date_label = today_date or (parse_date_label(datetime.now().strftime("%Y%m%d")))
    total = len(portfolio)

    portfolio_rows = ""
    for i, row in enumerate(portfolio):
        try:
            w = float(row["weight"].replace("%", ""))
        except ValueError:
            w = 0.0
        bar_width = min(int(w * 8), 100)
        portfolio_rows += f"""
        <tr>
          <td class="code">{row['code']}</td>
          <td>{row['name']}</td>
          <td class="num">{row['shares']}</td>
          <td class="weight-cell">
            <div class="weight-bar-wrap">
              <div class="weight-bar" style="width:{bar_width}%"></div>
              <span class="weight-label">{row['weight']}</span>
            </div>
          </td>
        </tr>"""

    def added_table(rows):
        if not rows:
            return "<p class='empty'>無新增股票</p>"
        s = "<table><thead><tr><th>代號</th><th>名稱</th><th>股數</th><th>權重</th></tr></thead><tbody>"
        for r in rows:
            s += f"<tr><td class='code'>{r['code']}</td><td>{r['name']}</td><td class='num'>{r['shares']}</td><td class='pos'>{r['weight']}</td></tr>"
        return s + "</tbody></table>"

    def removed_table(rows):
        if not rows:
            return "<p class='empty'>無刪除股票</p>"
        s = "<table><thead><tr><th>代號</th><th>名稱</th><th>原股數</th><th>原權重</th></tr></thead><tbody>"
        for r in rows:
            s += f"<tr><td class='code'>{r['code']}</td><td>{r['name']}</td><td class='num'>{r['shares']}</td><td class='neg'>{r['weight']}</td></tr>"
        return s + "</tbody></table>"

    def changed_table(rows):
        if not rows:
            return "<p class='empty'>持股無異動</p>"
        s = "<table><thead><tr><th>代號</th><th>名稱</th><th>前日股數</th><th>今日股數</th><th>股數變化</th><th>前日權重</th><th>今日權重</th><th>權重變化</th></tr></thead><tbody>"
        for r in rows:
            wc = weight_class(r['weight_change'])
            sd_class = "pos" if "+" in r["shares_diff"] else ("neg" if r["shares_diff"].startswith("-") else "")
            s += (
                f"<tr><td class='code'>{r['code']}</td><td>{r['name']}</td>"
                f"<td class='num'>{r['prev_shares']}</td><td class='num'>{r['today_shares']}</td>"
                f"<td class='num {sd_class}'>{r['shares_diff']}</td>"
                f"<td>{r['prev_weight']}</td><td>{r['today_weight']}</td>"
                f"<td class='{wc}'>{r['weight_change']}</td></tr>"
            )
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
    main {{ max-width: 1100px; margin: 0 auto; padding: 28px 20px; }}
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
    th {{ padding: 10px 14px; text-align: left; color: #64748b; font-weight: 500; font-size: 0.75rem; text-transform: uppercase; letter-spacing: 0.05em; white-space: nowrap; }}
    td {{ padding: 9px 14px; border-top: 1px solid #1e293b; color: #cbd5e1; white-space: nowrap; }}
    tbody tr:hover {{ background: #263148; }}
    .code {{ font-family: monospace; color: #93c5fd; font-size: 0.85rem; }}
    .num {{ text-align: right; font-variant-numeric: tabular-nums; }}
    .pos {{ color: #4ade80; font-weight: 600; }}
    .neg {{ color: #f87171; font-weight: 600; }}
    .weight-cell {{ min-width: 130px; }}
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
      <div class="sec-header"><h2>📋 今日持股</h2><span class="count">{total} 檔</span></div>
      <div class="table-wrap">
        <table>
          <thead><tr><th>代號</th><th>名稱</th><th>股數</th><th>持股權重</th></tr></thead>
          <tbody>{portfolio_rows}</tbody>
        </table>
      </div>
    </section>

    <section>
      <div class="sec-header"><h2>🟢 新增股票</h2><span class="count">{len(added_rows)} 檔</span></div>
      <div class="table-wrap">{added_table(added_rows)}</div>
    </section>

    <section>
      <div class="sec-header"><h2>🔴 刪除股票</h2><span class="count">{len(removed_rows)} 檔</span></div>
      <div class="table-wrap">{removed_table(removed_rows)}</div>
    </section>

    <section>
      <div class="sec-header"><h2>🔄 持股異動</h2><span class="count">{len(changed_rows)} 檔</span></div>
      <div class="table-wrap">{changed_table(changed_rows)}</div>
    </section>
  </main>
  <footer>資料來源：49YTW 基金 &nbsp;·&nbsp; 每個交易日自動更新</footer>
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
