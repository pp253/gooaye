<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase } from '@/lib/supabase'
import { pct, rate, retColor } from '@/lib/format'

interface Scope {
  scope: string
  n_trades: number
  win_rate?: number
  avg_return?: number
  median_return?: number
  avg_bm_return?: number | null
  avg_alpha?: number | null
  beat_bm_rate?: number | null
}
interface Strategy { id: string; label: string; scopes: Scope[] }
interface HitRow { horizon: number; n: number; pct_positive?: number; avg_return?: number; avg_alpha?: number | null; beat_bm_rate?: number | null }

const loading = ref(true)
const referenceDate = ref('')
const holdDays = ref(60)
const strategies = ref<Strategy[]>([])
const hitRate = ref<HitRow[]>([])

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
  }
  loading.value = false
})
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">回測</h1>
      <span v-if="referenceDate" class="ref-date">資料截至 {{ referenceDate }}</span>
    </div>

    <div class="disclaimer">
      ⚠️ 本回測樣本為 2026 上半年（EP622–671），正逢 AI／半導體大多頭，絕對報酬偏高。
      請以<strong>「超額報酬（vs 各市場基準）」與「勝率」</strong>為主要判讀依據，且過去績效不代表未來。非投資建議。
    </div>

    <p v-if="loading" class="loading">載入中 …</p>

    <template v-else>
      <!-- 三種策略 -->
      <section v-for="st in strategies" :key="st.id" class="strat">
        <h2 class="strat-title"><span class="sid">{{ st.id }}</span> {{ st.label }}</h2>
        <table class="bt-table">
          <thead>
            <tr>
              <th>範圍</th><th>交易數</th><th>勝率</th><th>平均報酬</th>
              <th>基準報酬</th><th>超額(α)</th><th>贏基準比例</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="sc in st.scopes" :key="sc.scope" :class="{ dim: !sc.n_trades }">
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
      </section>

      <!-- 命中率 -->
      <section class="strat">
        <h2 class="strat-title">📊 看多訊號命中率</h2>
        <p class="strat-desc">他每次「看多」之後 N 天，股價上漲的比例與平均報酬（含對基準的超額）</p>
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
        交易假設：進場價為該集發布日「隔日起」第一個收盤，收盤對收盤計算；基準為 TW→0050、US→SPY。
        S2 持有 {{ holdDays }} 天。
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
  padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1.75rem;
}
.disclaimer strong { color: #fbd38d; }

.strat { margin-bottom: 2rem; }
.strat-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 0.3rem; }
.strat-title .sid { color: #63b3ed; font-family: monospace; margin-right: 0.3rem; }
.strat-desc { font-size: 0.8rem; color: #718096; margin-bottom: 0.75rem; }

.bt-table { width: 100%; border-collapse: collapse; }
.bt-table th {
  text-align: left; padding: 0.5rem 0.9rem; background: #1a1f2e; color: #718096;
  font-size: 0.76rem; font-weight: 600; border-bottom: 1px solid #2d3748;
}
.bt-table td { padding: 0.5rem 0.9rem; border-bottom: 1px solid #1e2535; font-size: 0.85rem; }
.bt-table tr.dim td { color: #4a5568; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.muted { color: #718096; }

.method { font-size: 0.76rem; color: #718096; line-height: 1.6; margin-top: 1rem; }
</style>
