<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { loadStockSignals, type StockRow } from '@/lib/useData'
import { FRESHNESS_META, relativeTime } from '@/lib/signal'
import { TRADEABLE_TYPES } from '@/lib/types'
import { pct, retColor } from '@/lib/format'

const rows = ref<StockRow[]>([])
const referenceDate = ref('')
const loading = ref(true)

const dirColor: Record<string, string> = {
  看多: '#68d391',
  看空: '#fc8181',
  中性: '#90cdf4',
}

// 決策只看「可直接買賣」的標的（個股 / ETF），題材、指數、商品不列入
const tradeable = computed(() => rows.value.filter((r) => TRADEABLE_TYPES.includes(r.asset_type)))

// 只看「近期（非過期）」的訊號做決策
const fresh = computed(() => tradeable.value.filter((r) => r.signal.latest_freshness !== 'stale'))

// 1. 他有部位（最強訊號）
const hasPosition = computed(() =>
  fresh.value
    .filter((r) => r.signal.has_position_ever)
    .sort((a, b) => b.signal.score - a.signal.score)
    .slice(0, 8),
)
// 2. 高分看多
const topBull = computed(() =>
  fresh.value
    .filter((r) => r.signal.latest_direction === '看多')
    .sort((a, b) => b.signal.score - a.signal.score)
    .slice(0, 8),
)
// 3. 最新提及
const recent = computed(() =>
  [...tradeable.value]
    .sort((a, b) => a.signal.latest_days_ago - b.signal.latest_days_ago)
    .slice(0, 8),
)

onMounted(async () => {
  const res = await loadStockSignals()
  rows.value = res.stocks
  referenceDate.value = res.referenceDate
  loading.value = false
})
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">決策面板</h1>
      <span v-if="referenceDate" class="ref-date">時效基準：{{ referenceDate }}（資料集最新一集）</span>
    </div>
    <p v-if="loading" class="loading">載入中 …</p>

    <template v-else>
      <section class="board">
        <h2 class="board-title">🔴 謝孟恭有部位</h2>
        <p class="board-desc">他自己的錢也在裡面——最值得參考的訊號</p>
        <div class="card-row">
          <RouterLink v-for="r in hasPosition" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-dir" :style="{ color: dirColor[r.signal.latest_direction] }">{{ r.signal.latest_direction }}</span>
              <span class="sc-score">分數 {{ r.signal.score.toFixed(2) }}</span>
            </div>
            <div class="sc-fresh" :style="{ color: FRESHNESS_META[r.signal.latest_freshness].color }">
              {{ FRESHNESS_META[r.signal.latest_freshness].dot }} {{ relativeTime(r.signal.latest_days_ago) }} · EP{{ r.signal.latest_ep }}
            </div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span v-if="r.performance.ret_since_last_bull != null"
                :style="{ color: retColor(r.performance.ret_since_last_bull) }">
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </RouterLink>
          <p v-if="hasPosition.length === 0" class="empty">近期無此類訊號</p>
        </div>
      </section>

      <section class="board">
        <h2 class="board-title">🟢 高分看多</h2>
        <p class="board-desc">近期語氣積極、且經時間加權後分數最高</p>
        <div class="card-row">
          <RouterLink v-for="r in topBull" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
              <span v-if="r.signal.bull_streak >= 2" class="sc-streak">🔥{{ r.signal.bull_streak }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-score-big" :style="{ color: '#68d391' }">+{{ r.signal.score.toFixed(2) }}</span>
            </div>
            <div class="sc-fresh" :style="{ color: FRESHNESS_META[r.signal.latest_freshness].color }">
              {{ FRESHNESS_META[r.signal.latest_freshness].dot }} {{ relativeTime(r.signal.latest_days_ago) }} · EP{{ r.signal.latest_ep }}
            </div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span v-if="r.performance.ret_since_last_bull != null"
                :style="{ color: retColor(r.performance.ret_since_last_bull) }">
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </RouterLink>
          <p v-if="topBull.length === 0" class="empty">近期無此類訊號</p>
        </div>
      </section>

      <section class="board">
        <h2 class="board-title">🆕 最新提及</h2>
        <p class="board-desc">資料集中最近被談到的標的</p>
        <div class="card-row">
          <RouterLink v-for="r in recent" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-dir" :style="{ color: dirColor[r.signal.latest_direction] }">{{ r.signal.latest_direction }}</span>
            </div>
            <div class="sc-fresh" :style="{ color: FRESHNESS_META[r.signal.latest_freshness].color }">
              {{ FRESHNESS_META[r.signal.latest_freshness].dot }} {{ relativeTime(r.signal.latest_days_ago) }} · EP{{ r.signal.latest_ep }}
            </div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span v-if="r.performance.ret_since_last_bull != null"
                :style="{ color: retColor(r.performance.ret_since_last_bull) }">
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </RouterLink>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 1.5rem; }
.page-title { font-size: 1.4rem; font-weight: 700; color: #63b3ed; }
.ref-date { font-size: 0.78rem; color: #718096; }
.loading { color: #718096; }
.empty { color: #718096; font-size: 0.85rem; }

.board { margin-bottom: 2.25rem; }
.board-title { font-size: 1.05rem; font-weight: 700; margin-bottom: 0.2rem; }
.board-desc { font-size: 0.8rem; color: #718096; margin-bottom: 0.9rem; }

.card-row { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 0.75rem; }

.sig-card {
  background: #1a1f2e; border: 1px solid #2d3748; border-radius: 8px;
  padding: 0.8rem 0.9rem; text-decoration: none; color: inherit;
  display: flex; flex-direction: column; gap: 0.45rem;
  transition: border-color 0.15s, background 0.15s;
}
.sig-card:hover { border-color: #63b3ed; background: #1e2535; }

.sc-top { display: flex; align-items: baseline; gap: 0.4rem; }
.sc-ticker { font-family: monospace; font-weight: 700; color: #90cdf4; font-size: 0.95rem; }
.sc-name { color: #cbd5e0; font-size: 0.82rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.sc-streak { color: #f6ad55; font-size: 0.78rem; margin-left: auto; }

.sc-mid { display: flex; align-items: baseline; gap: 0.5rem; }
.sc-dir { font-weight: 700; font-size: 1rem; }
.sc-score { font-size: 0.78rem; color: #718096; }
.sc-score-big { font-size: 1.15rem; font-weight: 700; font-variant-numeric: tabular-nums; }

.sc-fresh { font-size: 0.76rem; font-weight: 500; }
.sc-price { font-size: 0.76rem; color: #cbd5e0; font-variant-numeric: tabular-nums; }
</style>
