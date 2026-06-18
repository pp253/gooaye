"""計算跟單績效快照 + 執行回測，寫回 Supabase。

用法：
    python scripts/run_analytics.py
"""

from __future__ import annotations

from gooaye.db import get_client
from gooaye.analytics import compute_performance, load_price_book, run_backtest


def main() -> None:
    client = get_client()
    print("載入股價 …")
    book = load_price_book(client)
    print(f"  {len(book.by_stock)} 檔有股價；基準市場：{list(book.benchmark_by_market)}")

    print("計算跟單績效快照 …")
    n = compute_performance(client, book)
    print(f"  stock_performance：{n} 檔")

    print("執行回測（三種規則）…")
    res = run_backtest(client, book)
    for st in res["strategies"]:
        allsc = next(s for s in st["scopes"] if s["scope"] == "ALL")
        if allsc.get("n_trades"):
            print(
                f"  [{st['id']}] {st['label']}：{allsc['n_trades']} 筆交易, "
                f"勝率 {allsc['win_rate']:.0%}, 平均報酬 {allsc['avg_return']:+.1%}, "
                f"超額 {allsc.get('avg_alpha')}"
            )
    print("  命中率：")
    for h in res["hit_rate"]:
        if h.get("n"):
            print(
                f"    {h['horizon']}天: n={h['n']}, 上漲 {h['pct_positive']:.0%}, "
                f"平均 {h['avg_return']:+.1%}"
            )
    print("完成")


if __name__ == "__main__":
    main()
