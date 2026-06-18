<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { supabase } from '@/lib/supabase'
import { pct, rate, retColor } from '@/lib/format'
import EquityChart from '@/components/EquityChart.vue'

interface Scope {
  scope: string; n_trades: number; win_rate?: number; avg_return?: number
  median_return?: number; avg_bm_return?: number | null
  avg_alpha?: number | null; beat_bm_rate?: number | null
}
interface TradeRow {
  ticker: string; name_zh: string; market: string; ep_date: string
  entry_date: string; exit_date: string; ret: number
  bm_ret: number | null; alpha: number | null
}
interface Strategy {
  id: string; label: string; scopes: Scope[]
  trades?: TradeRow[]; equity_curve?: { date: string; value: number }[]
}
interface HitRow {
  horizon: number; n: number; pct_positive?: number
  avg_return?: number; avg_alpha?: number | null; beat_bm_rate?: number | null
}

const loading = ref(true)
const referenceDate = ref('')
const holdDays = ref(60)
const strategies = ref<Strategy[]>([])
const hitRate = ref<HitRow[]>([])

// 回測區間篩選（ep_date 範圍）
const dateMin = ref('')
const dateMax = ref('')
const filterFrom = ref('')
const filterTo = ref('')

const scopeLabel: Record<string, string> = { ALL: '全部', TW: '台股', US: '美股' }

onMounted(async () => {
  const { data } = await supabase
    .from('backtest_runs')
    .select('*')
    .order('created_at', { ascending: false })
    .limit(1)
    .single()
  if (data) {
    referenceDate.value = data.reference_date ?? ''
    const r = data.results
    holdDays.value = r.hold_days ?? 60
    strategies.value = r.strategies ?? []
    hitRate.value = r.hit_rate ?? []

    // 從 trades 推算可用日期範圍
    const allDates = (r.strategies ?? [])
      .flatMap((s: Strategy) => (s.trades ?? []).map((t: TradeRow) => t.ep_date))
      .filter(Boolean).sort()
    if (allDates.length) {
      dateMin.value = allDates[0]
      dateMax.value = allDates[allDates.length - 1]
      filterTo.value = allDates[allDates.length - 1]
      const oneYearAgo = new Date()
      oneYearAgo.setFullYear(oneYearAgo.getFullYear() - 1)
      const oneYearAgoStr = oneYearAgo.toISOString().slice(0, 10)
      filterFrom.value = allDates.find((d: string) => d >= oneYearAgoStr) ?? allDates[0]
    }
  }
  loading.value = false
})

// 客戶端重算聚合（依 ep_date 篩選後的 trades）
function aggregate(trades: TradeRow[], scope: string) {
  const sel = scope === 'ALL' ? trades : trades.filter(t => t.market === scope)
  if (!sel.length) return { scope, n_trades: 0 }
  const rets = sel.map(t => t.ret)
  const withBm = sel.filter(t => t.bm_ret !== null && t.bm_ret !== undefined)
  const alphas = withBm.map(t => t.ret - t.bm_ret!)
  const mean = (arr: number[]) => arr.reduce((a, b) => a + b, 0) / arr.length
  return {
    scope,
    n_trades: sel.length,
    win_rate: rets.filter(r => r > 0).length / rets.length,
    avg_return: mean(rets),
    avg_bm_return: withBm.length ? mean(withBm.map(t => t.bm_ret!)) : null,
    avg_alpha: alphas.length ? mean(alphas) : null,
    beat_bm_rate: alphas.length ? alphas.filter(a => a > 0).length / alphas.length : null,
  }
}

function equityCurveFrom(trades: TradeRow[]) {
  const sorted = [...trades].sort((a, b) => a.exit_date.localeCompare(b.exit_date))
  let sum = 0
  return sorted.map((t, i) => {
    sum += t.ret
    return { date: t.exit_date, value: parseFloat((sum / (i + 1)).toFixed(4)) }
  })
}

const filteredStrategies = computed(() =>
  strategies.value.map(st => {
    const trades = (st.trades ?? []).filter(
      t => t.ep_date >= filterFrom.value && t.ep_date <= filterTo.value,
    )
    return {
      ...st,
      _trades: trades,
      _scopes: ['ALL', 'TW', 'US'].map(sc => aggregate(trades, sc)),
      _curve: equityCurveFrom(trades),
    }
  }),
)

// 每個策略展開交易清單
const expanded = ref<Record<string, boolean>>({})
function toggle(id: string) { expanded.value[id] = !expanded.value[id] }

function topBottomBy(trades: TradeRow[], key: 'ret' | 'alpha', n = 5) {
  const valid = trades.filter(t => t[key] !== null && t[key] !== undefined)
  const sorted = [...valid].sort((a, b) => (b[key] as number) - (a[key] as number))
  return { top: sorted.slice(0, n), bottom: sorted.slice(-n).reverse() }
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">回測</h1>
      <span v-if="referenceDate" class="ref-date">資料截至 {{ referenceDate }}</span>
    </div>

    <div class="disclaimer">
      ⚠️ 樣本集中於 2025–2026 年，包含 AI／半導體大多頭行情，絕對報酬偏高。
      請以<strong>超額報酬（α）與勝率</strong>為主要判讀依據，過去績效不代表未來。非投資建議。
    </div>

    <p v-if="loading" class="loading">載入中 …</p>

    <template v-else>
      <!-- 回測區間篩選 -->
      <section class="filter-bar">
        <span class="filter-label">回測區間</span>
        <input type="date" v-model="filterFrom" :min="dateMin" :max="filterTo" class="date-input" />
        <span class="filter-sep">—</span>
        <input type="date" v-model="filterTo" :min="filterFrom" :max="dateMax" class="date-input" />
        <button class="reset-btn" @click="filterFrom = dateMin; filterTo = dateMax">全部</button>
        <span class="filter-count">
          共 {{ filteredStrategies[0]?._trades?.length ?? 0 }} 筆交易（S1）
        </span>
      </section>

      <!-- 三種策略 -->
      <section v-for="st in filteredStrategies" :key="st.id" class="strat">
        <h2 class="strat-title"><span class="sid">{{ st.id }}</span> {{ st.label }}</h2>

        <!-- 資金曲線 -->
        <div class="curve-wrap">
          <EquityChart :curve="st._curve" :width="700" :height="110" />
        </div>

        <!-- 聚合統計表 -->
        <table class="bt-table">
          <thead>
            <tr>
              <th>範圍</th><th>交易數</th><th>勝率</th><th>平均報酬</th>
              <th>基準報酬</th><th>超額(α)</th><th>贏基準比例</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sc in st._scopes" :key="sc.scope" :class="{ dim: !sc.n_trades }">
              <td>{{ scopeLabel[sc.scope] }}</td>
              <td class="num">{{ sc.n_trades || '—' }}</td>
              <td class="num">{{ rate(sc.win_rate) }}</td>
              <td class="num" :style="{ color: retColor(sc.avg_return) }">{{ pct(sc.avg_return) }}</td>
              <td class="num muted">{{ pct(sc.avg_bm_return) }}</td>
              <td class="num" :style="{ color: retColor(sc.avg_alpha) }"><strong>{{ pct(sc.avg_alpha) }}</strong></td>
              <td class="num">{{ rate(sc.beat_bm_rate) }}</td>
            </tr>
          </tbody>
        </table>

        <!-- Top / Bottom performers -->
        <template v-if="st._trades.length">
          <div class="performers">
            <div class="perf-col">
              <div class="perf-head win">最佳 5 檔（α）</div>
              <div v-for="t in topBottomBy(st._trades, 'alpha').top" :key="t.ticker + t.entry_date" class="perf-row">
                <span class="perf-ticker">{{ t.ticker }}</span>
                <span class="perf-name">{{ t.name_zh }}</span>
                <span class="perf-val win">{{ pct(t.alpha) }}</span>
              </div>
            </div>
            <div class="perf-col">
              <div class="perf-head loss">最差 5 檔（α）</div>
              <div v-for="t in topBottomBy(st._trades, 'alpha').bottom" :key="t.ticker + t.entry_date" class="perf-row">
                <span class="perf-ticker">{{ t.ticker }}</span>
                <span class="perf-name">{{ t.name_zh }}</span>
                <span class="perf-val loss">{{ pct(t.alpha) }}</span>
              </div>
            </div>
          </div>
        </template>

        <!-- 展開交易清單 -->
        <button class="expand-btn" @click="toggle(st.id)">
          {{ expanded[st.id] ? '收合' : `查看 ${st._trades.length} 筆交易 ▾` }}
        </button>
        <div v-show="expanded[st.id]" class="trade-log">
          <table class="bt-table small">
            <thead>
              <tr><th>股票</th><th>市場</th><th>集日期</th><th>進場</th><th>出場</th><th>報酬</th><th>超額(α)</th></tr>
            </thead>
            <tbody>
              <tr v-for="t in st._trades" :key="t.ticker + t.entry_date">
                <td><span class="ticker">{{ t.ticker }}</span> {{ t.name_zh }}</td>
                <td>{{ t.market }}</td>
                <td class="mono">{{ t.ep_date }}</td>
                <td class="mono">{{ t.entry_date }}</td>
                <td class="mono">{{ t.exit_date }}</td>
                <td class="num" :style="{ color: retColor(t.ret) }">{{ pct(t.ret) }}</td>
                <td class="num" :style="{ color: retColor(t.alpha) }"><strong>{{ pct(t.alpha) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>

      <!-- 命中率 -->
      <section class="strat">
        <h2 class="strat-title">📊 看多訊號命中率</h2>
        <p class="strat-desc">每次「看多」後 N 天，股價上漲的比例與平均報酬</p>
        <table class="bt-table">
          <thead>
            <tr><th>持有天數</th><th>樣本數</th><th>上漲比例</th><th>平均報酬</th><th>超額(α)</th><th>贏基準比例</th></tr>
          </thead>
          <tbody>
            <tr v-for="h in hitRate" :key="h.horizon">
              <td>{{ h.horizon }} 天</td>
              <td class="num">{{ h.n || '—' }}</td>
              <td class="num">{{ rate(h.pct_positive) }}</td>
              <td class="num" :style="{ color: retColor(h.avg_return) }">{{ pct(h.avg_return) }}</td>
              <td class="num" :style="{ color: retColor(h.avg_alpha) }">{{ pct(h.avg_alpha) }}</td>
              <td class="num">{{ rate(h.beat_bm_rate) }}</td>
            </tr>
          </tbody>
        </table>
      </section>

      <p class="method">
        交易假設：進場價為集發布日隔日起第一個收盤，收盤對收盤計算；基準 TW→0050、US→SPY。
        S2 持有 {{ holdDays }} 天。折線圖為「累計平均報酬」（隨交易結算逐筆更新的移動均值）。
      </p>
    </template>
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 1rem; }
.page-title { font-size: 1.4rem; font-weight: 700; color: #63b3ed; }
.ref-date { font-size: 0.78rem; color: #718096; }
.loading { color: #718096; }

.disclaimer {
  background: #2d2410; color: #f6ad55; font-size: 0.82rem; line-height: 1.6;
  padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1.25rem;
}
.disclaimer strong { color: #fbd38d; }

/* 篩選列 */
.filter-bar {
  display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
  background: #1a1f2e; padding: 0.6rem 1rem; border-radius: 8px; margin-bottom: 1.5rem;
}
.filter-label { font-size: 0.8rem; color: #718096; white-space: nowrap; }
.filter-sep { color: #718096; }
.date-input {
  background: #0d1117; color: #e2e8f0; border: 1px solid #2d3748;
  border-radius: 4px; padding: 0.25rem 0.5rem; font-size: 0.8rem; outline: none;
}
.reset-btn {
  background: #2d3748; color: #a0aec0; border: none; border-radius: 4px;
  padding: 0.25rem 0.6rem; font-size: 0.78rem; cursor: pointer;
}
.reset-btn:hover { background: #4a5568; }
.filter-count { font-size: 0.75rem; color: #4a5568; margin-left: auto; }

.strat { margin-bottom: 2.5rem; }
.strat-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 0.4rem; }
.strat-title .sid { color: #63b3ed; font-family: monospace; margin-right: 0.3rem; }
.strat-desc { font-size: 0.8rem; color: #718096; margin-bottom: 0.75rem; }

.curve-wrap { margin-bottom: 0.75rem; }

.bt-table { width: 100%; border-collapse: collapse; }
.bt-table th {
  text-align: left; padding: 0.5rem 0.9rem; background: #1a1f2e; color: #718096;
  font-size: 0.76rem; font-weight: 600; border-bottom: 1px solid #2d3748;
}
.bt-table td { padding: 0.5rem 0.9rem; border-bottom: 1px solid #1e2535; font-size: 0.85rem; }
.bt-table.small td { padding: 0.35rem 0.7rem; font-size: 0.78rem; }
.bt-table tr.dim td { color: #4a5568; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.muted { color: #718096; }
.mono { font-family: monospace; font-size: 0.78rem; color: #718096; }
.ticker { font-family: monospace; color: #90cdf4; font-weight: 600; margin-right: 0.3rem; }

/* Performers */
.performers {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
  margin: 0.75rem 0;
}
.perf-col { background: #1a1f2e; border-radius: 6px; padding: 0.5rem 0.75rem; }
.perf-head { font-size: 0.74rem; font-weight: 600; margin-bottom: 0.4rem; }
.perf-head.win { color: #68d391; }
.perf-head.loss { color: #fc8181; }
.perf-row { display: flex; align-items: baseline; gap: 0.4rem; padding: 0.2rem 0; font-size: 0.78rem; }
.perf-ticker { font-family: monospace; color: #90cdf4; font-weight: 600; min-width: 3.5rem; }
.perf-name { color: #a0aec0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.perf-val { font-variant-numeric: tabular-nums; font-size: 0.8rem; margin-left: auto; }
.perf-val.win { color: #68d391; }
.perf-val.loss { color: #fc8181; }

/* 展開按鈕 & 交易清單 */
.expand-btn {
  background: none; border: 1px solid #2d3748; color: #718096;
  border-radius: 4px; padding: 0.3rem 0.7rem; font-size: 0.76rem;
  cursor: pointer; margin-top: 0.5rem;
}
.expand-btn:hover { background: #1a1f2e; color: #a0aec0; }
.trade-log { margin-top: 0.5rem; max-height: 360px; overflow-y: auto; border-radius: 6px; }

.method { font-size: 0.76rem; color: #718096; line-height: 1.6; margin-top: 1rem; }
</style>
