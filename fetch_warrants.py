#!/usr/bin/env python3
"""
台灣證交所 認購售權證清單 自動抓取腳本
每個交易日由 GitHub Actions 執行，將結果存為 data/warrants_YYYYMMDD.json
格式：{"標的證券代號": {"call": N, "put": N}, ...}
"""

import json
import os
import urllib.request
import urllib.error
from datetime import datetime

DATA_DIR = "data"

# TWSE OpenAPI：上市權證基本資料彙總表（每日更新）
# 過往的 BWIBBU_d 是個股本益比/殖利率/股價淨值比，並非權證；
# 過往的 opendata.twse.com.tw 域名不存在（正確是 openapi）。
CANDIDATE_URLS = [
    "https://openapi.twse.com.tw/v1/opendata/t187ap37_L",
]

UNDERLYING_KEYS = (
    "標的代號",
    "標的證券代號",
    "underlyingCode",
    "UnderlyingCode",
)

CALLPUT_KEYS = (
    "認購或認售",
    "認購售型態",
    "callPut",
    "CallPut",
)


def _classify(record: dict) -> str:
    """回傳 'call' / 'put' / ''（無法判別）。"""
    for k in CALLPUT_KEYS:
        v = (record.get(k) or "").strip()
        if not v:
            continue
        if "購" in v or v.lower() in ("c", "call"):
            return "call"
        if "售" in v or v.lower() in ("p", "put"):
            return "put"
    # 後備：以權證代號第二字元推斷（TWSE 慣例：英文字母多為認售）
    wcode = (record.get("權證代號") or record.get("warrantCode") or "").strip()
    if len(wcode) >= 2 and wcode[0] == "0":
        c = wcode[1].upper()
        if c.isalpha():
            return "put"
        if c.isdigit():
            return "call"
    return ""


def fetch_warrants() -> dict:
    last_err = None
    for url in CANDIDATE_URLS:
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/124.0 Safari/537.36"
                    ),
                    "Accept": "application/json,*/*",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                rows = json.loads(resp.read().decode("utf-8"))

            if not isinstance(rows, list) or not rows:
                continue

            wmap: dict = {}
            for w in rows:
                code = ""
                for k in UNDERLYING_KEYS:
                    code = (w.get(k) or "").strip()
                    if code:
                        break
                if not code:
                    continue
                bucket = wmap.setdefault(code, {"call": 0, "put": 0})
                t = _classify(w)
                if t:
                    bucket[t] += 1

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
