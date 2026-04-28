#!/usr/bin/env python3
"""
從歷史 CSV 產生持股趨勢圖表，儲存至 reports/
  - top10_trend.png  : Top 10 持股權重折線趨勢圖
  - latest_bar.png   : 當日持股分佈長條圖（Top 20）
"""

import csv
import glob
import os
from datetime import datetime

import matplotlib
matplotlib.use("Agg")
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

DATA_DIR = "data"
REPORT_DIR = "reports"


def _setup_cjk_font():
    for path in fm.findSystemFonts():
        lower = path.lower()
        if ("noto" in lower and "cjk" in lower) or "wqy" in lower:
            try:
                name = fm.FontProperties(fname=path).get_name()
                plt.rcParams["font.family"] = name
                return
            except Exception:
                continue

_setup_cjk_font()
plt.rcParams["axes.unicode_minus"] = False


def load_csv(filepath):
    result = {}
    with open(filepath, newline="", encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            code = row["股票代號"].strip()
            name = row["股票名稱"].strip()
            weight = float(row["持股權重"].replace("%", "").strip())
            result[code] = {"name": name, "weight": weight}
    return result


def parse_date(filepath):
    base = os.path.basename(filepath)
    raw = base.replace("49YTW_portfolio_", "").replace(".csv", "")
    return datetime.strptime(raw, "%Y%m%d")


def load_all():
    files = sorted(glob.glob(os.path.join(DATA_DIR, "49YTW_portfolio_????????.csv")))
    history = []
    for f in files:
        history.append((parse_date(f), load_csv(f)))
    return history


def plot_top10_trend(history):
    if not history:
        return None

    latest_date, latest_data = history[-1]
    top10_codes = sorted(latest_data, key=lambda c: latest_data[c]["weight"], reverse=True)[:10]

    dates = [d for d, _ in history]
    date_labels = [d.strftime("%m/%d") for d in dates]

    fig, ax = plt.subplots(figsize=(11, 6))
    colors = plt.cm.tab10.colors

    for i, code in enumerate(top10_codes):
        weights = []
        for _, data in history:
            weights.append(data.get(code, {}).get("weight", None))
        name = latest_data[code]["name"]
        label = f"{code} {name}"

        valid_x = [date_labels[j] for j, w in enumerate(weights) if w is not None]
        valid_y = [w for w in weights if w is not None]

        if valid_x:
            ax.plot(valid_x, valid_y, marker="o", linewidth=2,
                    markersize=5, color=colors[i % 10], label=label)

    ax.set_title("49YTW Top 10 持股權重趨勢", fontsize=14, fontweight="bold", pad=12)
    ax.set_xlabel("日期", fontsize=11)
    ax.set_ylabel("持股權重 (%)", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.legend(loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=9, framealpha=0.8)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_facecolor("#f9f9f9")
    fig.patch.set_facecolor("white")
    plt.tight_layout()

    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, "top10_trend.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → 已儲存：{path}")
    return path


def plot_latest_bar(history):
    if not history:
        return None

    latest_date, latest_data = history[-1]
    top20 = sorted(latest_data.items(), key=lambda kv: kv[1]["weight"], reverse=True)[:20]

    codes = [f"{kv[0]}\n{kv[1]['name']}" for kv in top20]
    weights = [kv[1]["weight"] for kv in top20]

    fig, ax = plt.subplots(figsize=(13, 6))
    bars = ax.bar(codes, weights, color=plt.cm.Blues(
        [0.4 + 0.5 * (w / max(weights)) for w in weights]
    ), edgecolor="white", linewidth=0.5)

    for bar, w in zip(bars, weights):
        ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
                f"{w}%", ha="center", va="bottom", fontsize=7.5)

    ax.set_title(
        f"49YTW 持股分佈 Top 20（{latest_date.strftime('%Y/%m/%d')}）",
        fontsize=14, fontweight="bold", pad=12,
    )
    ax.set_ylabel("持股權重 (%)", fontsize=11)
    ax.yaxis.set_major_formatter(mticker.FormatStrFormatter("%.1f%%"))
    ax.tick_params(axis="x", labelsize=7.5)
    ax.grid(axis="y", linestyle="--", alpha=0.5)
    ax.set_facecolor("#f9f9f9")
    fig.patch.set_facecolor("white")
    plt.tight_layout()

    os.makedirs(REPORT_DIR, exist_ok=True)
    path = os.path.join(REPORT_DIR, "latest_bar.png")
    fig.savefig(path, dpi=150, bbox_inches="tight")
    plt.close(fig)
    print(f"  → 已儲存：{path}")
    return path


if __name__ == "__main__":
    history = load_all()
    if not history:
        print("找不到歷史資料，略過圖表產生。")
    else:
        print(f"載入 {len(history)} 天資料，產生圖表中...")
        plot_top10_trend(history)
        plot_latest_bar(history)
        print("完成！")
