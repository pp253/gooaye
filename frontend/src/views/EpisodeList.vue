<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { supabase, fetchAllPaged } from '@/lib/supabase'
import { useQuerySync } from '@/lib/useQuerySync'
import type { Episode, Direction } from '@/lib/types'

interface Chip { name: string; direction: Direction }

const EP_COLUMNS = 'id, ep_no, title, source_url, published_at, summary, topics, created_at'
// 看多 → 中性 → 看空 的排序權重
const DIR_ORDER: Record<Direction, number> = { 看多: 0, 中性: 1, 看空: 2 }
const PAGE_SIZE = 100

/** 撈 mentions（PostgREST 單次上限 1000 列，mentions 表已超過，需分頁）。
 *  傳 episodeIds 時只查這些集數（單頁用，通常一次就夠）；不傳則撈全表（搜尋用）。 */
async function fetchMentionsMap(episodeIds?: number[]): Promise<Record<number, Chip[]>> {
  const rows = await fetchAllPaged<{ episode_id: number; name_raw: string; direction: Direction }>(
    (offset, limit) => {
      let query = supabase
        .from('mentions')
        .select('episode_id, name_raw, direction')
        .order('id', { ascending: true })
        .range(offset, offset + limit - 1)
      if (episodeIds) query = query.in('episode_id', episodeIds)
      return query
    },
  )
  const map: Record<number, Chip[]> = {}
  for (const m of rows) {
    ;(map[m.episode_id] ??= []).push({ name: m.name_raw, direction: m.direction })
  }
  for (const id in map) {
    map[id].sort((a, b) => DIR_ORDER[a.direction] - DIR_ORDER[b.direction])
  }
  return map
}

const search = ref('')
// ''＝第一頁（最新一百集）；否則為 "低-高"，如 "601-700"
const pageKey = ref('')

useQuerySync({
  q: { ref: search, default: '' },
  page: { ref: pageKey, default: '' },
})

const isSearching = computed(() => search.value.trim().length > 0)

// ── 單頁載入（預設路徑：只抓目前頁的 100 集 + 對應 mentions）──
const maxEpNo = ref(0)
const pageEpisodes = ref<Episode[]>([])
const pageMentions = ref<Record<number, Chip[]>>({})
const pageLoading = ref(true)

// 依 ep_no 切成每 100 集一頁，邊界對齊整百（700-601、600-501…），與實際缺集無關
const pages = computed(() => {
  if (maxEpNo.value === 0) return []
  const top = Math.ceil(maxEpNo.value / PAGE_SIZE) * PAGE_SIZE
  const list: { key: string; label: string; low: number; high: number }[] = []
  for (let high = top; high > 0; high -= PAGE_SIZE) {
    const low = Math.max(high - PAGE_SIZE + 1, 1)
    list.push({ key: `${low}-${high}`, label: `${high}-${low}`, low, high })
  }
  return list
})

const currentPage = computed(() => pages.value.find((p) => p.key === pageKey.value) ?? pages.value[0])

async function loadPage() {
  if (!currentPage.value) {
    pageEpisodes.value = []
    pageMentions.value = {}
    pageLoading.value = false
    return
  }
  pageLoading.value = true
  const { low, high } = currentPage.value
  const { data } = await supabase
    .from('episodes')
    .select(EP_COLUMNS)
    .gte('ep_no', low)
    .lte('ep_no', high)
    .order('ep_no', { ascending: false })
  const eps = (data ?? []) as Episode[]
  pageEpisodes.value = eps
  pageMentions.value = await fetchMentionsMap(eps.map((e) => e.id))
  pageLoading.value = false
}

// ── 搜尋路徑：使用者開始搜尋時才懶載入全量資料（跨全部集數比對），只載一次、之後快取 ──
const allEpisodes = ref<Episode[] | null>(null)
const allMentions = ref<Record<number, Chip[]> | null>(null)
const searchLoading = ref(false)

async function ensureFullDataLoaded() {
  if (allEpisodes.value) return
  searchLoading.value = true
  const { data } = await supabase.from('episodes').select(EP_COLUMNS).order('ep_no', { ascending: false })
  allEpisodes.value = (data ?? []) as Episode[]
  allMentions.value = await fetchMentionsMap()
  searchLoading.value = false
}

watch(isSearching, (v) => {
  if (v) ensureFullDataLoaded()
})
watch(pageKey, () => {
  if (!isSearching.value) loadPage()
})

// ── 顯示用：依目前是否搜尋，切換資料來源 ──
const busy = computed(() => (isSearching.value ? searchLoading.value : pageLoading.value))
const mentionsByEp = computed(() => (isSearching.value ? allMentions.value ?? {} : pageMentions.value))

const displayEpisodes = computed(() => {
  if (!isSearching.value) return pageEpisodes.value
  const q = search.value.trim().toLowerCase()
  const eps = allEpisodes.value ?? []
  const mentions = allMentions.value ?? {}
  return eps.filter((ep) => {
    if (String(ep.ep_no).includes(q)) return true
    if (ep.title?.toLowerCase().includes(q)) return true
    if (ep.topics.some((t) => t.toLowerCase().includes(q))) return true
    if (ep.summary.some((s) => s.toLowerCase().includes(q))) return true
    if (mentions[ep.id]?.some((c) => c.name.toLowerCase().includes(q))) return true
    return false
  })
})

onMounted(async () => {
  const { data } = await supabase.from('episodes').select('ep_no').order('ep_no', { ascending: false }).limit(1)
  maxEpNo.value = data?.[0]?.ep_no ?? 0
  await loadPage()
})
</script>

<template>
  <div>
    <h1 class="page-title">集數列表</h1>

    <input
      v-model="search"
      type="search"
      class="search-box"
      placeholder="搜尋集數、標題、主題、提及個股…"
    />

    <div v-if="!isSearching && pages.length > 1" class="pager">
      <button
        v-for="p in pages" :key="p.key"
        :class="['chip', { active: p.key === currentPage?.key }]"
        @click="pageKey = p.key"
      >
        {{ p.label }}
      </button>
    </div>
    <p v-else-if="isSearching" class="search-hint">搜尋結果（跨全部集數，不分頁）</p>

    <p v-if="busy" class="loading">載入中 …</p>
    <p v-else-if="displayEpisodes.length === 0" class="loading">沒有符合條件的集數</p>
    <div v-else class="episode-grid">
      <RouterLink
        v-for="ep in displayEpisodes"
        :key="ep.id"
        :to="`/episodes/${ep.ep_no}`"
        class="ep-card"
      >
        <div class="ep-header">
          <span class="ep-no">EP{{ ep.ep_no }}</span>
          <span class="ep-title">{{ ep.title }}</span>
          <span class="ep-date" v-if="ep.published_at">{{ ep.published_at }}</span>
        </div>
        <ul class="ep-summary">
          <li v-for="(s, i) in ep.summary.slice(0, 3)" :key="i">{{ s }}</li>
        </ul>
        <div class="ep-tags">
          <span v-for="t in ep.topics.slice(0, 4)" :key="t" class="tag">{{ t }}</span>
        </div>
        <div v-if="mentionsByEp[ep.id]?.length" class="ep-mentions">
          <span
            v-for="(c, i) in mentionsByEp[ep.id].slice(0, 12)" :key="i"
            :class="['m-chip', c.direction === '看多' ? 'bull' : c.direction === '看空' ? 'bear' : 'neutral']"
          >{{ c.name }}</span>
          <span v-if="mentionsByEp[ep.id].length > 12" class="m-more">
            +{{ mentionsByEp[ep.id].length - 12 }}
          </span>
        </div>
      </RouterLink>
    </div>
  </div>
</template>

<style scoped>
.page-title { font-size: 1.4rem; font-weight: 700; margin-bottom: 1.5rem; color: transparent; background: linear-gradient(90deg, #63b3ed, #9ae6b4); -webkit-background-clip: text; background-clip: text; }
.loading { color: #718096; }

.search-box {
  display: block; width: 100%; max-width: 360px; margin-bottom: 1.25rem;
  padding: 0.45rem 0.75rem; border-radius: 8px; border: 1px solid #2d3748;
  background: #1a1f2e; color: #e2e8f0; font-size: 0.88rem;
}
.search-box::placeholder { color: #718096; }
.search-box:focus { outline: none; border-color: #63b3ed; }

.pager { display: flex; flex-wrap: wrap; gap: 0.4rem; margin-bottom: 1.25rem; }
.chip {
  background: #2d3748; color: #a0aec0; border: none; border-radius: 6px;
  padding: 0.3rem 0.7rem; cursor: pointer; font-size: 0.8rem;
  transition: background 0.15s, color 0.15s;
}
.chip:hover { background: #374151; }
.chip.active { background: linear-gradient(135deg, #63b3ed, #4299e1); color: #1a1f2e; font-weight: 600; box-shadow: 0 4px 12px -4px rgba(99, 179, 237, 0.5); }
.search-hint { color: #718096; font-size: 0.82rem; margin-bottom: 1.25rem; }

.episode-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.ep-card {
  background: #1a1f2e;
  border: 1px solid #2d3748;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  transition: border-color 0.15s, background 0.15s, transform 0.15s, box-shadow 0.15s;
}
.ep-card:hover {
  border-color: #63b3ed; background: #1e2535;
  transform: translateY(-2px);
  box-shadow: 0 10px 24px -12px rgba(99, 179, 237, 0.3);
}

.ep-header { display: flex; align-items: baseline; gap: 0.6rem; }
.ep-no { font-weight: 700; color: #63b3ed; font-size: 1rem; white-space: nowrap; }
.ep-title { color: #a0aec0; font-size: 0.9rem; }
.ep-date { color: #718096; font-size: 0.75rem; margin-left: auto; }

.ep-summary { padding-left: 1rem; color: #cbd5e0; font-size: 0.82rem; line-height: 1.6; }
.ep-summary li { margin-bottom: 0.2rem; }

.ep-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; }
.tag {
  background: #2d3748;
  color: #90cdf4;
  font-size: 0.72rem;
  padding: 0.15rem 0.5rem;
  border-radius: 9999px;
}

.ep-mentions { display: flex; flex-wrap: wrap; gap: 0.3rem; border-top: 1px solid #232b3a; padding-top: 0.6rem; }
.m-chip { font-size: 0.72rem; padding: 0.12rem 0.45rem; border-radius: 4px; }
.m-chip.bull { background: #22543d; color: #9ae6b4; }
.m-chip.bear { background: #5b2330; color: #feb2b2; }
.m-chip.neutral { background: #2a3950; color: #90cdf4; }
.m-more { font-size: 0.72rem; color: #718096; align-self: center; }
</style>
