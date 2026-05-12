#!/usr/bin/env python3
"""
比對最近兩天的權證 JSON，產出每檔標的 call/put 檔數變化報告。
輸出：
  - reports/warrant_diff_{prev}_to_{today}.md
  - reports/latest_warrant_diff.md
"""
import csv
import glob
import json
import os
from datetime import datetime

DATA_DIR = "data"
REPORT_DIR = "reports"


def find_sorted_warrant_files():
    files = glob.glob(os.path.join(DATA_DIR, "warrants_????????.json"))
    files.sort(reverse=True)
    return files


def parse_date(filepath):
    return os.path.basename(filepath).replace("warrants_", "").replace(".json", "")


def load_warrants(filepath):
    with open(filepath, encoding="utf-8") as f:
        return json.load(f)


def load_name_map():
    """從最新持股 CSV 取得 代號→名稱 對應，方便報告顯示名稱。"""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "49YTW_portfolio_????????.csv")))
    if not files:
        return {}
    mapping = {}
    with open(files[-1], encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row.get("股票代號") or "").strip()
            name = (row.get("股票名稱") or "").strip()
            if code:
                mapping[code] = name
    return mapping


def compare(today, prev):
    all_codes = set(today) | set(prev)
    added, removed, changed = [], [], []
    for code in sorted(all_codes):
        t = today.get(code) or {"call": 0, "put": 0}
        p = prev.get(code) or {"call": 0, "put": 0}
        t_total = t["call"] + t["put"]
        p_total = p["call"] + p["put"]
        if p_total == 0 and t_total > 0:
            added.append((code, t["call"], t["put"]))
        elif t_total == 0 and p_total > 0:
            removed.append((code, p["call"], p["put"]))
        elif t["call"] != p["call"] or t["put"] != p["put"]:
            changed.append({
                "代號": code,
                "今日認購": t["call"], "前日認購": p["call"], "認購變化": t["call"] - p["call"],
                "今日認售": t["put"],  "前日認售": p["put"],  "認售變化": t["put"]  - p["put"],
            })
    changed.sort(key=lambda x: abs(x["認購變化"]) + abs(x["認售變化"]), reverse=True)
    return added, removed, changed


def sign(n):
    return f"+{n}" if n > 0 else str(n)


def fmt_date(d):
    return f"{d[:4]}/{d[4:6]}/{d[6:]}"


def generate_report(today_date, prev_date, today_data, prev_data, names, added, removed, changed):
    lines = [
        "# 49YTW 權證檔數變化報告",
        "",
        f"**比較區間：** {fmt_date(prev_date)} → {fmt_date(today_date)}",
        f"**產生時間：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 摘要",
        "",
        "| 項目 | 數量 |",
        "|------|------|",
        f"| 今日有權證標的 | {len(today_data)} 檔 |",
        f"| 前日有權證標的 | {len(prev_data)} 檔 |",
        f"| 新增有權證標的 | {len(added)} 檔 |",
        f"| 失去全部權證標的 | {len(removed)} 檔 |",
        f"| 認購/認售檔數異動 | {len(changed)} 檔 |",
        "",
        f"## 🟢 新增有權證標的（{len(added)} 檔）",
        "",
    ]
    if added:
        lines += [
            "| 股票代號 | 股票名稱 | 認購 | 認售 |",
            "|----------|----------|------|------|",
        ]
        for code, c, p in added:
            lines.append(f"| {code} | {names.get(code, '')} | {c} | {p} |")
    else:
        lines.append("_無_")
    lines += ["", f"## 🔴 失去全部權證標的（{len(removed)} 檔）", ""]
    if removed:
        lines += [
            "| 股票代號 | 股票名稱 | 原認購 | 原認售 |",
            "|----------|----------|--------|--------|",
        ]
        for code, c, p in removed:
            lines.append(f"| {code} | {names.get(code, '')} | {c} | {p} |")
    else:
        lines.append("_無_")
    lines += ["", f"## 🔄 認購/認售檔數異動（{len(changed)} 檔，依變化幅度排序）", ""]
    if changed:
        lines += [
            "| 股票代號 | 股票名稱 | 前日認購 | 今日認購 | 認購變化 | 前日認售 | 今日認售 | 認售變化 |",
            "|----------|----------|----------|----------|----------|----------|----------|----------|",
        ]
        for r in changed:
            lines.append(
                f"| {r['代號']} | {names.get(r['代號'], '')} | "
                f"{r['前日認購']} | {r['今日認購']} | {sign(r['認購變化'])} | "
                f"{r['前日認售']} | {r['今日認售']} | {sign(r['認售變化'])} |"
            )
    else:
        lines.append("_無異動_")
    return "\n".join(lines) + "\n"


def main():
    files = find_sorted_warrant_files()
    if len(files) < 2:
        print("權證資料不足（需要至少兩天），跳過分析。")
        return
    today_file, prev_file = files[0], files[1]
    today_date, prev_date = parse_date(today_file), parse_date(prev_file)
    print(f"比較：{prev_date} vs {today_date}")
    today_data = load_warrants(today_file)
    prev_data = load_warrants(prev_file)
    names = load_name_map()
    added, removed, changed = compare(today_data, prev_data)
    report = generate_report(today_date, prev_date, today_data, prev_data, names, added, removed, changed)

    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"warrant_diff_{prev_date}_to_{today_date}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(REPORT_DIR, "latest_warrant_diff.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(f"報告已儲存：{report_path}")
    print(f"新增：{len(added)} 檔　失去：{len(removed)} 檔　異動：{len(changed)} 檔")


if __name__ == "__main__":
    main()
