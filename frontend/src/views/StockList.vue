<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { loadStockSignals, type StockRow } from '@/lib/useData'
import { FRESHNESS_META, relativeTime } from '@/lib/signal'
import { TRADEABLE_TYPES } from '@/lib/types'

const rows = ref<StockRow[]>([])
const referenceDate = ref('')
const loading = ref(true)

const assetView = ref<'tradeable' | 'theme' | 'all'>('tradeable')
const market = ref<'ALL' | 'TW' | 'US'>('ALL')
const onlyPosition = ref(false)
const hideStale = ref(true)
const sortBy = ref<'score' | 'recent' | 'count'>('score')

const dirColor: Record<string, string> = {
  看多: '#68d391',
  看空: '#fc8181',
  中性: '#90cdf4',
}

const filtered = computed(() => {
  let list = rows.value.slice()
  if (assetView.value === 'tradeable') list = list.filter((r) => TRADEABLE_TYPES.includes(r.asset_type))
  else if (assetView.value === 'theme') list = list.filter((r) => !TRADEABLE_TYPES.includes(r.asset_type))
  if (market.value !== 'ALL') list = list.filter((r) => r.market === market.value)
  if (onlyPosition.value) list = list.filter((r) => r.signal.has_position_ever)
  if (hideStale.value) list = list.filter((r) => r.signal.latest_freshness !== 'stale')

  list.sort((a, b) => {
    if (sortBy.value === 'score') return b.signal.score - a.signal.score
    if (sortBy.value === 'recent') return a.signal.latest_days_ago - b.signal.latest_days_ago
    return b.signal.mention_count - a.signal.mention_count
  })
  return list
})

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
      <h1 class="page-title">個股追蹤</h1>
      <span v-if="referenceDate" class="ref-date">時效基準：{{ referenceDate }}（資料集最新一集）</span>
    </div>

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
      <div class="ctrl-group">
        <button :class="['chip', { active: onlyPosition }]" @click="onlyPosition = !onlyPosition">
          🔴 只看他有部位
        </button>
        <button :class="['chip', { active: hideStale }]" @click="hideStale = !hideStale">
          隱藏過期（&gt;2月）
        </button>
      </div>
      <div class="ctrl-group sort">
        <span class="sort-label">排序</span>
        <button v-for="s in (['score', 'recent', 'count'] as const)" :key="s"
          :class="['chip', { active: sortBy === s }]" @click="sortBy = s">
          {{ s === 'score' ? '訊號分數' : s === 'recent' ? '最近提及' : '提及次數' }}
        </button>
      </div>
    </div>

    <p v-if="loading" class="loading">載入中 …</p>
    <p v-else-if="filtered.length === 0" class="loading">沒有符合條件的個股</p>
    <table v-else class="stock-table">
      <thead>
        <tr>
          <th>個股</th>
          <th>訊號分數</th>
          <th>目前立場</th>
          <th>最近提及</th>
          <th>連續看多</th>
          <th>次數</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in filtered" :key="r.id">
          <td>
            <RouterLink :to="`/stocks/${r.id}`" class="stock-cell">
              <span class="ticker">{{ r.ticker }}</span>
              <span class="name">{{ r.name_zh }}</span>
              <span :class="['market-badge', r.market.toLowerCase()]">{{ r.market }}</span>
              <span v-if="!['個股','ETF'].includes(r.asset_type)" class="type-badge">{{ r.asset_type }}</span>
              <span v-else-if="r.asset_type === 'ETF'" class="type-badge etf">ETF</span>
              <span v-if="r.signal.has_position_ever" class="pos-flag" title="謝孟恭曾自述有部位">🔴 有部位</span>
            </RouterLink>
          </td>
          <td>
            <div class="score-cell">
              <div class="score-bar-track">
                <div class="score-bar"
                  :style="{
                    width: Math.min(100, Math.abs(r.signal.score) * 40) + '%',
                    background: r.signal.score >= 0 ? '#68d391' : '#fc8181',
                  }" />
              </div>
              <span class="score-num" :style="{ color: r.signal.score >= 0 ? '#68d391' : '#fc8181' }">
                {{ r.signal.score >= 0 ? '+' : '' }}{{ r.signal.score.toFixed(2) }}
              </span>
            </div>
          </td>
          <td>
            <span class="dir" :style="{ color: dirColor[r.signal.latest_direction] }">
              {{ r.signal.latest_direction }}
            </span>
          </td>
          <td>
            <span class="fresh" :style="{ color: FRESHNESS_META[r.signal.latest_freshness].color }">
              {{ FRESHNESS_META[r.signal.latest_freshness].dot }}
              {{ relativeTime(r.signal.latest_days_ago) }}
            </span>
            <span class="ep-ref">EP{{ r.signal.latest_ep }}</span>
          </td>
          <td class="num">
            <span v-if="r.signal.bull_streak >= 2" class="streak">🔥 {{ r.signal.bull_streak }}</span>
            <span v-else class="muted">{{ r.signal.bull_streak }}</span>
          </td>
          <td class="num muted">{{ r.signal.mention_count }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.page-header { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 1.25rem; }
.page-title { font-size: 1.4rem; font-weight: 700; color: #63b3ed; }
.ref-date { font-size: 0.78rem; color: #718096; }
.loading { color: #718096; }

.controls { display: flex; flex-wrap: wrap; gap: 1.25rem; margin-bottom: 1.5rem; }
.ctrl-group { display: flex; align-items: center; gap: 0.4rem; }
.sort-label { font-size: 0.78rem; color: #718096; margin-right: 0.2rem; }

.chip {
  background: #2d3748; color: #a0aec0; border: none; border-radius: 6px;
  padding: 0.3rem 0.7rem; cursor: pointer; font-size: 0.8rem;
  transition: background 0.15s, color 0.15s;
}
.chip:hover { background: #374151; }
.chip.active { background: #63b3ed; color: #1a1f2e; font-weight: 600; }

.stock-table { width: 100%; border-collapse: collapse; }
.stock-table th {
  text-align: left; padding: 0.6rem 1rem; background: #1a1f2e; color: #718096;
  font-size: 0.78rem; font-weight: 600; border-bottom: 1px solid #2d3748;
}
.stock-table td { padding: 0.6rem 1rem; border-bottom: 1px solid #1e2535; font-size: 0.88rem; vertical-align: middle; }
.stock-table tr:hover td { background: #1a1f2e; }

.stock-cell { display: flex; align-items: center; gap: 0.5rem; text-decoration: none; color: inherit; }
.ticker { font-family: monospace; font-weight: 700; color: #90cdf4; }
.name { color: #e2e8f0; }
.stock-cell:hover .name { text-decoration: underline; }

.market-badge { font-size: 0.7rem; padding: 0.08rem 0.4rem; border-radius: 4px; font-weight: 600; }
.market-badge.tw { background: #22543d; color: #9ae6b4; }
.market-badge.us { background: #1a365d; color: #90cdf4; }
.market-badge.other, .market-badge.unknown { background: #2d3748; color: #a0aec0; }
.pos-flag { font-size: 0.7rem; color: #fc8181; }
.type-badge { font-size: 0.68rem; padding: 0.06rem 0.4rem; border-radius: 4px; background: #3a3052; color: #d6bcfa; }
.type-badge.etf { background: #1e3a3a; color: #9ae6cd; }

.score-cell { display: flex; align-items: center; gap: 0.5rem; }
.score-bar-track { width: 70px; height: 6px; background: #2d3748; border-radius: 3px; overflow: hidden; }
.score-bar { height: 100%; border-radius: 3px; }
.score-num { font-variant-numeric: tabular-nums; font-size: 0.82rem; font-weight: 600; min-width: 3rem; }

.dir { font-weight: 600; }
.fresh { font-size: 0.82rem; font-weight: 500; }
.ep-ref { font-size: 0.72rem; color: #718096; margin-left: 0.4rem; }

.num { text-align: center; font-variant-numeric: tabular-nums; }
.muted { color: #718096; }
.streak { color: #f6ad55; font-weight: 600; }
</style>
