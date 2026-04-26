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
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,900")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    return driver


def fetch_portfolio():
    print(f"[{datetime.now()}] 正在抓取 49YTW 基金投資組合...")
    driver = get_driver()
    try:
        driver.get(URL)

        # 等待頁面 #asset 區塊出現（最多 20 秒）
        wait = WebDriverWait(driver, 20)
        wait.until(EC.presence_of_element_located((By.ID, "asset")))

        # debug: 印出 #asset 裡的 table 數量和 th 內容
        asset_el = driver.find_element(By.ID, "asset")
        tables = asset_el.find_elements(By.TAG_NAME, "table")
        print(f"  → #asset 裡找到 {len(tables)} 個 table")
        for i, t in enumerate(tables):
            ths = [th.text.strip() for th in t.find_elements(By.TAG_NAME, "th")]
            print(f"    table[{i}] ths: {ths}")

        # 優先用 JavaScript 直接從 DOM 抓取（最可靠）
        result = driver.execute_script("""
            const tables = document.querySelectorAll('#asset table');
            const rows = [];
            tables.forEach(table => {
                const allThs = Array.from(table.querySelectorAll('th'))
                    .map(th => th.textContent.trim());
                if (allThs.includes('股票代號') && allThs.includes('持股權重')) {
                    table.querySelectorAll('tr').forEach(tr => {
                        const cells = Array.from(tr.querySelectorAll('td'))
                            .map(td => td.textContent.trim());
                        if (cells.length === 4 && cells[0]) rows.push(cells);
                    });
                }
            });
            return rows;
        """)

        if result:
            print(f"  → JavaScript 找到 {len(result)} 檔股票")
            return result

        raise ValueError("找不到股票持股資料，網站可能封鎖了 headless 瀏覽器")

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
