<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { supabase } from '@/lib/supabase'
import type { Episode } from '@/lib/types'

const episodes = ref<Episode[]>([])
const loading = ref(true)

onMounted(async () => {
  const { data } = await supabase
    .from('episodes')
    .select('*')
    .order('ep_no', { ascending: false })
  episodes.value = (data ?? []) as Episode[]
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
</style>
