#!/usr/bin/env python3
"""
台灣證交所 認購售權證清單 自動抓取腳本
每個交易日由 GitHub Actions 執行，將結果存為 data/warrants_YYYYMMDD.json
格式：{"股票代號": {"call": N, "put": N}, ...}
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime

DATA_DIR = "data"
TWSE_URL = "https://opendata.twse.com.tw/v1/derivatives/BWIBBU_d"


def fetch_warrants() -> dict:
    req = urllib.request.Request(TWSE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        rows = json.loads(resp.read().decode("utf-8"))

    wmap = {}
    for w in rows:
        code = (w.get("標的證券代號") or w.get("underlyingCode") or "").strip()
        if not code:
            continue
        if code not in wmap:
            wmap[code] = {"call": 0, "put": 0}
        t = (w.get("認購或認售") or w.get("callPut") or "").strip()
        if t == "認購":
            wmap[code]["call"] += 1
        elif t == "認售":
            wmap[code]["put"] += 1
    return wmap


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    outpath = os.path.join(DATA_DIR, f"warrants_{today}.json")

    try:
        wmap = fetch_warrants()
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(wmap, f, ensure_ascii=False, separators=(",", ":"))
        print(f"已儲存 {outpath}（{len(wmap)} 檔標的有權證）")
    except urllib.error.URLError as e:
        print(f"網路錯誤，權證資料抓取失敗：{e}")
        raise
    except Exception as e:
        print(f"權證資料抓取失敗：{e}")
        raise


if __name__ == "__main__":
    main()
