<script setup lang="ts">
import { ref, onMounted, watch } from 'vue'
import { RouterLink } from 'vue-router'
import { loadSparklines, searchStockSignals } from '@/lib/useData'
import type { StockRow } from '@/types/stock'
import { HALF_LIFE_DAYS, DIRECTION_COLOR as dirColor } from '@/lib/signal'
import { pct, retColor } from '@/lib/format'
import { useQuerySync } from '@/lib/useQuerySync'
import { useStockFiltering } from '@/lib/useStockFiltering'
import Sparkline from '@/components/Sparkline.vue'
import FreshnessLabel from '@/components/FreshnessLabel.vue'
import ScoreLabel from '@/components/ScoreLabel.vue'
import InfoTip from '@/components/InfoTip.vue'
import BaseChip from '@/components/BaseChip.vue'
import BaseInput from '@/components/BaseInput.vue'

const rows = ref<StockRow[]>([])
const referenceDate = ref('')
const loading = ref(true)

const assetView = ref<'tradeable' | 'theme' | 'all'>('tradeable')
const market = ref<'ALL' | 'TW' | 'US'>('ALL')
const onlyPosition = ref(false)
const hideStale = ref(true)
const sortBy = ref<'score' | 'recent' | 'count' | 'first_mention'>('score')
const search = ref('')

// 篩選狀態同步到網址（重新整理／返回時保留）
useQuerySync({
  asset: { ref: assetView, default: 'tradeable' },
  market: { ref: market, default: 'ALL' },
  pos: { ref: onlyPosition, default: false },
  hideStale: { ref: hideStale, default: true },
  sort: { ref: sortBy, default: 'score' },
  q: { ref: search, default: '' },
})

const { filtered } = useStockFiltering(rows, {
  assetView,
  market,
  onlyPosition,
  hideStale,
  search,
  sortBy,
})

async function doSearch(q: string) {
  loading.value = true
  const res = await searchStockSignals(q)
  rows.value = res.stocks
  referenceDate.value = res.referenceDate
  await loadSparklines(rows.value)
  loading.value = false
}

let debounceTimer: ReturnType<typeof setTimeout> | null = null
watch(search, (newVal) => {
  if (debounceTimer) clearTimeout(debounceTimer)
  debounceTimer = setTimeout(() => {
    doSearch(newVal)
  }, 300)
})

onMounted(async () => {
  await doSearch(search.value)
})
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">個股追蹤</h1>
      <span v-if="referenceDate" class="ref-date"
        >時效基準：{{ referenceDate }}（資料集最新一集）</span
      >
    </div>

    <BaseInput v-model="search" type="search" placeholder="搜尋代號／名稱…" />

    <div class="controls">
      <div class="ctrl-group">
        <BaseChip
          v-for="a in ['tradeable', 'theme', 'all'] as const"
          :key="a"
          :active="assetView === a"
          @click="assetView = a"
        >
          {{ a === 'tradeable' ? '可交易（個股/ETF）' : a === 'theme' ? '題材/指數' : '全部' }}
        </BaseChip>
      </div>
      <div class="ctrl-group">
        <BaseChip
          v-for="f in ['ALL', 'TW', 'US'] as const"
          :key="f"
          :active="market === f"
          @click="market = f"
        >
          {{ f === 'ALL' ? '全部市場' : f }}
        </BaseChip>
      </div>
      <div class="ctrl-group">
        <BaseChip :active="onlyPosition" @click="onlyPosition = !onlyPosition">
          🔴 只看他有部位
        </BaseChip>
        <BaseChip :active="hideStale" @click="hideStale = !hideStale">
          隱藏過期（&gt;2月）
        </BaseChip>
      </div>
      <div class="ctrl-group sort">
        <span class="sort-label">排序</span>
        <BaseChip
          v-for="s in ['score', 'recent', 'count', 'first_mention'] as const"
          :key="s"
          :active="sortBy === s"
          @click="sortBy = s"
        >
          {{
            s === 'score'
              ? '訊號分數'
              : s === 'recent'
                ? '最近提及'
                : s === 'first_mention'
                  ? '首次提及'
                  : '提及次數'
          }}
        </BaseChip>
      </div>
    </div>

    <p v-if="loading" class="loading">載入中 …</p>
    <p v-else-if="filtered.length === 0" class="loading">沒有符合條件的個股</p>
    <div v-else class="table-wrap">
      <table class="app-table stock-table-min">
        <thead>
          <tr>
            <th>個股</th>
            <th>
              <span class="th-info">
                訊號分數
                <InfoTip label="訊號分數怎麼算的" :width="300">
                  把他每次提到這檔的「方向 × 信心」依時間加權後加總：
                  <ul class="info-list">
                    <li>方向權重：看多 <b>+1</b>、中性 <b>0</b>、看空 <b>−1</b></li>
                    <li>乘上當次<b>信心</b>（0–100%）</li>
                    <li>再乘<b>時間衰減</b>：半衰期 {{ HALF_LIFE_DAYS }} 天，越久遠權重越低</li>
                  </ul>
                  公式：<code>Σ 方向 × 信心 × 0.5^(距今天數 / {{ HALF_LIFE_DAYS }})</code><br />
                  分數<b>正</b>＝近期偏多、<b>負</b>＝近期偏空；數字越大代表近期看法越積極且一致。
                </InfoTip>
              </span>
            </th>
            <th>目前立場</th>
            <th>現價</th>
            <th>近30天</th>
            <th>最近提及</th>
            <th>首次看多至今</th>
            <th>連續看多</th>
            <th>次數</th>
            <th>首次提及</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="r in filtered" :key="r.id">
            <td>
              <RouterLink :to="`/stocks/${r.id}`" class="stock-cell">
                <span class="ticker">{{ r.ticker }}</span>
                <span class="name">{{ r.name_zh }}</span>
                <span :class="['market-badge', r.market.toLowerCase()]">{{ r.market }}</span>
                <span v-if="!['個股', 'ETF'].includes(r.asset_type)" class="type-badge">{{
                  r.asset_type
                }}</span>
                <span v-else-if="r.asset_type === 'ETF'" class="type-badge etf">ETF</span>
                <span v-if="r.signal.has_position_ever" class="pos-flag" title="謝孟恭曾自述有部位"
                  >🔴 有部位</span
                >
              </RouterLink>
            </td>
            <td>
              <ScoreLabel :score="r.signal.score" />
            </td>
            <td>
              <span class="dir" :style="{ color: dirColor[r.signal.latest_direction] }">
                {{ r.signal.latest_direction }}
              </span>
            </td>
            <td class="num price">{{ r.performance?.current_price ?? '—' }}</td>
            <td class="spark-cell"><Sparkline :values="r.recent" /></td>
            <td>
              <FreshnessLabel :days-ago="r.signal.latest_days_ago" />
            </td>
            <td class="num" :style="{ color: retColor(r.performance?.ret_since_first_bull) }">
              {{ pct(r.performance?.ret_since_first_bull) }}
            </td>
            <td class="num">
              <span v-if="r.signal.bull_streak >= 2" class="streak"
                >🔥 {{ r.signal.bull_streak }}</span
              >
              <span v-else class="muted">{{ r.signal.bull_streak }}</span>
            </td>
            <td class="num muted">{{ r.signal.mention_count }}</td>
            <td class="muted first-date">
              <FreshnessLabel :days-ago="r.signal.first_mention_days_ago" />
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}
.ctrl-group {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.sort-label {
  font-size: 0.78rem;
  color: #718096;
  margin-right: 0.2rem;
}

.stock-table-min {
  min-width: 920px;
}

.th-info {
  display: inline-flex;
  align-items: center;
  gap: 0.15rem;
}
.info-list {
  margin: 0.4rem 0;
  padding-left: 1.1rem;
}
.info-list li {
  margin-bottom: 0.2rem;
}

.stock-cell {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  text-decoration: none;
  color: inherit;
}
.ticker {
  font-family: monospace;
  font-weight: 700;
  color: #90cdf4;
}
.name {
  color: #e2e8f0;
}
.stock-cell:hover .name {
  text-decoration: underline;
}

.pos-flag {
  font-size: 0.7rem;
  color: #fc8181;
}
.type-badge {
  font-size: 0.68rem;
  padding: 0.06rem 0.4rem;
  border-radius: 4px;
  background: #3a3052;
  color: #d6bcfa;
}
.type-badge.etf {
  background: #1e3a3a;
  color: #9ae6cd;
}

.dir {
  font-weight: 600;
}
.fresh {
  font-size: 0.82rem;
  font-weight: 500;
}
.ep-ref {
  font-size: 0.72rem;
  color: #718096;
  margin-left: 0.4rem;
}

.price {
  text-align: right;
  color: #cbd5e0;
}
.spark-cell {
  width: 100px;
  padding-top: 0;
  padding-bottom: 0;
}
.muted {
  color: #718096;
}
.streak {
  color: #f6ad55;
  font-weight: 600;
}
</style>
