<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { loadStockSignals, type StockRow } from '@/lib/useData'
import { FRESHNESS_META, relativeTime } from '@/lib/signal'
import { pct, retColor } from '@/lib/format'
import { useQuerySync } from '@/lib/useQuerySync'
import TrajectoryChart from '@/components/TrajectoryChart.vue'
import PriceChart from '@/components/PriceChart.vue'

const props = defineProps<{ id: string }>()

const row = ref<StockRow | null>(null)
const referenceDate = ref('')
const loading = ref(true)

// 共用時間範圍：同步控制下方所有圖表
const RANGES = [
  { key: 'ALL', label: '全部', days: null },
  { key: '1Y', label: '1年', days: 365 },
  { key: '6M', label: '半年', days: 182 },
  { key: '1Q', label: '1季', days: 91 },
  { key: '1M', label: '1月', days: 30 },
  { key: '1W', label: '1週', days: 7 },
] as const
const range = ref<string>('ALL')
useQuerySync({ range: { ref: range, default: 'ALL' } })
const fromDate = computed<string | null>(() => {
  const r = RANGES.find((x) => x.key === range.value)
  if (!r || r.days == null) return null
  return new Date(Date.now() - r.days * 86_400_000).toISOString().slice(0, 10)
})

// 兩張圖共用的 x 時間軸範圍，確保時間刻度對齊
const ALL_LOOKBACK_DAYS = 430
const axisEnd = computed(() => new Date().toISOString().slice(0, 10))
const axisStart = computed(
  () =>
    fromDate.value ??
    new Date(Date.now() - ALL_LOOKBACK_DAYS * 86_400_000).toISOString().slice(0, 10),
)

const dirColor: Record<string, string> = {
  看多: '#68d391',
  看空: '#fc8181',
  中性: '#90cdf4',
}

// 時間軸：新→舊
const timeline = computed(() =>
  row.value
    ? [...row.value.mentions].sort(
        (a, b) => Date.parse(b.published_at) - Date.parse(a.published_at),
      )
    : [],
)
const latest = computed(() => timeline.value[0] ?? null)

onMounted(async () => {
  const res = await loadStockSignals()
  referenceDate.value = res.referenceDate
  row.value = res.stocks.find((s) => s.id === Number(props.id)) ?? null
  loading.value = false
})
</script>

<template>
  <div>
    <p v-if="loading" class="loading">載入中 …</p>
    <template v-else-if="row">
      <div class="stock-header">
        <span :class="['market-badge', row.market.toLowerCase()]">{{ row.market }}</span>
        <h1 class="stock-name">{{ row.name_zh }}</h1>
        <span class="stock-ticker">{{ row.ticker }}</span>
      </div>

      <!-- 立場 + 現價／績效 合併卡片 -->
      <div v-if="latest" class="summary-card" :style="{ borderColor: dirColor[latest.direction] }">
        <div class="summary-grid">
          <!-- 目前立場 -->
          <div class="sc-block">
            <div class="sc-label">目前立場（最新一次提到）</div>
            <div class="sc-main">
              <span class="stance-dir" :style="{ color: dirColor[latest.direction] }">{{ latest.direction }}</span>
              <span class="stance-conf">信心 {{ Math.round(latest.confidence * 100) }}%</span>
              <span v-if="latest.has_position" class="stance-pos">🔴 他有部位</span>
            </div>
            <div class="sc-fresh" :style="{ color: FRESHNESS_META[latest.freshness].color }">
              {{ FRESHNESS_META[latest.freshness].dot }} {{ relativeTime(latest.days_ago) }}
              · EP{{ latest.episodes?.ep_no }}（{{ latest.published_at }}）
            </div>
          </div>

          <!-- 現價／跟單績效 -->
          <template v-if="row.performance?.current_price">
            <div class="sc-divider"></div>
            <div class="perf-row">
              <div class="perf-item">
                <span class="perf-label">現價</span>
                <span class="perf-val">{{ row.performance.current_price }}</span>
              </div>
              <div class="perf-item" v-if="row.performance.ret_since_first_bull != null">
                <span class="perf-label">首次看多至今</span>
                <span class="perf-val" :style="{ color: retColor(row.performance.ret_since_first_bull) }">
                  {{ pct(row.performance.ret_since_first_bull) }}
                </span>
                <span class="perf-sub">（{{ row.performance.first_bull_date }}）</span>
              </div>
              <div class="perf-item" v-if="row.performance.ret_since_last_bull != null">
                <span class="perf-label">最近看多至今</span>
                <span class="perf-val" :style="{ color: retColor(row.performance.ret_since_last_bull) }">
                  {{ pct(row.performance.ret_since_last_bull) }}
                </span>
                <span class="perf-sub">（{{ row.performance.last_bull_date }}）</span>
              </div>
            </div>
          </template>
        </div>
        <div v-if="latest.freshness === 'stale'" class="stance-warn">
          ⚠️ 這是 2 個月前以上的觀點，可能已不具時效，僅供參考
        </div>
      </div>

      <!-- 共用時間範圍選擇器（同步所有圖表） -->
      <div class="range-bar">
        <span class="range-label">時間範圍</span>
        <button v-for="r in RANGES" :key="r.key"
          :class="['range-chip', { active: range === r.key }]" @click="range = r.key">
          {{ r.label }}
        </button>
      </div>

      <!-- 股價走勢 + 提及點 -->
      <section class="section">
        <h2 class="section-title">股價走勢（點＝他提到的時機，顏色＝當時方向）</h2>
        <PriceChart :stock-id="row.id" :mentions="row.mentions" :from-date="fromDate"
          :axis-start="axisStart" :axis-end="axisEnd" />
      </section>

      <!-- 演變圖 -->
      <section class="section">
        <h2 class="section-title">觀點演變（點越大＝信心越高，金圈＝他有部位）</h2>
        <TrajectoryChart :mentions="row.mentions" :reference-date="referenceDate" :from-date="fromDate"
          :axis-start="axisStart" :axis-end="axisEnd" />
      </section>

      <!-- 時間軸 -->
      <section class="section">
        <h2 class="section-title">提及紀錄（{{ timeline.length }} 次，新到舊）</h2>
        <div class="timeline">
          <div v-for="m in timeline" :key="m.id"
            :class="['timeline-item', { stale: m.freshness === 'stale' }]">
            <div class="tl-head">
              <span class="fresh-dot">{{ FRESHNESS_META[m.freshness].dot }}</span>
              <RouterLink :to="`/episodes/${m.episodes?.ep_no}`" class="ep-link">EP{{ m.episodes?.ep_no }}</RouterLink>
              <span class="tl-date">{{ m.published_at }} · {{ relativeTime(m.days_ago) }}</span>
              <span class="m-dir" :style="{ color: dirColor[m.direction] }">{{ m.direction }}</span>
              <span class="m-conf">{{ Math.round(m.confidence * 100) }}%</span>
              <span v-if="m.has_position" class="m-pos">有部位</span>
            </div>
            <blockquote class="m-quote">「{{ m.quote }}」</blockquote>
            <p class="m-note" v-if="m.note">{{ m.note }}</p>
          </div>
        </div>
      </section>
    </template>
    <p v-else class="loading">找不到此個股</p>
  </div>
</template>

<style scoped>
.loading { color: #718096; }

.stock-header { display: flex; align-items: baseline; gap: 0.8rem; margin-bottom: 1.25rem; }
.stock-name { font-size: 1.4rem; font-weight: 700; }
.stock-ticker { font-family: monospace; font-size: 1.1rem; color: #90cdf4; font-weight: 600; }

.market-badge { font-size: 0.75rem; padding: 0.15rem 0.5rem; border-radius: 4px; font-weight: 600; }
.market-badge.tw { background: #22543d; color: #9ae6b4; }
.market-badge.us { background: #1a365d; color: #90cdf4; }
.market-badge.other, .market-badge.unknown { background: #2d3748; color: #a0aec0; }

.summary-card {
  background: #1a1f2e; border: 1px solid; border-left-width: 4px;
  border-radius: 8px; padding: 1rem 1.25rem; margin-bottom: 1.75rem;
}
.summary-grid { display: flex; align-items: center; flex-wrap: wrap; gap: 1rem 1.75rem; }
.sc-block { display: flex; flex-direction: column; gap: 0.4rem; }
.sc-label { font-size: 0.78rem; color: #718096; }
.sc-main { display: flex; align-items: center; flex-wrap: wrap; gap: 0.9rem; }
.stance-dir { font-size: 1.5rem; font-weight: 700; }
.stance-conf { font-size: 0.9rem; color: #a0aec0; }
.stance-pos { font-size: 0.82rem; color: #fc8181; font-weight: 600; }
.sc-fresh { font-size: 0.82rem; font-weight: 500; }
.sc-divider { width: 1px; align-self: stretch; background: #2d3748; }
.stance-warn { margin-top: 0.75rem; font-size: 0.82rem; color: #f6ad55; background: #2d2410; padding: 0.5rem 0.75rem; border-radius: 6px; }

.perf-row { display: flex; flex-wrap: wrap; gap: 1.75rem; }
.perf-item { display: flex; flex-direction: column; gap: 0.15rem; }
.perf-label { font-size: 0.72rem; color: #718096; }
.perf-val { font-size: 1.15rem; font-weight: 700; font-variant-numeric: tabular-nums; }
.perf-sub { font-size: 0.7rem; color: #4a5568; }

.range-bar { display: flex; align-items: center; gap: 0.4rem; margin-bottom: 1.25rem; }
.range-label { font-size: 0.78rem; color: #718096; margin-right: 0.3rem; }
.range-chip {
  background: #2d3748; color: #a0aec0; border: none; border-radius: 6px;
  padding: 0.28rem 0.7rem; cursor: pointer; font-size: 0.8rem;
  transition: background 0.15s, color 0.15s;
}
.range-chip:hover { background: #374151; }
.range-chip.active { background: #63b3ed; color: #1a1f2e; font-weight: 600; }

.section { margin-bottom: 2rem; }
.section-title { font-size: 0.95rem; font-weight: 600; color: #a0aec0; margin-bottom: 0.75rem; border-bottom: 1px solid #2d3748; padding-bottom: 0.4rem; }

.timeline { display: flex; flex-direction: column; gap: 0.75rem; }
.timeline-item { background: #1a1f2e; border: 1px solid #2d3748; border-radius: 8px; padding: 0.8rem 1rem; }
.timeline-item.stale { opacity: 0.6; }

.tl-head { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.45rem; }
.fresh-dot { font-size: 0.7rem; }
.ep-link { color: #63b3ed; text-decoration: none; font-weight: 700; font-size: 0.9rem; }
.ep-link:hover { text-decoration: underline; }
.tl-date { font-size: 0.78rem; color: #718096; }
.m-dir { font-weight: 600; font-size: 0.85rem; margin-left: auto; }
.m-conf { font-size: 0.78rem; color: #718096; }
.m-pos { background: #2a4365; color: #90cdf4; font-size: 0.7rem; padding: 0.08rem 0.4rem; border-radius: 4px; }

.m-quote { border-left: 3px solid #4a5568; padding-left: 0.75rem; color: #a0aec0; font-size: 0.85rem; line-height: 1.6; font-style: italic; margin-bottom: 0.4rem; }
.m-note { font-size: 0.8rem; color: #718096; }
</style>
