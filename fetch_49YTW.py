#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import csv
import os
from datetime import datetime

URL = "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=49YTW"
OUTPUT_DIR = "data"

def fetch_portfolio():
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"}
    print(f"[{datetime.now()}] 正在抓取 49YTW 基金投資組合...")
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    asset_div = soup.find(id="asset")
    if not asset_div:
        raise ValueError("找不到 #asset 區塊")
    target_table = None
    for table in asset_div.find_all("table"):
        headers_row = table.find("tr")
        if headers_row:
            ths = [th.get_text(strip=True) for th in headers_row.find_all("th")]
            if "股票代號" in ths and "持股權重" in ths:
                target_table = table
                break
    if not target_table:
        raise ValueError("找不到股票持股 table")
    rows = []
    for tr in target_table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all(["th", "td"])]
        if len(cells) == 4 and cells[0] not in ("股票", "股票代號"):
            rows.append(cells)
    print(f"  → 共找到 {len(rows)} 檔股票")
    return rows

def save_csv(rows):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    filename = os.path.join(OUTPUT_DIR, f"49YTW_portfolio_{today}.csv")
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["股票代號", "股票名稱", "股數", "持股權重"])
        writer.writerows(rows)
    print(f"  → 已儲存：{filename}")
    return filename

def update_latest(rows):
    filename = os.path.join(OUTPUT_DIR, "49YTW_portfolio_latest.csv")
    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["股票代號", "股票名稱", "股數", "持股權重"])
        writer.writerows(rows)
    print(f"  → 已更新最新版：{filename}")

if __name__ == "__main__":
    rows = fetch_portfolio()
    save_csv(rows)
    update_latest(rows)
    print("完成！")
