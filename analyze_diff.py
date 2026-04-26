#!/usr/bin/env python3
import csv, os, glob
from datetime import datetime

DATA_DIR = "data"
REPORT_DIR = "reports"

def load_csv(filepath):
    result = {}
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = row["股票代號"].strip()
            shares = int(row["股數"].replace(",", "").strip())
            weight = float(row["持股權重"].replace("%", "").strip())
            result[code] = {"名稱": row["股票名稱"].strip(), "股數": shares, "權重": weight}
    return result

def find_sorted_files():
    files = glob.glob(os.path.join(DATA_DIR, "49YTW_portfolio_????????.csv"))
    files.sort(reverse=True)
    return files

def parse_date(filepath):
    base = os.path.basename(filepath)
    return base.replace("49YTW_portfolio_", "").replace(".csv", "")

def compare(today_data, prev_data):
    all_codes = set(today_data) | set(prev_data)
    added, removed, changed = [], [], []
    for code in sorted(all_codes):
        t = today_data.get(code)
        p = prev_data.get(code)
        if t and not p:
            added.append((code, t["名稱"], t["股數"], t["權重"]))
        elif p and not t:
            removed.append((code, p["名稱"], p["股數"], p["權重"]))
        else:
            shares_diff = t["股數"] - p["股數"]
            weight_diff = round(t["權重"] - p["權重"], 2)
            if shares_diff != 0 or weight_diff != 0.0:
                changed.append({"代號": code, "名稱": t["名稱"], "今日股數": t["股數"], "前日股數": p["股數"], "股數變化": shares_diff, "今日權重": t["權重"], "前日權重": p["權重"], "權重變化": weight_diff})
    changed.sort(key=lambda x: abs(x["權重變化"]), reverse=True)
    return added, removed, changed

def sign(n):
    return f"+{n}" if n > 0 else str(n)

def fmt(n):
    return f"{n:,}"

def generate_report(today_data, prev_data, today_date, prev_date, added, removed, changed):
    tf = f"{today_date[:4]}/{today_date[4:6]}/{today_date[6:]}"
    pf = f"{prev_date[:4]}/{prev_date[4:6]}/{prev_date[6:]}"
    lines = [f"# 49YTW 持股變化報告", "", f"**比較區間：** {pf} → {tf}", f"**產生時間：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", ""]
    lines += ["## 摘要", "", "| 項目 | 數量 |", "|------|------|", f"| 今日持股總數 | {len(today_data)} 檔 |", f"| 前日持股總數 | {len(prev_data)} 檔 |", f"| 新增股票 | {len(added)} 檔 |", f"| 刪除股票 | {len(removed)} 檔 |", f"| 權重/股數異動 | {len(changed)} 檔 |", ""]
    lines += [f"## 🟢 新增股票（{len(added)} 檔）", ""]
    if added:
        lines += ["| 股票代號 | 股票名稱 | 股數 | 持股權重 |", "|----------|----------|------|----------|"]
        for code, name, shares, weight in added:
            lines.append(f"| {code} | {name} | {fmt(shares)} | {weight}% |")
    else:
        lines.append("_無新增股票_")
    lines += ["", f"## 🔴 刪除股票（{len(removed)} 檔）", ""]
    if removed:
        lines += ["| 股票代號 | 股票名稱 | 原股數 | 原持股權重 |", "|----------|----------|--------|------------|"]
        for code, name, shares, weight in removed:
            lines.append(f"| {code} | {name} | {fmt(shares)} | {weight}% |")
    else:
        lines.append("_無刪除股票_")
    lines += ["", f"## 🔄 持股異動（{len(changed)} 檔，依權重變化排序）", ""]
    if changed:
        lines += ["| 股票代號 | 股票名稱 | 前日股數 | 今日股數 | 股數變化 | 前日權重 | 今日權重 | 權重變化 |", "|----------|----------|----------|----------|----------|----------|----------|----------|"]
        for r in changed:
            lines.append(f"| {r['代號']} | {r['名稱']} | {fmt(r['前日股數'])} | {fmt(r['今日股數'])} | {sign(r['股數變化'])} | {r['前日權重']}% | {r['今日權重']}% | {sign(r['權重變化'])}% |")
    else:
        lines.append("_持股無異動_")
    return "\n".join(lines)

def main():
    files = find_sorted_files()
    if len(files) < 2:
        print("資料不足（需要至少兩天的 CSV），跳過分析。")
        return
    today_file, prev_file = files[0], files[1]
    today_date, prev_date = parse_date(today_file), parse_date(prev_file)
    print(f"比較：{prev_date} vs {today_date}")
    today_data, prev_data = load_csv(today_file), load_csv(prev_file)
    added, removed, changed = compare(today_data, prev_data)
    report = generate_report(today_data, prev_data, today_date, prev_date, added, removed, changed)
    os.makedirs(REPORT_DIR, exist_ok=True)
    report_path = os.path.join(REPORT_DIR, f"diff_{prev_date}_to_{today_date}.md")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report)
    with open(os.path.join(REPORT_DIR, "latest_diff.md"), "w", encoding="utf-8") as f:
        f.write(report)
    print(f"報告已儲存：{report_path}")
    print(f"新增：{len(added)} 檔　刪除：{len(removed)} 檔　異動：{len(changed)} 檔")

if __name__ == "__main__":
    main()
