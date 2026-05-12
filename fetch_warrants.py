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
    "標的證券/指數",
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

WARRANT_CODE_KEYS = ("權證代號", "warrantCode", "WarrantCode")


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
    wcode = ""
    for k in WARRANT_CODE_KEYS:
        wcode = (record.get(k) or "").strip()
        if wcode:
            break
    if len(wcode) >= 2 and wcode[0] == "0":
        c = wcode[1].upper()
        if c.isalpha():
            return "put"
        if c.isdigit():
            return "call"
    return ""


def _extract_list(payload):
    """把回應正規化成 records list。處理直接 list 或 dict 包裝兩種格式。"""
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        # TWSE rwd 風格：{"fields":[...], "data":[[...]]}
        fields = payload.get("fields") or payload.get("Fields")
        data = payload.get("data") or payload.get("Data")
        if fields and isinstance(data, list) and data and isinstance(data[0], list):
            return [dict(zip(fields, row)) for row in data]
        if isinstance(data, list):
            return data
    return []


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
                    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
                    "Referer": "https://openapi.twse.com.tw/",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                status = resp.status
                body = resp.read().decode("utf-8", errors="replace")
                print(f"[debug] {url} → HTTP {status}, {len(body)} bytes")

            try:
                payload = json.loads(body)
            except json.JSONDecodeError as e:
                last_err = f"JSON 解析失敗：{e}；前 200 字：{body[:200]!r}"
                print(f"嘗試失敗 {url}: {last_err}")
                continue

            rows = _extract_list(payload)
            if not rows:
                last_err = (
                    f"回應非預期格式或為空（type={type(payload).__name__}）；"
                    f"前 200 字：{body[:200]!r}"
                )
                print(f"嘗試失敗 {url}: {last_err}")
                continue

            wmap: dict = {}
            for w in rows:
                if not isinstance(w, dict):
                    continue
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
                print(f"成功（{url}）解析 {len(rows)} 筆，覆蓋 {len(wmap)} 檔標的")
                return wmap

            last_err = (
                f"已取得 {len(rows)} 筆紀錄但無法萃取標的代號；"
                f"首筆 keys={list(rows[0].keys()) if isinstance(rows[0], dict) else '非 dict'}"
            )
            print(f"嘗試失敗 {url}: {last_err}")

        except Exception as e:
            last_err = f"{type(e).__name__}: {e}"
            print(f"嘗試失敗 {url}: {last_err}")
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
