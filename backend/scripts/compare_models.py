"""比較數個 OpenAI 模型在逐字稿抽取上的能力差異。

對固定樣本集數、用相同 prompt + schema 跑各模型，輸出：
  量化指標（提及數、真實ticker比例、雜訊比例、tokens、延遲、成本）
  + 與旗艦(gpt-5.4)的一致率
  + 各模型並排輸出（供人工檢視）

只讀 data/raw、輸出到 data/model_compare/，不碰 Supabase。

用法：uv run python scripts/compare_models.py
"""

from __future__ import annotations

import json
import time
from pathlib import Path

from openai import OpenAI

from gooaye import config
from gooaye.extractor.extract import _SYSTEM_PROMPT
from gooaye.extractor.schema import EpisodeExtraction
from gooaye.normalize import resolve

MODELS = ["gpt-5.4", "gpt-5.4-mini", "gpt-5.4-nano"]
REFERENCE = "gpt-5.4"
EPISODES = [641, 596, 660, 671, 663]

# 每百萬 tokens 美元（2026-06 公告價）
PRICES = {
    "gpt-5.4": (2.50, 15.00),
    "gpt-5.4-mini": (0.75, 4.50),
    "gpt-5.4-nano": (0.20, 1.25),
}

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"
OUT_DIR = Path(__file__).resolve().parents[1] / "data" / "model_compare"


def call(client: OpenAI, model: str, transcript: str) -> dict:
    """回傳 {parsed, in_tok, out_tok, latency, error}。"""
    t0 = time.time()
    try:
        resp = client.responses.parse(
            model=model,
            reasoning={"effort": "low"},
            input=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f"以下是單集逐字稿：\n\n{transcript}"},
            ],
            text_format=EpisodeExtraction,
        )
        latency = time.time() - t0
        usage = resp.usage
        return {
            "parsed": resp.output_parsed,
            "in_tok": getattr(usage, "input_tokens", 0),
            "out_tok": getattr(usage, "output_tokens", 0),
            "latency": round(latency, 1),
            "error": None,
        }
    except Exception as exc:  # noqa: BLE001
        return {"parsed": None, "in_tok": 0, "out_tok": 0,
                "latency": round(time.time() - t0, 1), "error": f"{type(exc).__name__}: {exc}"}


def classify(ext: EpisodeExtraction) -> dict:
    """用 normalize 把抽取結果分類，回傳量化指標 + ticker→direction 對照。"""
    tradeable = 0
    theme = 0
    by_ticker: dict[str, str] = {}
    for m in ext.mentions:
        r = resolve(m.name_raw, m.ticker_guess, m.market)
        if r.asset_type in ("個股", "ETF"):
            tradeable += 1
        else:
            theme += 1
        by_ticker[r.ticker] = m.direction
    return {
        "n_mentions": len(ext.mentions),
        "n_tradeable": tradeable,
        "n_theme": theme,
        "n_summary": len(ext.summary),
        "by_ticker": by_ticker,
    }


def agreement(ref: dict, other: dict) -> dict:
    """other 相對 ref 的個股重疊與方向一致率。"""
    rset = set(ref["by_ticker"])
    oset = set(other["by_ticker"])
    inter = rset & oset
    dir_match = sum(1 for t in inter if ref["by_ticker"][t] == other["by_ticker"][t])
    return {
        "overlap_vs_ref": round(len(inter) / len(rset), 2) if rset else None,
        "extra_vs_ref": len(oset - rset),  # ref 沒抓到、它多抓的
        "dir_agree": round(dir_match / len(inter), 2) if inter else None,
    }


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    client = OpenAI(api_key=config.OPENAI_API_KEY)

    # results[ep][model] = {metrics..., parsed, cost...}
    results: dict[int, dict[str, dict]] = {}
    for ep in EPISODES:
        raw = json.loads((RAW_DIR / f"EP{ep}.json").read_text(encoding="utf-8"))
        tx = raw["transcript"]
        results[ep] = {}
        print(f"\n=== EP{ep}（{len(tx)} 字）===")
        for model in MODELS:
            r = call(client, model, tx)
            if r["error"] or r["parsed"] is None:
                print(f"  {model:14} 失敗: {r['error']}")
                results[ep][model] = {"error": r["error"]}
                continue
            metrics = classify(r["parsed"])
            pin, pout = PRICES[model]
            cost = r["in_tok"] / 1e6 * pin + r["out_tok"] / 1e6 * pout
            rec = {
                **metrics,
                "in_tok": r["in_tok"], "out_tok": r["out_tok"],
                "latency": r["latency"], "cost": round(cost, 5),
                "parsed": r["parsed"].model_dump(),
            }
            results[ep][model] = rec
            print(f"  {model:14} 提及{metrics['n_mentions']:2}（可交易{metrics['n_tradeable']} 題材{metrics['n_theme']}）"
                  f" summary{metrics['n_summary']} | {r['in_tok']}+{r['out_tok']}tok {r['latency']}s ${cost:.4f}")

    # 存完整輸出
    (OUT_DIR / "results.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )

    # 彙總表（跨集平均）
    print("\n\n=== 跨 5 集彙總 ===")
    print(f"{'模型':16}{'平均提及':>8}{'可交易%':>8}{'題材%':>7}{'avg tok':>10}{'avg秒':>7}{'總成本$':>9}{'重疊率':>8}{'方向一致':>9}")
    summary_rows = []
    for model in MODELS:
        recs = [results[ep][model] for ep in EPISODES if "error" not in results[ep][model]]
        if not recs:
            continue
        n = len(recs)
        avg_men = sum(r["n_mentions"] for r in recs) / n
        tot_men = sum(r["n_mentions"] for r in recs)
        trad_pct = sum(r["n_tradeable"] for r in recs) / tot_men if tot_men else 0
        theme_pct = sum(r["n_theme"] for r in recs) / tot_men if tot_men else 0
        avg_tok = sum(r["in_tok"] + r["out_tok"] for r in recs) / n
        avg_lat = sum(r["latency"] for r in recs) / n
        tot_cost = sum(r["cost"] for r in recs)
        # 與旗艦一致率（跨集平均）
        overlaps, diragrees = [], []
        for ep in EPISODES:
            ref = results[ep].get(REFERENCE)
            cur = results[ep].get(model)
            if not ref or not cur or "error" in ref or "error" in cur:
                continue
            ag = agreement(ref, cur)
            if ag["overlap_vs_ref"] is not None:
                overlaps.append(ag["overlap_vs_ref"])
            if ag["dir_agree"] is not None:
                diragrees.append(ag["dir_agree"])
        ov = sum(overlaps) / len(overlaps) if overlaps else None
        da = sum(diragrees) / len(diragrees) if diragrees else None
        ref_tag = "（基準）" if model == REFERENCE else ""
        print(f"{model:16}{avg_men:>8.1f}{trad_pct:>8.0%}{theme_pct:>7.0%}{avg_tok:>10.0f}{avg_lat:>7.1f}{tot_cost:>9.4f}"
              f"{(ov if ov is not None else 0):>8.0%}{(da if da is not None else 0):>9.0%} {ref_tag}")
        summary_rows.append(model)

    print(f"\n完整輸出與並排內容存於 {OUT_DIR}/results.json")


if __name__ == "__main__":
    main()
