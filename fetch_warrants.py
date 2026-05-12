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

# 依序嘗試，第一個成功即停止
CANDIDATE_URLS = [
    "https://www.twse.com.tw/rwd/zh/call-warrant/BWIBBU_d?response=json",
    "https://www.twse.com.tw/exchangeReport/BWIBBU_d?response=json&date={date}",
    "https://opendata.twse.com.tw/v1/exchange/BWIBBU_d",
    "https://opendata.twse.com.tw/v1/derivatives/BWIBBU_d",
]


def _parse_rows(data: object) -> list:
    """將不同格式的 TWSE 回應統一轉為 [{field: value}] 列表。"""
    if isinstance(data, list):
        return data  # opendata 格式：直接是物件陣列
    if isinstance(data, dict):
        stat = data.get("stat", "")
        if stat not in ("OK", "ok", ""):
            raise ValueError(f"API 回傳 stat={stat!r}")
        fields = data.get("fields") or data.get("Fields") or []
        rows   = data.get("data")   or data.get("Data")   or []
        if fields and rows:
            return [dict(zip(fields, row)) for row in rows]
    return []


def fetch_warrants() -> dict:
    today = datetime.now().strftime("%Y%m%d")
    last_err = None

    for url_tpl in CANDIDATE_URLS:
        url = url_tpl.format(date=today)
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Mozilla/5.0 (compatible; ETF-tracker/1.0)"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                raw = json.loads(resp.read().decode("utf-8"))

            rows = _parse_rows(raw)
            if not rows:
                continue  # 空回應，試下一個 URL

            wmap: dict = {}
            for w in rows:
                code = (
                    w.get("標的證券代號") or w.get("underlyingCode") or ""
                ).strip()
                if not code:
                    continue
                if code not in wmap:
                    wmap[code] = {"call": 0, "put": 0}
                t = (w.get("認購或認售") or w.get("callPut") or "").strip()
                if t == "認購":
                    wmap[code]["call"] += 1
                elif t == "認售":
                    wmap[code]["put"] += 1

            if wmap:
                print(f"成功（{url}）")
                return wmap

        except Exception as e:
            print(f"嘗試失敗 {url}: {e}")
            last_err = e
            continue

    raise RuntimeError(f"所有 URL 均失敗，最後錯誤：{last_err}")


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    today = datetime.now().strftime("%Y%m%d")
    outpath = os.path.join(DATA_DIR, f"warrants_{today}.json")

    try:
        wmap = fetch_warrants()
        with open(outpath, "w", encoding="utf-8") as f:
            json.dump(wmap, f, ensure_ascii=False, separators=(",", ":"))
        print(f"已儲存 {outpath}（{len(wmap)} 檔標的有權證）")
    except Exception as e:
        print(f"⚠ 權證資料抓取失敗（跳過，不影響主流程）：{e}")


if __name__ == "__main__":
    main()
