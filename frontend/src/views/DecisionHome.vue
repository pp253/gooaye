<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { supabase } from '@/lib/supabase'
import { loadStockSignals, type StockRow } from '@/lib/useData'
import { TRADEABLE_TYPES, type Episode } from '@/lib/types'
import { pct, retColor } from '@/lib/format'
import { useQuerySync } from '@/lib/useQuerySync'
import { DIRECTION_COLOR as dirColor } from '@/lib/signal'
import FreshnessLabel from '@/components/FreshnessLabel.vue'
import ScoreLabel from '@/components/ScoreLabel.vue'
import BaseChip from '@/components/BaseChip.vue'
import BaseCard from '@/components/BaseCard.vue'

const rows = ref<StockRow[]>([])
const referenceDate = ref('')
const loading = ref(true)

const latestEpisodes = ref<Episode[]>([])
async function loadLatestEpisodes() {
  const { data } = await supabase
    .from('episodes')
    .select('id, ep_no, title, source_url, published_at, summary, topics, created_at')
    .order('ep_no', { ascending: false })
    .limit(3)
  latestEpisodes.value = (data ?? []) as Episode[]
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
  if (assetView.value === 'tradeable')
    list = list.filter((r) => TRADEABLE_TYPES.includes(r.asset_type))
  else if (assetView.value === 'theme')
    list = list.filter((r) => !TRADEABLE_TYPES.includes(r.asset_type))
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
  loadLatestEpisodes()
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
      <span v-if="referenceDate" class="ref-date"
        >時效基準：{{ referenceDate }}（資料集最新一集）</span
      >
    </div>

    <section v-if="latestEpisodes.length" class="board latest-ep-board">
      <div class="latest-ep-head">
        <h2 class="board-title">📻 最新集數</h2>
        <RouterLink to="/episodes" class="more-link">看全部集數 →</RouterLink>
      </div>
      <div class="card-row">
        <BaseCard
          v-for="ep in latestEpisodes"
          :key="ep.id"
          :to="`/episodes/${ep.ep_no}`"
          class="ep-card"
        >
          <div class="ep-header">
            <span class="ep-no">EP{{ ep.ep_no }}</span>
            <span class="ep-title">{{ ep.title }}</span>
          </div>
          <span v-if="ep.published_at" class="ep-date">{{ ep.published_at }}</span>
          <ul class="ep-summary">
            <li v-for="(s, i) in ep.summary.slice(0, 2)" :key="i">{{ s }}</li>
          </ul>
        </BaseCard>
      </div>
    </section>

    <p v-if="loading" class="loading">載入中 …</p>

    <template v-else>
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
        <div class="ctrl-group ctrl-view">
          <BaseChip :active="viewMode === 'card'" title="卡片" @click="viewMode = 'card'"
            >⊞</BaseChip
          >
          <BaseChip :active="viewMode === 'table'" title="列表" @click="viewMode = 'table'"
            >☰</BaseChip
          >
        </div>
      </div>

      <!-- ══ 有部位 ══ -->
      <section class="board">
        <h2 class="board-title">🔴 謝孟恭有部位</h2>
        <p class="board-desc">他自己的錢也在裡面——最值得參考的訊號</p>
        <!-- card -->
        <div v-if="viewMode === 'card'" class="card-row">
          <BaseCard v-for="r in hasPosition" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-dir" :style="{ color: dirColor[r.signal.latest_direction] }">{{
                r.signal.latest_direction
              }}</span>
              <span class="sc-score">分數 {{ r.signal.score.toFixed(2) }}</span>
            </div>
            <div class="sc-fresh"><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span
                v-if="r.performance.ret_since_last_bull != null"
                :style="{ color: retColor(r.performance.ret_since_last_bull) }"
              >
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </BaseCard>
          <p v-if="hasPosition.length === 0" class="empty">近期無此類訊號</p>
        </div>
        <!-- table -->
        <template v-else>
          <p v-if="hasPosition.length === 0" class="empty">近期無此類訊號</p>
          <div v-else class="table-wrap">
            <table class="app-table">
              <thead>
                <tr>
                  <th>個股</th>
                  <th>方向</th>
                  <th>分數</th>
                  <th>現價</th>
                  <th>最近看多</th>
                  <th>時效</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in hasPosition" :key="r.id">
                  <td>
                    <RouterLink :to="`/stocks/${r.id}`" class="tl-link"
                      ><b class="tl-ticker">{{ r.ticker }}</b> {{ r.name_zh }}</RouterLink
                    >
                  </td>
                  <td>
                    <span :style="{ color: dirColor[r.signal.latest_direction] }">{{
                      r.signal.latest_direction
                    }}</span>
                  </td>
                  <td><ScoreLabel :score="r.signal.score" /></td>
                  <td class="num">{{ r.performance?.current_price ?? '—' }}</td>
                  <td class="num" :style="{ color: retColor(r.performance?.ret_since_last_bull) }">
                    {{ pct(r.performance?.ret_since_last_bull) }}
                  </td>
                  <td><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </section>

      <!-- ══ 高分看多 ══ -->
      <section class="board">
        <h2 class="board-title">🟢 高分看多</h2>
        <p class="board-desc">近期語氣積極、且經時間加權後分數最高</p>
        <!-- card -->
        <div v-if="viewMode === 'card'" class="card-row">
          <BaseCard v-for="r in topBull" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
              <span v-if="r.signal.bull_streak >= 2" class="sc-streak"
                >🔥{{ r.signal.bull_streak }}</span
              >
            </div>
            <div class="sc-mid">
              <span class="sc-score-big" :style="{ color: '#68d391' }"
                >+{{ r.signal.score.toFixed(2) }}</span
              >
            </div>
            <div class="sc-fresh"><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span
                v-if="r.performance.ret_since_last_bull != null"
                :style="{ color: retColor(r.performance.ret_since_last_bull) }"
              >
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </BaseCard>
          <p v-if="topBull.length === 0" class="empty">近期無此類訊號</p>
        </div>
        <!-- table -->
        <template v-else>
          <p v-if="topBull.length === 0" class="empty">近期無此類訊號</p>
          <div v-else class="table-wrap">
            <table class="app-table">
              <thead>
                <tr>
                  <th>個股</th>
                  <th>連多</th>
                  <th>分數</th>
                  <th>現價</th>
                  <th>最近看多</th>
                  <th>時效</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in topBull" :key="r.id">
                  <td>
                    <RouterLink :to="`/stocks/${r.id}`" class="tl-link"
                      ><b class="tl-ticker">{{ r.ticker }}</b> {{ r.name_zh }}</RouterLink
                    >
                  </td>
                  <td class="num">
                    {{
                      r.signal.bull_streak >= 2 ? `🔥${r.signal.bull_streak}` : r.signal.bull_streak
                    }}
                  </td>
                  <td><ScoreLabel :score="r.signal.score" /></td>
                  <td class="num">{{ r.performance?.current_price ?? '—' }}</td>
                  <td class="num" :style="{ color: retColor(r.performance?.ret_since_last_bull) }">
                    {{ pct(r.performance?.ret_since_last_bull) }}
                  </td>
                  <td><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </section>

      <!-- ══ 近期首次提及 ══ -->
      <section class="board">
        <h2 class="board-title">🆕 近期首次提及</h2>
        <p class="board-desc">
          近一個月內第一次被謝孟恭談到的標的（{{ newlyMentioned.length }}
          檔）——新進場的標的，短期注意流動性相對低
        </p>
        <!-- card -->
        <div v-if="viewMode === 'card'" class="card-row">
          <BaseCard
            v-for="r in newlyMentioned"
            :key="r.id"
            :to="`/stocks/${r.id}`"
            class="sig-card new-card"
          >
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-dir" :style="{ color: dirColor[r.signal.latest_direction] }">{{
                r.signal.latest_direction
              }}</span>
            </div>
            <div class="sc-fresh" style="color: #9ae6b4">
              🆕 首次：{{ r.signal.first_mention_date }}
            </div>
            <div class="sc-fresh"><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></div>
          </BaseCard>
          <p v-if="newlyMentioned.length === 0" class="empty">近一個月無新首次提及的標的</p>
        </div>
        <!-- table -->
        <template v-else>
          <p v-if="newlyMentioned.length === 0" class="empty">近一個月無新首次提及的標的</p>
          <div v-else class="table-wrap">
            <table class="app-table">
              <thead>
                <tr>
                  <th>個股</th>
                  <th>方向</th>
                  <th>首次提及</th>
                  <th>最近提及</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="r in newlyMentioned" :key="r.id">
                  <td>
                    <RouterLink :to="`/stocks/${r.id}`" class="tl-link"
                      ><b class="tl-ticker">{{ r.ticker }}</b> {{ r.name_zh }}</RouterLink
                    >
                  </td>
                  <td>
                    <span :style="{ color: dirColor[r.signal.latest_direction] }">{{
                      r.signal.latest_direction
                    }}</span>
                  </td>
                  <td style="color: #9ae6b4">
                    <FreshnessLabel :days-ago="r.signal.first_mention_days_ago" />
                  </td>
                  <td><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></td>
                </tr>
              </tbody>
            </table>
          </div>
        </template>
      </section>

      <!-- ══ 最新提及 ══ -->
      <section class="board">
        <h2 class="board-title">🆕 最新提及</h2>
        <p class="board-desc">近一個月內被談到的標的（{{ recent.length }} 檔）</p>
        <!-- card -->
        <div v-if="viewMode === 'card'" class="card-row">
          <BaseCard v-for="r in recent" :key="r.id" :to="`/stocks/${r.id}`" class="sig-card">
            <div class="sc-top">
              <span class="sc-ticker">{{ r.ticker }}</span>
              <span class="sc-name">{{ r.name_zh }}</span>
            </div>
            <div class="sc-mid">
              <span class="sc-dir" :style="{ color: dirColor[r.signal.latest_direction] }">{{
                r.signal.latest_direction
              }}</span>
            </div>
            <div class="sc-fresh"><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></div>
            <div v-if="r.performance?.current_price" class="sc-price">
              {{ r.performance.current_price }}
              <span
                v-if="r.performance.ret_since_last_bull != null"
                :style="{ color: retColor(r.performance.ret_since_last_bull) }"
              >
                · 最近看多 {{ pct(r.performance.ret_since_last_bull) }}
              </span>
            </div>
          </BaseCard>
        </div>
        <!-- table -->
        <div v-else class="table-wrap">
          <table class="app-table">
            <thead>
              <tr>
                <th>個股</th>
                <th>方向</th>
                <th>現價</th>
                <th>最近看多</th>
                <th>時效</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="r in recent" :key="r.id">
                <td>
                  <RouterLink :to="`/stocks/${r.id}`" class="tl-link"
                    ><b class="tl-ticker">{{ r.ticker }}</b> {{ r.name_zh }}</RouterLink
                  >
                </td>
                <td>
                  <span :style="{ color: dirColor[r.signal.latest_direction] }">{{
                    r.signal.latest_direction
                  }}</span>
                </td>
                <td class="num">{{ r.performance?.current_price ?? '—' }}</td>
                <td class="num" :style="{ color: retColor(r.performance?.ret_since_last_bull) }">
                  {{ pct(r.performance?.ret_since_last_bull) }}
                </td>
                <td><FreshnessLabel :days-ago="r.signal.latest_days_ago" /></td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </template>
  </div>
</template>

<style scoped>
.controls {
  display: flex;
  flex-wrap: wrap;
  gap: 1.25rem;
  margin-bottom: 1.75rem;
}
.ctrl-group {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}
.ctrl-view {
  margin-left: auto;
}

.board {
  margin-bottom: 2.25rem;
}
.board-title {
  font-size: 1.05rem;
  font-weight: 700;
  margin-bottom: 0.2rem;
}
.board-desc {
  font-size: 0.8rem;
  color: #718096;
  margin-bottom: 0.9rem;
}

.card-row {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: 0.75rem;
}

.latest-ep-board .card-row {
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
}
.latest-ep-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.9rem;
}
.latest-ep-head .board-title {
  margin-bottom: 0;
}
.more-link {
  font-size: 0.8rem;
  color: #63b3ed;
  text-decoration: none;
  white-space: nowrap;
}
.more-link:hover {
  text-decoration: underline;
}

.ep-card {
  padding: 0.8rem 0.9rem;
  gap: 0.4rem;
}
.ep-header {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}
.ep-no {
  font-weight: 700;
  color: #63b3ed;
  font-size: 0.92rem;
  white-space: nowrap;
}
.ep-title {
  color: #a0aec0;
  font-size: 0.85rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.ep-date {
  color: #718096;
  font-size: 0.74rem;
}
.ep-summary {
  padding-left: 1rem;
  color: #cbd5e0;
  font-size: 0.8rem;
  line-height: 1.55;
}
.ep-summary li {
  margin-bottom: 0.15rem;
}

.sig-card {
  padding: 0.8rem 0.9rem;
  gap: 0.45rem;
}

.new-card {
  border-color: #2d4a3e;
}
.new-card:hover {
  border-color: #9ae6b4;
  box-shadow: 0 10px 24px -12px rgba(154, 230, 180, 0.35);
}

.tl-link {
  text-decoration: none;
  color: inherit;
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
}
.tl-link:hover .tl-ticker {
  text-decoration: underline;
}
.tl-ticker {
  font-family: monospace;
  font-weight: 700;
  color: #90cdf4;
}

.sc-top {
  display: flex;
  align-items: baseline;
  gap: 0.4rem;
}
.sc-ticker {
  font-family: monospace;
  font-weight: 700;
  color: #90cdf4;
  font-size: 0.95rem;
}
.sc-name {
  color: #cbd5e0;
  font-size: 0.82rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.sc-streak {
  color: #f6ad55;
  font-size: 0.78rem;
  margin-left: auto;
}

.sc-mid {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
}
.sc-dir {
  font-weight: 700;
  font-size: 1rem;
}
.sc-score {
  font-size: 0.78rem;
  color: #718096;
}
.sc-score-big {
  font-size: 1.15rem;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}

.sc-fresh {
  font-size: 0.76rem;
  font-weight: 500;
}
.sc-price {
  font-size: 0.76rem;
  color: #cbd5e0;
  font-variant-numeric: tabular-nums;
}
</style>
