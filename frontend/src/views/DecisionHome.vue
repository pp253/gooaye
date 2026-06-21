<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { loadStockSignals, type StockRow } from '@/lib/useData'
import { TRADEABLE_TYPES } from '@/lib/types'
import { pct, retColor } from '@/lib/format'
import { useQuerySync } from '@/lib/useQuerySync'
import FreshnessLabel from '@/components/FreshnessLabel.vue'
import ScoreLabel from '@/components/ScoreLabel.vue'

const rows = ref<StockRow[]>([])
const referenceDate = ref('')
const loading = ref(true)

const dirColor: Record<string, string> = {
  看多: '#68d391',
  看空: '#fc8181',
  中性: '#90cdf4',
}

const assetView = ref<'tradeable' | 'theme' | 'all'>('tradeable')
const market = ref<'ALL' | 'TW' | 'US'>('ALL')
const viewMode = ref<'card' | 'table'>('card')

useQuerySync({
  asset: { ref: assetView, default: 'tradeable' },
  market: { ref: market, default: 'ALL' },
  view: { ref: viewMode, default: 'card' },
})

// 套用資產類型 + 市場篩選後的基底
const filtered = computed(() => {
  let list = rows.value.slice()
  if (assetView.value === 'tradeable') list = list.filter((r) => TRADEABLE_TYPES.includes(r.asset_type))
  else if (assetView.value === 'theme') list = list.filter((r) => !TRADEABLE_TYPES.includes(r.asset_type))
  if (market.value !== 'ALL') list = list.filter((r) => r.market === market.value)
  return list
})

// 只看「近期（非過期）」的訊號做決策
const fresh = computed(() => filtered.value.filter((r) => r.signal.latest_freshness !== 'stale'))

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
// 3. 最新提及（近一個月內被談到的標的）
const recent = computed(() =>
  filtered.value
    .filter((r) => r.signal.latest_days_ago <= 30)
    .sort((a, b) => a.signal.latest_days_ago - b.signal.latest_days_ago),
)
// 4. 近一個月首次提及（資料集有紀錄以來第一次被談到）
const newlyMentioned = computed(() =>
  filtered.value
    .filter((r) => r.signal.first_mention_days_ago <= 30)
    .sort((a, b) => a.signal.first_mention_days_ago - b.signal.first_mention_days_ago),
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
      <div class="controls">
        <div class="ctrl-group">
          <button v-for="a in (['tradeable', 'theme', 'all'] as const)" :key="a"
            :class="['chip', { active: assetView === a }]" @click="assetView = a">
            {{ a === 'tradeable' ? '可交易（個股/ETF）' : a === 'theme' ? '題材/指數' : '全部' }}
          </button>
        </div>
        <div class="ctrl-group">
          <button v-for="f in (['ALL', 'TW', 'US'] as const)" :key="f"
            :class="['chip', { active: market === f }]" @click="market = f">
            {{ f === 'ALL' ? '全部市場' : f }}
          </button>
        </div>
        <div class="ctrl-group ctrl-view">
          <button :class="['chip', { active: viewMode === 'card' }]" @click="viewMode = 'card'" title="卡片">⊞</button>
          <button :class="['chip', { active: viewMode === 'table' }]" @click="viewMode = 'table'" title="列表">☰</button>
        </div>
      </div>

      <!-- ══ 有部位 ══ -->
      <section class="board">
        <h2 class="board-title">🔴 謝孟恭有部位</h2>
        <p class="board-desc">他自己的錢也在裡面——最值得參考的訊號</p>
        <!-- card -->
        <div v-if="viewMode === 'card'" class="card-row">
          <RouterLink v-for="r in hasPosition" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-dir" :style="{ color: dirColor[r.signal.latest_direction] }">{{ r.signal.latest_direction }}</span>
              <span class="sc-score">分數 {{ r.signal.score.toFixed(2) }}</span>
            </div>
            <div class="sc-fresh"><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span v-if="r.performance.ret_since_last_bull != null" :style="{ color: retColor(r.performance.ret_since_last_bull) }">
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </RouterLink>
          <p v-if="hasPosition.length === 0" class="empty">近期無此類訊號</p>
        </div>
        <!-- table -->
        <template v-else>
          <p v-if="hasPosition.length === 0" class="empty">近期無此類訊號</p>
          <table v-else class="d-table">
            <thead><tr><th>個股</th><th>方向</th><th>分數</th><th>現價</th><th>最近看多</th><th>時效</th></tr></thead>
            <tbody>
              <tr v-for="r in hasPosition" :key="r.id">
                <td><RouterLink :to="`/stocks/${r.id}`" class="tl-link"><b class="tl-ticker">{{ r.ticker }}</b> {{ r.name_zh }}</RouterLink></td>
                <td><span :style="{ color: dirColor[r.signal.latest_direction] }">{{ r.signal.latest_direction }}</span></td>
                <td><ScoreLabel :score="r.signal.score" /></td>
                <td class="num">{{ r.performance?.current_price ?? '—' }}</td>
                <td class="num" :style="{ color: retColor(r.performance?.ret_since_last_bull) }">{{ pct(r.performance?.ret_since_last_bull) }}</td>
                <td><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></td>
              </tr>
            </tbody>
          </table>
        </template>
      </section>

      <!-- ══ 高分看多 ══ -->
      <section class="board">
        <h2 class="board-title">🟢 高分看多</h2>
        <p class="board-desc">近期語氣積極、且經時間加權後分數最高</p>
        <!-- card -->
        <div v-if="viewMode === 'card'" class="card-row">
          <RouterLink v-for="r in topBull" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
              <span v-if="r.signal.bull_streak >= 2" class="sc-streak">🔥{{ r.signal.bull_streak }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-score-big" :style="{ color: '#68d391' }">+{{ r.signal.score.toFixed(2) }}</span>
            </div>
            <div class="sc-fresh"><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span v-if="r.performance.ret_since_last_bull != null" :style="{ color: retColor(r.performance.ret_since_last_bull) }">
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </RouterLink>
          <p v-if="topBull.length === 0" class="empty">近期無此類訊號</p>
        </div>
        <!-- table -->
        <template v-else>
          <p v-if="topBull.length === 0" class="empty">近期無此類訊號</p>
          <table v-else class="d-table">
            <thead><tr><th>個股</th><th>連多</th><th>分數</th><th>現價</th><th>最近看多</th><th>時效</th></tr></thead>
            <tbody>
              <tr v-for="r in topBull" :key="r.id">
                <td><RouterLink :to="`/stocks/${r.id}`" class="tl-link"><b class="tl-ticker">{{ r.ticker }}</b> {{ r.name_zh }}</RouterLink></td>
                <td class="num">{{ r.signal.bull_streak >= 2 ? `🔥${r.signal.bull_streak}` : r.signal.bull_streak }}</td>
                <td><ScoreLabel :score="r.signal.score" /></td>
                <td class="num">{{ r.performance?.current_price ?? '—' }}</td>
                <td class="num" :style="{ color: retColor(r.performance?.ret_since_last_bull) }">{{ pct(r.performance?.ret_since_last_bull) }}</td>
                <td><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></td>
              </tr>
            </tbody>
          </table>
        </template>
      </section>

      <!-- ══ 近期首次提及 ══ -->
      <section class="board">
        <h2 class="board-title">🆕 近期首次提及</h2>
        <p class="board-desc">近一個月內第一次被謝孟恭談到的標的（{{ newlyMentioned.length }} 檔）——新進場的標的，短期注意流動性相對低</p>
        <!-- card -->
        <div v-if="viewMode === 'card'" class="card-row">
          <RouterLink v-for="r in newlyMentioned" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card new-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-dir" :style="{ color: dirColor[r.signal.latest_direction] }">{{ r.signal.latest_direction }}</span>
            </div>
            <div class="sc-fresh" style="color: #9ae6b4">🆕 首次：{{ r.signal.first_mention_date }}</div>
            <div class="sc-fresh"><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></div>
          </RouterLink>
          <p v-if="newlyMentioned.length === 0" class="empty">近一個月無新首次提及的標的</p>
        </div>
        <!-- table -->
        <template v-else>
          <p v-if="newlyMentioned.length === 0" class="empty">近一個月無新首次提及的標的</p>
          <table v-else class="d-table">
            <thead><tr><th>個股</th><th>方向</th><th>首次提及</th><th>最近提及</th></tr></thead>
            <tbody>
              <tr v-for="r in newlyMentioned" :key="r.id">
                <td><RouterLink :to="`/stocks/${r.id}`" class="tl-link"><b class="tl-ticker">{{ r.ticker }}</b> {{ r.name_zh }}</RouterLink></td>
                <td><span :style="{ color: dirColor[r.signal.latest_direction] }">{{ r.signal.latest_direction }}</span></td>
                <td style="color:#9ae6b4"><FreshnessLabel :days-ago="r.signal.first_mention_days_ago" /></td>
                <td><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></td>
              </tr>
            </tbody>
          </table>
        </template>
      </section>

      <!-- ══ 最新提及 ══ -->
      <section class="board">
        <h2 class="board-title">🆕 最新提及</h2>
        <p class="board-desc">近一個月內被談到的標的（{{ recent.length }} 檔）</p>
        <!-- card -->
        <div v-if="viewMode === 'card'" class="card-row">
          <RouterLink v-for="r in recent" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-dir" :style="{ color: dirColor[r.signal.latest_direction] }">{{ r.signal.latest_direction }}</span>
            </div>
            <div class="sc-fresh"><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span v-if="r.performance.ret_since_last_bull != null" :style="{ color: retColor(r.performance.ret_since_last_bull) }">
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </RouterLink>
        </div>
        <!-- table -->
        <table v-else class="d-table">
          <thead><tr><th>個股</th><th>方向</th><th>現價</th><th>最近看多</th><th>時效</th></tr></thead>
          <tbody>
            <tr v-for="r in recent" :key="r.id">
              <td><RouterLink :to="`/stocks/${r.id}`" class="tl-link"><b class="tl-ticker">{{ r.ticker }}</b> {{ r.name_zh }}</RouterLink></td>
              <td><span :style="{ color: dirColor[r.signal.latest_direction] }">{{ r.signal.latest_direction }}</span></td>
              <td class="num">{{ r.performance?.current_price ?? '—' }}</td>
              <td class="num" :style="{ color: retColor(r.performance?.ret_since_last_bull) }">{{ pct(r.performance?.ret_since_last_bull) }}</td>
              <td><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></td>
            </tr>
          </tbody>
        </table>
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

.controls { display: flex; flex-wrap: wrap; gap: 1.25rem; margin-bottom: 1.75rem; }
.ctrl-group { display: flex; align-items: center; gap: 0.4rem; }

.ctrl-view { margin-left: auto; }

.chip {
  background: #2d3748; color: #a0aec0; border: none; border-radius: 6px;
  padding: 0.3rem 0.7rem; cursor: pointer; font-size: 0.8rem;
  transition: background 0.15s, color 0.15s;
}
.chip:hover { background: #374151; }
.chip.active { background: #63b3ed; color: #1a1f2e; font-weight: 600; }

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
.new-card { border-color: #2d4a3e; }
.new-card:hover { border-color: #9ae6b4; }

/* ── Table view ────────────────────────────────── */
.d-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
.d-table th {
  text-align: left; padding: 0.5rem 0.7rem;
  background: #1a1f2e; color: #718096; font-size: 0.76rem; font-weight: 600;
  border-bottom: 1px solid #2d3748; white-space: nowrap;
}
.d-table td { padding: 0.5rem 0.7rem; border-bottom: 1px solid #1e2535; vertical-align: middle; white-space: nowrap; }
.d-table tr:hover td { background: #1a1f2e; }
.d-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.tl-link { text-decoration: none; color: inherit; display: flex; align-items: baseline; gap: 0.4rem; }
.tl-link:hover .tl-ticker { text-decoration: underline; }
.tl-ticker { font-family: monospace; font-weight: 700; color: #90cdf4; }

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
