<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { supabase } from '@/lib/supabase'
import { pct, rate, retColor } from '@/lib/format'
import { loadStockSignals } from '@/lib/useData'
import KpiCard from '@/components/KpiCard.vue'
import MultiEquityChart from '@/components/MultiEquityChart.vue'
import HitRateChart from '@/components/HitRateChart.vue'
import RecommendationList from '@/components/RecommendationList.vue'
import type { Rec } from '@/components/RecommendationList.vue'
import BaseChip from '@/components/BaseChip.vue'
import BaseInput from '@/components/BaseInput.vue'

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
interface DailyBlock { dates: string[]; nav: number[]; bm_nav: number[] | null }
interface Strategy {
  id: string; label: string; scopes: Scope[]
  trades?: TradeRow[]
  /** 後端日頻 NAV（每市場一條），前端切片重設基準後算 Sharpe/MDD/CAGR */
  daily?: Record<string, DailyBlock>
  /** 截至資料日仍開倉中的標的（目前建議買進/續抱） */
  recommendations?: Rec[]
  /** 邊際真實性檢驗：嚴格對標 + 因子(市場/半導體)beta 拆解（美股、全期） */
  factor?: {
    vs: Record<string, { n: number; avg_alpha: number; beat_rate: number } | null>
    decomp: { n: number; alpha_ann: number; beta_mkt: number; beta_semis: number; r2: number | null } | null
  }
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

// 全局篩選
const selectedMarket = ref<'ALL' | 'TW' | 'US'>('ALL')

// Hero 指標卡顯示的「主要策略」（預設指向推薦策略 S4，可切換）
const featuredId = ref('S4')
// 建議清單：只看「可買進（訊號≤14天）」
const recFreshOnly = ref(false)

// Ticker 尋找 Stock ID 用於超連結
const tickerToIdMap = ref<Record<string, number>>({})

// 交易清單搜尋與篩選 (每個策略分開，載入後依實際策略 id 初始化)
const searchQuery = ref<Record<string, string>>({})
const tradeResultFilter = ref<Record<string, 'ALL' | 'WIN' | 'LOSS'>>({})

const scopeLabel: Record<string, string> = { ALL: '全部', TW: '台股', US: '美股' }

onMounted(async () => {
  // 1. 載入回測主資料
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

    // 依實際策略 id 初始化各策略的搜尋/篩選狀態；確保 featured 指向存在的策略
    for (const st of strategies.value) {
      searchQuery.value[st.id] = ''
      tradeResultFilter.value[st.id] = 'ALL'
    }
    if (!strategies.value.some(s => s.id === featuredId.value)) {
      featuredId.value = strategies.value[0]?.id ?? 'S1'
    }

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

  // 2. 載入個股對照表以建立連結
  try {
    const { stocks } = await loadStockSignals()
    const map: Record<string, number> = {}
    for (const s of stocks) {
      map[s.ticker] = s.id
    }
    tickerToIdMap.value = map
  } catch (e) {
    console.error('Failed to load stock list mapping', e)
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

// 從後端日頻 NAV 取出選定市場的序列，依篩選區間切片並重設基準為 1.0。
// 回傳策略曲線與基準曲線（皆 { date, value }[]），供畫圖與指標計算共用。
function slicedDaily(st: Strategy, scope: string) {
  const d = st.daily?.[scope]
  if (!d || d.dates.length < 2) return { curve: [], bmCurve: [] }
  const idx: number[] = []
  for (let i = 0; i < d.dates.length; i++) {
    if (d.dates[i] >= filterFrom.value && d.dates[i] <= filterTo.value) idx.push(i)
  }
  if (idx.length < 2) return { curve: [], bmCurve: [] }
  const base = d.nav[idx[0]] || 1
  const bmBase = d.bm_nav ? d.bm_nav[idx[0]] || 1 : null
  const curve = idx.map(i => ({ date: d.dates[i], value: +(d.nav[i] / base).toFixed(4) }))
  const bmCurve =
    d.bm_nav && bmBase
      ? idx.map(i => ({ date: d.dates[i], value: +(d.bm_nav![i] / bmBase).toFixed(4) }))
      : []
  return { curve, bmCurve }
}

// 由日頻淨值序列計算最大回撤 (MDD)：含持倉期間浮動回撤，符合真實風險。
function computeMdd(curve: { date: string; value: number }[]) {
  let peak = -Infinity
  let mdd = 0.0
  for (const p of curve) {
    if (p.value > peak) peak = p.value
    const dd = p.value / peak - 1.0
    if (dd < mdd) mdd = dd
  }
  return mdd
}

// 由淨值序列計算年化 Sharpe：以實際取樣頻率年化（自動適應日/週頻，含現金空檔，投組層級）。
function computeSharpe(curve: { date: string; value: number }[]) {
  if (curve.length < 3) return null
  const r: number[] = []
  for (let i = 1; i < curve.length; i++) {
    if (curve[i - 1].value > 0) r.push(curve[i].value / curve[i - 1].value - 1)
  }
  if (r.length < 2) return null
  const mean = r.reduce((a, b) => a + b, 0) / r.length
  const variance = r.reduce((a, b) => a + Math.pow(b - mean, 2), 0) / (r.length - 1)
  const sd = Math.sqrt(variance)
  if (sd === 0) return null
  const days = (Date.parse(curve[curve.length - 1].date) - Date.parse(curve[0].date)) / 86400000
  const years = days / 365.25
  const periodsPerYear = years > 0 ? r.length / years : 252
  return (mean / sd) * Math.sqrt(periodsPerYear)
}

// 由日頻淨值序列計算年化複合報酬 (CAGR)。
function computeCagr(curve: { date: string; value: number }[]) {
  if (curve.length < 2) return null
  const days = (Date.parse(curve[curve.length - 1].date) - Date.parse(curve[0].date)) / 86400000
  if (days <= 0 || curve[0].value <= 0) return null
  const years = days / 365.25
  return Math.pow(curve[curve.length - 1].value / curve[0].value, 1 / years) - 1
}

// 計算連續勝敗
function computeStreaks(trades: TradeRow[]) {
  const sorted = [...trades].sort((a, b) => a.exit_date.localeCompare(b.exit_date))
  let winStreak = 0
  let loseStreak = 0
  let maxWin = 0
  let maxLose = 0
  for (const t of sorted) {
    if (t.ret > 0) {
      winStreak++
      loseStreak = 0
      if (winStreak > maxWin) maxWin = winStreak
    } else if (t.ret < 0) {
      loseStreak++
      winStreak = 0
      if (loseStreak > maxLose) maxLose = loseStreak
    } else {
      winStreak = 0
      loseStreak = 0
    }
  }
  return { maxWin, maxLose }
}

// 產出分年統計
function getYearlyStats(trades: TradeRow[]) {
  const byYear: Record<string, TradeRow[]> = {}
  for (const t of trades) {
    if (!t.exit_date) continue
    const year = t.exit_date.split('-')[0]
    if (!byYear[year]) byYear[year] = []
    byYear[year].push(t)
  }
  return Object.keys(byYear).sort().map(year => ({
    year,
    ...aggregate(byYear[year], 'ALL')
  }))
}

const filteredStrategies = computed(() =>
  strategies.value.map(st => {
    // 依全局日期與市場篩選
    const trades = (st.trades ?? []).filter(
      t => t.ep_date >= filterFrom.value && 
           t.ep_date <= filterTo.value &&
           (selectedMarket.value === 'ALL' || t.market === selectedMarket.value),
    )
    const streaks = computeStreaks(trades)
    const { curve, bmCurve } = slicedDaily(st, selectedMarket.value)
    return {
      ...st,
      _trades: trades,
      _scopes: ['ALL', 'TW', 'US'].map(sc => aggregate(trades, sc)),
      _curve: curve,
      _bmCurve: bmCurve,
      _mdd: computeMdd(curve),
      _sharpe: computeSharpe(curve),
      _cagr: computeCagr(curve),
      _maxWin: streaks.maxWin,
      _maxLose: streaks.maxLose,
      _yearly: getYearlyStats(trades),
    }
  }),
)

// 主要策略數據（給 Hero 指標卡使用，可由使用者切換）
const featured = computed(
  () => filteredStrategies.value.find(s => s.id === featuredId.value) ?? filteredStrategies.value[0],
)
const featScopeAll = computed(() => featured.value?._scopes.find(sc => sc.scope === 'ALL'))
const featScopeTw = computed(() => featured.value?._scopes.find(sc => sc.scope === 'TW'))
const featScopeUs = computed(() => featured.value?._scopes.find(sc => sc.scope === 'US'))

// 主要策略「目前建議」：受市場篩選與「只看可買進」開關影響（不受日期區間影響，因為是當下持倉）
const featuredRecs = computed(() => {
  const recs = featured.value?.recommendations ?? []
  return recs.filter(
    r =>
      (selectedMarket.value === 'ALL' || r.market === selectedMarket.value) &&
      (!recFreshOnly.value || r.fresh),
  )
})
const featuredBuyCount = computed(() => featuredRecs.value.filter(r => r.fresh).length)
const featuredHoldCount = computed(() => featuredRecs.value.filter(r => !r.fresh).length)

// 主要策略的邊際真實性檢驗（美股、全期，不隨日期/市場篩選變動）
const featuredFactor = computed(() => featured.value?.factor)
// 一句話判讀：殘餘真 α 是否站得住、是否主要靠半導體 beta
const factorVerdict = computed(() => {
  const d = featuredFactor.value?.decomp
  if (!d) return ''
  const bm = d.beta_mkt ?? 0
  const bs = d.beta_semis ?? 0
  const aSoxx = featuredFactor.value?.vs?.SOXX?.avg_alpha ?? 0
  const beatSoxx = featuredFactor.value?.vs?.SOXX?.beat_rate ?? 0
  // 依實際拆解判斷主導 beta 來源（而非假設半導體）
  const betaSrc = bs >= 0.4 && bs >= bm ? '半導體' : bm >= 0.6 ? '大盤' : '市場／產業'
  const r2txt = d.r2 != null ? `、R² ${d.r2.toFixed(2)}` : ''
  const exposure = `報酬主要由${betaSrc} beta 解釋（β大盤 ${bm.toFixed(2)}、β費半 ${bs.toFixed(2)}${r2txt}）`
  const residual =
    aSoxx > 0 && beatSoxx >= 0.55
      ? `剝掉這些 beta 後對最嚴的費半仍有正殘餘（+${(aSoxx * 100).toFixed(1)}%／贏面 ${(beatSoxx * 100).toFixed(0)}%），邊際偏真但幅度有限`
      : aSoxx > 0
        ? '殘餘超額為正但贏面僅約五成，邊際薄弱、近雜訊'
        : '剝掉 beta 後對同產業沒有正超額，難認定為選股能力'
  return `${exposure}。${residual}。`
})

// 各策略配色（線色與 legend 圖示共用，確保一致）
const STRAT_COLORS: Record<string, string> = {
  S1: '#63b3ed', S2: '#f6ad55', S3: '#68d391',
  S4: '#b794f4', S5: '#f687b3', S6: '#4fd1c5',
}

const chartSeries = computed(() => {
  const colors = STRAT_COLORS
  const seriesList = filteredStrategies.value.map(st => ({
    id: st.id,
    label: `${st.id} ${st.label}`,
    color: colors[st.id] || '#cbd5e0',
    data: st._curve,
  }))
  
  const s1 = filteredStrategies.value[0]
  if (s1 && s1._bmCurve?.length) {
    seriesList.push({
      id: 'BM',
      label: `基準線 (${selectedMarket.value === 'TW' ? '0050' : selectedMarket.value === 'US' ? 'SPY' : '基準大盤組合'})`,
      color: '#4a5568',
      data: s1._bmCurve,
    })
  }
  return seriesList
})

// 每個策略展開交易清單
const expanded = ref<Record<string, boolean>>({})
function toggle(id: string) { expanded.value[id] = !expanded.value[id] }

function topBottomBy(trades: TradeRow[], key: 'ret' | 'alpha', n = 5) {
  const valid = trades.filter(t => t[key] !== null && t[key] !== undefined)
  const sorted = [...valid].sort((a, b) => (b[key] as number) - (a[key] as number))
  return { top: sorted.slice(0, n), bottom: sorted.slice(-n).reverse() }
}

function getDaysBetween(from: string, to: string): number {
  if (!from || !to) return 0
  const f = Date.parse(from)
  const t = Date.parse(to)
  return Math.round((t - f) / (1000 * 60 * 60 * 24))
}

function getFilteredTrades(stId: string, trades: TradeRow[]) {
  const q = searchQuery.value[stId]?.trim().toLowerCase()
  const resF = tradeResultFilter.value[stId]
  
  return trades.filter(t => {
    if (q) {
      const matchTicker = t.ticker.toLowerCase().includes(q)
      const matchName = t.name_zh.toLowerCase().includes(q)
      if (!matchTicker && !matchName) return false
    }
    if (resF === 'WIN' && t.ret <= 0) return false
    if (resF === 'LOSS' && t.ret > 0) return false
    return true
  })
}
</script>

<template>
  <div>
    <div class="page-header">
      <h1 class="page-title">回測表現儀表板</h1>
      <span v-if="referenceDate" class="ref-date">資料截至 {{ referenceDate }}</span>
    </div>

    <div class="disclaimer">
      ⚠️ 樣本集中於 2025–2026 年，包含 AI／半導體大多頭行情，絕對報酬偏高。
      請以<strong>超額報酬（α）與勝率</strong>為主要判讀依據，過去績效不代表未來。非投資建議。
    </div>

    <p v-if="loading" class="loading">載入回測大數據中 …</p>

    <template v-else>
      <!-- 全局回測控制篩選列 -->
      <section class="filter-bar">
        <div class="filter-group">
          <span class="filter-label">市場篩選</span>
          <div class="filter-pills">
            <BaseChip 
              v-for="m in ['ALL', 'TW', 'US'] as const" 
              :key="m" 
              :active="selectedMarket === m" 
              @click="selectedMarket = m"
            >
              {{ m === 'ALL' ? '全部' : m === 'TW' ? '台股' : '美股' }}
            </BaseChip>
          </div>
        </div>

        <div class="filter-group">
          <span class="filter-label">回測區間</span>
          <div class="date-range-picker">
            <BaseInput type="date" v-model="filterFrom" :min="dateMin" :max="filterTo" class="date-input-field" />
            <span class="filter-sep">—</span>
            <BaseInput type="date" v-model="filterTo" :min="filterFrom" :max="dateMax" class="date-input-field" />
            <BaseChip class="reset-btn" @click="filterFrom = dateMin; filterTo = dateMax">全部區間</BaseChip>
          </div>
        </div>

        <span class="filter-count">
          {{ featured?.id }} 目前範圍共 {{ featured?._trades?.length ?? 0 }} 筆交易
        </span>
      </section>

      <!-- 主要策略選擇器（控制下方 KPI 指標卡） -->
      <section class="featured-bar">
        <span class="filter-label">主要策略</span>
        <div class="filter-pills">
          <BaseChip
            v-for="st in filteredStrategies"
            :key="'feat-' + st.id"
            :active="featuredId === st.id"
            :style="featuredId === st.id ? { background: STRAT_COLORS[st.id], color: '#0d1117' } : {}"
            @click="featuredId = st.id"
          >
            {{ st.id }}
          </BaseChip>
        </div>
        <span class="featured-label">{{ featured?.label }}</span>
      </section>

      <!-- KPI Hero Section (Upgraded) -->
      <section class="kpi-grid">
        <KpiCard
          :label="`${featured?.id} 跟單勝率`"
          :value="rate(featScopeAll?.win_rate)"
          :secondary="[
            { label: '最長連勝', value: `${featured?._maxWin ?? 0}次`, color: '#68d391' },
            { label: '最長連敗', value: `${featured?._maxLose ?? 0}次`, color: '#fc8181' }
          ]"
          hasTip
        >
          <template #tip>
            <strong>跟單勝率</strong>：依該策略規則進出場，獲利為正的交易比例。下方顯示最長連續獲利與虧損的交易次數。
          </template>
        </KpiCard>

        <KpiCard
          :label="`${featured?.id} 平均超額 (α)`"
          :value="pct(featScopeAll?.avg_alpha)"
          :color="retColor(featScopeAll?.avg_alpha)"
          :secondary="[
            { label: '台股', value: pct(featScopeTw?.avg_alpha), color: retColor(featScopeTw?.avg_alpha) },
            { label: '美股', value: pct(featScopeUs?.avg_alpha), color: retColor(featScopeUs?.avg_alpha) }
          ]"
          hasTip
        >
          <template #tip>
            <strong>超額報酬 (α)</strong>：跟單報酬減去基準大盤報酬（台股基準：0050；美股基準：SPY）。正值代表打敗大盤。
          </template>
        </KpiCard>

        <KpiCard
          :label="`${featured?.id} 最大回撤 (MDD)`"
          :value="pct(featured?._mdd)"
          color="#fc8181"
          subtitle="風控與策略壓力指標"
          hasTip
        >
          <template #tip>
            <strong>最大回撤 (MDD)</strong>：由日頻投組淨值計算（含持倉期間的浮動回撤），帳戶從最高峰回落至最低谷底的最大幅度。越接近 0 代表抗跌能力越強。
          </template>
        </KpiCard>

        <KpiCard
          :label="`${featured?.id} Sharpe 比率`"
          :value="featured?._sharpe != null ? featured._sharpe.toFixed(2) : '—'"
          :color="featured?._sharpe && featured._sharpe > 1 ? '#68d391' : '#f6ad55'"
          subtitle="每承擔一單位風險的超額"
          hasTip
        >
          <template #tip>
            <strong>Sharpe Ratio (夏普值)</strong>：由投組淨值的週期報酬計算（依實際取樣頻率年化，含現金空檔）。通常大於 1 代表這套策略的「CP值」相當優異。
          </template>
        </KpiCard>

        <KpiCard
          :label="`${featured?.id} 年化報酬 (CAGR)`"
          :value="pct(featured?._cagr)"
          :color="retColor(featured?._cagr)"
          subtitle="日頻淨值年化複合"
          hasTip
        >
          <template #tip>
            <strong>CAGR (年化複合報酬)</strong>：由日頻投組淨值序列，依篩選區間首尾與實際天數年化。已扣交易成本，含資金上限（最多同時持 10 檔）與現金空檔。
          </template>
        </KpiCard>
      </section>

      <!-- 邊際真實性檢驗：嚴格對標 + 因子拆解 -->
      <section v-if="featuredFactor?.decomp" class="strat chart-section">
        <h2 class="chart-section-title">🔬 {{ featured?.id }} 邊際真實性檢驗（美股・全期）</h2>
        <p class="strat-desc">
          頭條的「贏大盤(α)」常常只是押對<strong>半導體 beta</strong>。這裡把策略報酬回歸到
          市場(SPY)＋費半(SOXX)，看剝掉這兩個 beta 後是否還有<strong>殘餘真 α</strong>。
          僅美股、全期；非投資建議。
        </p>
        <div class="factor-grid">
          <!-- 嚴格對標 -->
          <div class="factor-block">
            <div class="factor-block-title">每筆平均超額 vs 不同基準（贏面）</div>
            <table class="app-table bt-table small">
              <thead>
                <tr><th>對標</th><th class="num">平均超額 α</th><th class="num">贏面</th><th class="num">樣本</th></tr>
              </thead>
              <tbody>
                <tr v-for="tic in ['SPY', 'QQQ', 'SOXX']" :key="tic">
                  <td>
                    {{ tic }}
                    <span class="bm-note">{{ tic === 'SPY' ? '大盤' : tic === 'QQQ' ? '科技' : '費半（最嚴）' }}</span>
                  </td>
                  <td class="num" :style="{ color: retColor(featuredFactor?.vs?.[tic]?.avg_alpha) }">
                    <strong>{{ featuredFactor?.vs?.[tic] ? pct(featuredFactor.vs[tic]!.avg_alpha) : '—' }}</strong>
                  </td>
                  <td class="num">{{ featuredFactor?.vs?.[tic] ? rate(featuredFactor.vs[tic]!.beat_rate) : '—' }}</td>
                  <td class="num muted">{{ featuredFactor?.vs?.[tic]?.n ?? '—' }}</td>
                </tr>
              </tbody>
            </table>
          </div>
          <!-- 因子拆解 -->
          <div class="factor-block">
            <div class="factor-block-title">因子拆解（r = α + β·市場 + β·費半）</div>
            <div class="decomp-cards">
              <div class="decomp-card">
                <div class="decomp-label">對大盤 β</div>
                <div class="decomp-val">{{ featuredFactor?.decomp?.beta_mkt?.toFixed(2) }}</div>
              </div>
              <div class="decomp-card">
                <div class="decomp-label">對費半 β</div>
                <div class="decomp-val" :class="{ hot: (featuredFactor?.decomp?.beta_semis ?? 0) >= 0.4 }">
                  {{ featuredFactor?.decomp?.beta_semis?.toFixed(2) }}
                </div>
              </div>
              <div class="decomp-card">
                <div class="decomp-label">殘餘真 α（年化）</div>
                <div class="decomp-val" :style="{ color: retColor(featuredFactor?.decomp?.alpha_ann) }">
                  {{ pct(featuredFactor?.decomp?.alpha_ann) }}
                </div>
              </div>
              <div class="decomp-card">
                <div class="decomp-label">R²（beta 解釋度）</div>
                <div class="decomp-val">{{ featuredFactor?.decomp?.r2 != null ? featuredFactor.decomp.r2.toFixed(2) : '—' }}</div>
              </div>
            </div>
          </div>
        </div>
        <p class="factor-verdict">📌 {{ factorVerdict }}</p>
      </section>

      <!-- 主要策略「目前建議買進／續抱」 -->
      <section class="strat chart-section rec-section">
        <h2 class="chart-section-title">🛒 {{ featured?.id }} 目前建議買進／續抱</h2>
        <p class="strat-desc">
          依「{{ featured?.label }}」規則，截至 {{ referenceDate }} 仍開倉中的標的。
          <strong class="buy-hint">可買進</strong>＝訊號 ≤14 天（剛點名、時效新）；
          <strong class="hold-hint">續抱</strong>＝較早進場、規則上仍持有。
          切換上方「主要策略」可看各策略的建議；受市場篩選影響。未實現報酬為現價對進場價（未扣賣出成本）。
        </p>
        <div class="rec-controls">
          <label class="fresh-toggle">
            <input type="checkbox" v-model="recFreshOnly" />
            只看可買進（訊號 ≤14 天）
          </label>
          <span class="rec-count">
            可買 <strong class="buy-hint">{{ featuredBuyCount }}</strong> 檔 ・
            續抱 <strong>{{ featuredHoldCount }}</strong> 檔
          </span>
        </div>
        <RecommendationList :recs="featuredRecs" :tickerMap="tickerToIdMap" />
      </section>

      <!-- 三策略 NAV 淨值合圖 -->
      <section class="strat chart-section">
        <h2 class="chart-section-title">📈 策略 NAV 淨值走勢對比（複利）</h2>
        <p class="strat-desc">初始資金 $1.00，資金均分為 10 個部位（最多同時持 10 檔），逐日以收盤 mark-to-market 之投組淨值，已扣交易成本。基準為買進持有台股 (0050) / 美股 (SPY)；「全部」為依交易數加權混合。曲線依上方篩選區間重設基準。</p>
        <div class="multi-curve-wrap">
          <MultiEquityChart :series="chartSeries" :height="240" />
        </div>
      </section>

      <!-- 年度超額報酬 (α) 對比 (New Feature) -->
      <section class="strat chart-section">
        <h2 class="chart-section-title">📆 策略年度績效明細</h2>
        <p class="strat-desc">查看各策略在不同年份內，經過市場篩選後的交易數量、勝率與超額報酬 α 表現。</p>
        <div class="yearly-comparison">
          <div v-for="st in filteredStrategies" :key="'yearly-' + st.id" class="yearly-strategy-card">
            <div class="yearly-strat-title">
              <span class="sid">{{ st.id }}</span> {{ st.label }}
            </div>
            <table class="app-table bt-table small">
              <thead>
                <tr>
                  <th>年份</th>
                  <th class="num">交易數</th>
                  <th class="num">勝率</th>
                  <th class="num">平均報酬</th>
                  <th class="num">超額 (α)</th>
                  <th class="num">贏大盤率</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="y in st._yearly" :key="y.year">
                  <td>{{ y.year }} 年</td>
                  <td class="num">{{ y.n_trades }}</td>
                  <td class="num">{{ rate(y.win_rate) }}</td>
                  <td class="num" :style="{ color: retColor(y.avg_return) }">{{ pct(y.avg_return) }}</td>
                  <td class="num" :style="{ color: retColor(y.avg_alpha) }"><strong>{{ pct(y.avg_alpha) }}</strong></td>
                  <td class="num">{{ rate(y.beat_bm_rate) }}</td>
                </tr>
                <tr v-if="!(st._yearly?.length)">
                  <td colspan="6" class="empty-td">目前篩選條件下無年度交易數據</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <!-- 命中率統計視覺化 -->
      <section class="strat chart-section">
        <h2 class="chart-section-title">🎯 「看多」訊號持有天數命中率</h2>
        <p class="strat-desc">探討：被點名「看多」之後，持有 30 / 60 / 90 天的上漲勝率與打敗基準的機率。</p>
        <div class="hit-rate-container">
          <div class="hit-rate-chart-wrap">
            <HitRateChart :hitRate="hitRate" />
          </div>
          <div class="hit-rate-table-wrap">
            <table class="app-table bt-table small">
              <thead>
                <tr><th>持有天數</th><th>樣本數</th><th>上漲比例</th><th>平均報酬</th><th>超額(α)</th><th>贏大盤率</th></tr>
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
          </div>
        </div>
      </section>

      <!-- 策略個別解析 -->
      <h2 class="section-divider">策略個別解析</h2>

      <section v-for="st in filteredStrategies" :key="st.id" class="strat details-card">
        <div class="strat-header-row">
          <h3 class="strat-title"><span class="sid">{{ st.id }}</span> {{ st.label }}</h3>
          <button class="expand-btn-text" @click="toggle(st.id)">
            {{ expanded[st.id] ? '收合明細 ▲' : `展開交易明細（${getFilteredTrades(st.id, st._trades).length} 筆）▼` }}
          </button>
        </div>

        <!-- 聚合統計表 -->
        <table class="app-table bt-table">
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
              <div class="perf-head win">最佳 5 檔超額 (α)</div>
              <div v-for="t in topBottomBy(st._trades, 'alpha').top" :key="t.ticker + t.entry_date" class="perf-row">
                <router-link v-if="tickerToIdMap[t.ticker]" :to="`/stocks/${tickerToIdMap[t.ticker]}`" class="perf-ticker">
                  {{ t.ticker }}
                </router-link>
                <span v-else class="perf-ticker">{{ t.ticker }}</span>
                <span class="perf-name">{{ t.name_zh }}</span>
                <span class="perf-val win">{{ pct(t.alpha) }}</span>
              </div>
            </div>
            <div class="perf-col">
              <div class="perf-head loss">最差 5 檔超額 (α)</div>
              <div v-for="t in topBottomBy(st._trades, 'alpha').bottom" :key="t.ticker + t.entry_date" class="perf-row">
                <router-link v-if="tickerToIdMap[t.ticker]" :to="`/stocks/${tickerToIdMap[t.ticker]}`" class="perf-ticker">
                  {{ t.ticker }}
                </router-link>
                <span v-else class="perf-ticker">{{ t.ticker }}</span>
                <span class="perf-name">{{ t.name_zh }}</span>
                <span class="perf-val loss">{{ pct(t.alpha) }}</span>
              </div>
            </div>
          </div>
        </template>

        <!-- 交易清單展開區域 -->
        <div v-show="expanded[st.id]" class="trade-log-wrap">
          <div class="trade-filter-bar">
            <BaseInput 
              type="text" 
              v-model="searchQuery[st.id]" 
              placeholder="搜尋代號或名稱..." 
              class="trade-search-input" 
            />
            <div class="trade-filter-pills">
              <BaseChip 
                class="small"
                :active="tradeResultFilter[st.id] === 'ALL'" 
                @click="tradeResultFilter[st.id] = 'ALL'"
              >
                全部交易
              </BaseChip>
              <BaseChip 
                class="small"
                :active="tradeResultFilter[st.id] === 'WIN'" 
                @click="tradeResultFilter[st.id] = 'WIN'"
              >
                獲利
              </BaseChip>
              <BaseChip 
                class="small"
                :active="tradeResultFilter[st.id] === 'LOSS'" 
                @click="tradeResultFilter[st.id] = 'LOSS'"
              >
                虧損
              </BaseChip>
            </div>
            <span class="filtered-count">
              篩選後共 {{ getFilteredTrades(st.id, st._trades).length }} 筆
            </span>
          </div>

          <div class="trade-log">
            <table class="app-table bt-table small">
              <thead>
                <tr>
                  <th>股票</th>
                  <th>市場</th>
                  <th>集日期</th>
                  <th>進場</th>
                  <th>出場</th>
                  <th>持有天數</th>
                  <th class="num">報酬</th>
                  <th class="num">超額(α)</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="t in getFilteredTrades(st.id, st._trades)" :key="t.ticker + t.entry_date">
                  <td>
                    <router-link v-if="tickerToIdMap[t.ticker]" :to="`/stocks/${tickerToIdMap[t.ticker]}`" class="ticker-link">
                      <span class="ticker">{{ t.ticker }}</span>
                    </router-link>
                    <span v-else class="ticker">{{ t.ticker }}</span>
                    <span class="stock-name">{{ t.name_zh }}</span>
                  </td>
                  <td>{{ t.market }}</td>
                  <td class="mono">{{ t.ep_date }}</td>
                  <td class="mono">{{ t.entry_date }}</td>
                  <td class="mono">{{ t.exit_date }}</td>
                  <td class="num">{{ getDaysBetween(t.entry_date, t.exit_date) }} 天</td>
                  <td class="num" :style="{ color: retColor(t.ret) }">{{ pct(t.ret) }}</td>
                  <td class="num" :style="{ color: retColor(t.alpha) }"><strong>{{ pct(t.alpha) }}</strong></td>
                </tr>
                <tr v-if="getFilteredTrades(st.id, st._trades).length === 0">
                  <td colspan="8" class="empty-td">無符合條件之交易</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </section>

      <p class="method">
        交易假設說明：進場價為集發布日隔日起第一個收盤，收盤對收盤計算；基準 TW→0050、US→SPY。
        報酬<strong>已扣交易成本</strong>（台股：手續費 0.1425%／邊 + 證交稅 0.3% 賣出 + 滑價 0.05%／邊；
        美股：免佣金，僅估滑價 0.05%／邊）。基準以被動持有計、不扣每筆成本，
        故 α 代表「扣掉自己的交易成本後是否仍贏過懶人持有大盤」。
        S2 持有 {{ holdDays }} 天。折線圖為逐日 mark-to-market 之投組淨值（資金均分 10 部位、含現金空檔），
        Sharpe／MDD／CAGR 皆由此日頻序列計算。
      </p>
    </template>
  </div>
</template>

<style scoped>
.disclaimer {
  background: #2d2410; color: #f6ad55; font-size: 0.82rem; line-height: 1.6;
  padding: 0.75rem 1rem; border-radius: 8px; margin-bottom: 1.5rem;
  border-left: 4px solid #f6ad55;
}
.disclaimer strong { color: #fbd38d; }

/* 篩選列 */
.filter-bar {
  display: flex; align-items: center; gap: 1.5rem; flex-wrap: wrap;
  background: #1a1f2e; padding: 0.75rem 1.25rem; border-radius: 8px; margin-bottom: 1.5rem;
  border: 1px solid #2d3748;
}
.filter-group {
  display: flex; align-items: center; gap: 0.75rem;
}
.filter-label { font-size: 0.8rem; color: #718096; font-weight: 600; white-space: nowrap; }
.filter-sep { color: #718096; }
.date-range-picker {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: nowrap;
}
.date-input-field {
  max-width: 140px;
  margin-bottom: 0 !important;
}
.reset-btn {
  font-size: 0.78rem;
  padding: 0.35rem 0.75rem;
}
.filter-count { font-size: 0.78rem; color: #718096; margin-left: auto; }

/* 邊際真實性檢驗 */
.factor-grid {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1.25rem; margin-top: 0.75rem;
}
@media (max-width: 768px) { .factor-grid { grid-template-columns: 1fr; } }
.factor-block-title { font-size: 0.82rem; color: #a0aec0; font-weight: 600; margin-bottom: 0.5rem; }
.bm-note { color: #4a5568; font-size: 0.72rem; margin-left: 0.3rem; }
.decomp-cards { display: grid; grid-template-columns: 1fr 1fr; gap: 0.75rem; }
.decomp-card {
  background: #1e2535; border: 1px solid #2d3748; border-radius: 8px; padding: 0.7rem 0.9rem;
}
.decomp-label { font-size: 0.72rem; color: #718096; margin-bottom: 0.2rem; }
.decomp-val { font-size: 1.3rem; font-weight: 800; font-variant-numeric: tabular-nums; color: #e2e8f0; }
.decomp-val.hot { color: #f6ad55; }
.factor-verdict {
  margin-top: 1rem; padding: 0.75rem 1rem; background: #1a2230; border-left: 3px solid #63b3ed;
  border-radius: 6px; font-size: 0.84rem; color: #cbd5e0; line-height: 1.6;
}

/* 目前建議區 */
.rec-section .strat-desc { line-height: 1.7; }
.buy-hint { color: #68d391; }
.hold-hint { color: #a0aec0; }
.rec-controls {
  display: flex; align-items: center; gap: 1.25rem; flex-wrap: wrap;
  margin: 0.5rem 0 0.85rem;
}
.fresh-toggle {
  display: flex; align-items: center; gap: 0.4rem;
  font-size: 0.82rem; color: #a0aec0; cursor: pointer; user-select: none;
}
.fresh-toggle input { cursor: pointer; }
.rec-count { font-size: 0.82rem; color: #718096; }

/* 主要策略選擇器 */
.featured-bar {
  display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
  margin-bottom: 1rem;
}
.featured-label { font-size: 0.85rem; color: #a0aec0; font-weight: 600; }

/* KPI Grid */
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 1rem;
  margin-bottom: 1.5rem;
}

/* Chart Sections */
.chart-section {
  background: #1a1f2e;
  border: 1px solid #2d3748;
  border-radius: 10px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}
.chart-section-title {
  font-size: 1.15rem;
  font-weight: 700;
  margin-bottom: 0.3rem;
  color: #e2e8f0;
}
.multi-curve-wrap {
  margin-top: 1rem;
}

/* Hit Rate Split */
.hit-rate-container {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 1.5rem;
  align-items: center;
  margin-top: 1rem;
}
@media (max-width: 768px) {
  .hit-rate-container {
    grid-template-columns: 1fr;
  }
}

/* Yearly breakdown grid */
.yearly-comparison {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.25rem;
  margin-top: 1rem;
}
.yearly-strategy-card {
  background: #1e2535;
  border: 1px solid #2d3748;
  border-radius: 8px;
  padding: 1rem;
}
.yearly-strat-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #e2e8f0;
  margin-bottom: 0.75rem;
  border-bottom: 1px solid #2d3748;
  padding-bottom: 0.35rem;
}

/* Details Cards & Divider */
.section-divider {
  font-size: 1.3rem;
  font-weight: 700;
  color: #a0aec0;
  margin: 2.5rem 0 1rem 0;
  border-bottom: 1px solid #2d3748;
  padding-bottom: 0.5rem;
}
.details-card {
  background: #151a26;
  border: 1px solid #232c3f;
  border-radius: 10px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}
.strat-header-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}
.strat-title { font-size: 1.1rem; font-weight: 700; }
.strat-title .sid { color: #63b3ed; font-family: monospace; margin-right: 0.3rem; }
.strat-desc { font-size: 0.8rem; color: #718096; margin-bottom: 0.75rem; }

.expand-btn-text {
  background: none; border: none; color: #63b3ed;
  font-size: 0.82rem; font-weight: 600; cursor: pointer;
  padding: 0.25rem 0.5rem;
}
.expand-btn-text:hover {
  text-decoration: underline;
}

/* Tables */
.bt-table th {
  padding: 0.6rem 0.9rem; background: #1e2535;
}
.bt-table td { padding: 0.6rem 0.9rem; }
.bt-table.small td { padding: 0.45rem 0.8rem; font-size: 0.78rem; }
.bt-table tr.dim td { color: #4a5568; }
.num { text-align: right; font-variant-numeric: tabular-nums; }
.muted { color: #718096; }
.mono { font-family: monospace; font-size: 0.78rem; color: #718096; }
.ticker { font-family: monospace; color: #63b3ed; font-weight: 600; }
.ticker-link {
  text-decoration: none;
}
.ticker-link:hover .ticker {
  text-decoration: underline;
}
.stock-name {
  color: #e2e8f0;
  margin-left: 0.4rem;
}
.empty-td {
  text-align: center;
  color: #4a5568;
  padding: 2rem !important;
}

/* Performers */
.performers {
  display: grid; grid-template-columns: 1fr 1fr; gap: 1rem;
  margin: 1rem 0;
}
.perf-col { background: #1e2535; border-radius: 8px; padding: 0.6rem 0.9rem; border: 1px solid #2d3748; }
.perf-head { font-size: 0.76rem; font-weight: 700; margin-bottom: 0.5rem; letter-spacing: 0.04em; }
.perf-head.win { color: #68d391; }
.perf-head.loss { color: #fc8181; }
.perf-row { display: flex; align-items: baseline; gap: 0.4rem; padding: 0.25rem 0; font-size: 0.78rem; border-bottom: 1px dashed #2d3748; }
.perf-row:last-child { border-bottom: none; }
.perf-ticker { font-family: monospace; color: #63b3ed; font-weight: 600; min-width: 3.5rem; text-decoration: none; }
.perf-ticker:hover { text-decoration: underline; }
.perf-name { color: #a0aec0; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.perf-val { font-variant-numeric: tabular-nums; font-size: 0.8rem; margin-left: auto; font-weight: 600; }
.perf-val.win { color: #68d391; }
.perf-val.loss { color: #fc8181; }

/* Filter pills and Search inside trade log */
.trade-log-wrap {
  margin-top: 1rem;
  border-top: 1px solid #2d3748;
  padding-top: 1rem;
}
.trade-filter-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.75rem;
  flex-wrap: wrap;
}
.trade-search-input {
  max-width: 180px;
  margin-bottom: 0;
}
.trade-filter-pills {
  display: flex;
  gap: 0.35rem;
}
.trade-filter-pills .small {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}
.filtered-count {
  font-size: 0.75rem;
  color: #718096;
  margin-left: auto;
}

.trade-log { max-height: 400px; overflow-y: auto; border-radius: 8px; border: 1px solid #2d3748; }

.method { font-size: 0.76rem; color: #718096; line-height: 1.6; margin-top: 1.5rem; }
</style>
