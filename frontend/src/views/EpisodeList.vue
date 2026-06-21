<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { supabase } from '@/lib/supabase'
import type { Episode, Direction } from '@/lib/types'

interface Chip { name: string; direction: Direction }

const episodes = ref<Episode[]>([])
const mentionsByEp = ref<Record<number, Chip[]>>({})
const loading = ref(true)

// 看多 → 中性 → 看空 的排序權重
const DIR_ORDER: Record<Direction, number> = { 看多: 0, 中性: 1, 看空: 2 }

onMounted(async () => {
  const [epRes, mRes] = await Promise.all([
    // 明列欄位，排除大欄位 transcript/site_desc（列表不需要，避免下載全部逐字稿）
    supabase
      .from('episodes')
      .select('id, ep_no, title, source_url, published_at, summary, topics, created_at')
      .order('ep_no', { ascending: false }),
    supabase.from('mentions').select('episode_id, name_raw, direction'),
  ])
  episodes.value = (epRes.data ?? []) as Episode[]

  const map: Record<number, Chip[]> = {}
  for (const m of mRes.data ?? []) {
    ;(map[m.episode_id] ??= []).push({ name: m.name_raw, direction: m.direction })
  }
  for (const id in map) {
    map[id].sort((a, b) => DIR_ORDER[a.direction] - DIR_ORDER[b.direction])
  }
  mentionsByEp.value = map
  loading.value = false
})
</script>

<template>
  <div>
    <h1 class="page-title">集數列表</h1>
    <p v-if="loading" class="loading">載入中 …</p>
    <div v-else class="episode-grid">
      <RouterLink
        v-for="ep in episodes"
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
.page-title { font-size: 1.4rem; font-weight: 700; margin-bottom: 1.5rem; color: #63b3ed; }
.loading { color: #718096; }

.episode-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1rem;
}

.ep-card {
  background: #1a1f2e;
  border: 1px solid #2d3748;
  border-radius: 8px;
  padding: 1rem 1.25rem;
  text-decoration: none;
  color: inherit;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  transition: border-color 0.15s, background 0.15s;
}
.ep-card:hover { border-color: #63b3ed; background: #1e2535; }

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
