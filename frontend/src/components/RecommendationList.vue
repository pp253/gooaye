<script setup lang="ts">
import { pct, retColor } from '@/lib/format'

export interface Rec {
  stock_id: number
  ticker: string
  name_zh: string
  market: string
  asset_type: string
  ep_no: number | null
  signal_date: string
  confidence: number | null
  has_position: boolean | null
  quote: string | null
  entry_date: string
  entry_price: number
  current_date: string
  current_price: number
  ret: number | null
  days_held: number
  fresh: boolean
}

defineProps<{
  recs: Rec[]
  tickerMap: Record<string, number>
}>()

// 進場價與現價以一致小數位顯示（依該列兩值較小者決定位數，讓「進場 → 現價」對齊）
function pairPrice(entry: number, current: number): string {
  const m = Math.min(entry, current)
  const d = m >= 1000 ? 0 : m >= 100 ? 1 : 2
  return `${entry.toFixed(d)} → ${current.toFixed(d)}`
}
</script>

<template>
  <div v-if="recs.length" class="rec-wrap">
    <table class="rec-table">
      <thead>
        <tr>
          <th>狀態</th>
          <th>股票</th>
          <th>市場</th>
          <th>觸發訊號</th>
          <th class="num">信心</th>
          <th>他有部位</th>
          <th class="num">持有天數</th>
          <th class="num">進場 → 現價</th>
          <th class="num">未實現</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in recs" :key="r.ticker + r.entry_date">
          <td>
            <span class="status" :class="r.fresh ? 'buy' : 'hold'">
              {{ r.fresh ? '可買進' : '續抱' }}
            </span>
          </td>
          <td>
            <router-link
              v-if="tickerMap[r.ticker]"
              :to="`/stocks/${tickerMap[r.ticker]}`"
              class="ticker-link"
            >
              <span class="ticker">{{ r.ticker }}</span>
            </router-link>
            <span v-else class="ticker">{{ r.ticker }}</span>
            <span class="name" :title="r.quote ?? ''">{{ r.name_zh }}</span>
          </td>
          <td class="mkt">{{ r.market }}</td>
          <td class="signal">
            <span v-if="r.ep_no" class="ep">EP{{ r.ep_no }}</span>
            <span class="sdate">{{ r.signal_date }}</span>
          </td>
          <td class="num">{{ r.confidence != null ? (r.confidence * 100).toFixed(0) + '%' : '—' }}</td>
          <td>
            <span v-if="r.has_position" class="pos-badge">✓ 有</span>
            <span v-else class="no-pos">—</span>
          </td>
          <td class="num">{{ r.days_held }} 天</td>
          <td class="num mono">
            {{ pairPrice(r.entry_price, r.current_price) }}
          </td>
          <td class="num" :style="{ color: retColor(r.ret) }">
            <strong>{{ pct(r.ret) }}</strong>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
  <p v-else class="rec-empty">此策略目前沒有開倉中的標的（無建議買進）。</p>
</template>

<style scoped>
.rec-wrap {
  max-height: 420px;
  overflow-y: auto;
  border: 1px solid #2d3748;
  border-radius: 8px;
}
.rec-table {
  width: 100%;
  border-collapse: collapse;
}
.rec-table th {
  text-align: left;
  padding: 0.55rem 0.8rem;
  background: #1e2535;
  color: #718096;
  font-size: 0.74rem;
  font-weight: 600;
  border-bottom: 1px solid #2d3748;
  position: sticky;
  top: 0;
  z-index: 1;
}
.rec-table td {
  padding: 0.5rem 0.8rem;
  border-bottom: 1px solid #1e2535;
  font-size: 0.82rem;
  vertical-align: middle;
}
.num { text-align: right; font-variant-numeric: tabular-nums; }
.mono { font-family: monospace; font-size: 0.78rem; color: #a0aec0; }
.mkt { color: #718096; font-size: 0.78rem; }

.status {
  display: inline-block;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 700;
  white-space: nowrap;
}
.status.buy { background: #1c4532; color: #68d391; }
.status.hold { background: #2d3748; color: #a0aec0; }

.ticker { font-family: monospace; color: #63b3ed; font-weight: 600; }
.ticker-link { text-decoration: none; }
.ticker-link:hover .ticker { text-decoration: underline; }
.name { color: #e2e8f0; margin-left: 0.4rem; cursor: help; }

.signal { white-space: nowrap; }
.ep { font-family: monospace; color: #f6ad55; font-size: 0.74rem; margin-right: 0.4rem; }
.sdate { color: #718096; font-size: 0.76rem; }

.pos-badge { color: #68d391; font-weight: 600; font-size: 0.78rem; }
.no-pos { color: #4a5568; }

.rec-empty { color: #4a5568; font-size: 0.82rem; padding: 1rem 0; }
</style>
