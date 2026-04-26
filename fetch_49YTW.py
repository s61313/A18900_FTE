#!/usr/bin/env python3
"""
49YTW 基金投資組合 自動抓取腳本
使用 Selenium + headless Chrome 處理 JavaScript 動態渲染
由 GitHub Actions 每個工作日自動執行
"""

import csv
import os
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

URL = "https://www.ezmoney.com.tw/ETF/Fund/Info?fundCode=49YTW"
OUTPUT_DIR = "data"


def get_driver():
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,800")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    return webdriver.Chrome(options=options)


def fetch_portfolio():
    print(f"[{datetime.now()}] 正在抓取 49YTW 基金投資組合...")
    driver = get_driver()
    try:
        driver.get(URL)

        # 等待 #asset 區塊裡的 table 出現（最多等 15 秒）
        wait = WebDriverWait(driver, 15)
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#asset table")))

        # 找含有「股票代號」th 的 table
        # 注意：table 有兩層 header，第一行是「股票」大標，第二行才是欄位名稱
        # 需要找所有 th（包含所有 row）才能匹配到「股票代號」
        tables = driver.find_elements(By.CSS_SELECTOR, "#asset table")
        target_table = None
        for table in tables:
            all_ths = [th.text.strip() for th in table.find_elements(By.TAG_NAME, "th")]
            if "股票代號" in all_ths and "持股權重" in all_ths:
                target_table = table
                break

        if not target_table:
            raise ValueError("找不到股票持股 table，網站結構可能已變更")

        # 解析資料（只取有 4 個 td 的資料列）
        rows = []
        for tr in target_table.find_elements(By.TAG_NAME, "tr"):
            cells = [td.text.strip() for td in tr.find_elements(By.TAG_NAME, "td")]
            if len(cells) == 4 and cells[0]:
                rows.append(cells)

        print(f"  → 共找到 {len(rows)} 檔股票")
        return rows

    finally:
        driver.quit()


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
