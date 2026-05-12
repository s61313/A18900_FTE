#!/usr/bin/env python3
"""
台灣證交所 認購售權證清單 自動抓取腳本
每個交易日由 GitHub Actions 執行，將結果存為 data/warrants_YYYYMMDD.json
格式：{"股票代號": {"call": N, "put": N}, ...}

注意：TWSE OpenAPI t187ap37_L 只提供標的「名稱」（欄位 `標的證券/指數`），
沒有獨立的標的代號欄位。前端比對是用股票代號，所以必須用 49YTW 持股 CSV
（股票代號 ↔ 股票名稱）做名稱→代號對應；找不到代號的標的（如指數）會被略過。
"""

import csv
import glob
import json
import os
import urllib.request
import urllib.error
from datetime import datetime

DATA_DIR = "data"
WARRANT_URL = "https://openapi.twse.com.tw/v1/opendata/t187ap37_L"


def load_name_to_code() -> dict:
    """從最新的 49YTW 持股 CSV 建立 名稱→代號 對應表。"""
    files = sorted(glob.glob(os.path.join(DATA_DIR, "49YTW_portfolio_????????.csv")))
    if not files:
        return {}
    mapping: dict = {}
    with open(files[-1], encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = (row.get("股票代號") or "").strip()
            name = (row.get("股票名稱") or "").strip()
            if code and name:
                mapping[name] = code
    return mapping


def _classify(record: dict) -> str:
    """回傳 'call' / 'put' / ''（無法判別）。"""
    t = (record.get("權證類型") or "").strip()
    if "購" in t:
        return "call"
    if "售" in t:
        return "put"
    return ""


def fetch_warrants(name_to_code: dict) -> dict:
    req = urllib.request.Request(
        WARRANT_URL,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0 Safari/537.36"
            ),
            "Accept": "application/json,*/*",
            "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
            "Referer": "https://openapi.twse.com.tw/",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        print(f"[debug] {WARRANT_URL} → HTTP {resp.status}, {len(body)} bytes")

    rows = json.loads(body)
    if not isinstance(rows, list) or not rows:
        raise RuntimeError(f"回應非預期格式或為空（type={type(rows).__name__}）")

    wmap: dict = {}
    matched = 0
    for w in rows:
        if not isinstance(w, dict):
            continue
        name = (w.get("標的證券/指數") or "").strip()
        if not name:
            continue
        code = name_to_code.get(name)
        if not code:
            continue  # 不在持股名單，前端用不到
        t = _classify(w)
        if not t:
            continue
        bucket = wmap.setdefault(code, {"call": 0, "put": 0})
        bucket[t] += 1
        matched += 1

    print(f"解析 {len(rows)} 筆權證，{matched} 筆對到持股，覆蓋 {len(wmap)} 檔標的")
    return wmap


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    outpath = os.path.join(DATA_DIR, f"warrants_{today}.json")

    try:
        name_to_code = load_name_to_code()
        if not name_to_code:
            print("⚠ 找不到持股 CSV，名稱→代號對應表為空")
        wmap = fetch_warrants(name_to_code)
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(wmap, f, ensure_ascii=False, separators=(",", ":"))
        print(f"已儲存 {outpath}（{len(wmap)} 檔標的有權證）")
    except Exception as e:
        print(f"⚠ 權證資料抓取失敗（跳過，不影響主流程）：{e}")


if __name__ == "__main__":
    main()
