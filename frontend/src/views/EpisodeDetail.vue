<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase } from '@/lib/supabase'
import { DIRECTION_COLOR as dirColor } from '@/lib/signal'
import type { Episode, Mention } from '@/lib/types'

const props = defineProps<{ ep: string }>()

const episode = ref<Episode | null>(null)
const mentions = ref<Mention[]>([])
const loading = ref(true)
const activeTab = ref<'mentions' | 'transcript'>('mentions')
const transcript = ref<string | null>(null)
const transcriptLoading = ref(false)

// 初始查詢明列欄位、排除大欄位 transcript（只留小的 transcript_chars 顯示字數）
const EP_COLS =
  'id, ep_no, title, source_url, published_at, summary, topics, created_at, transcript_chars, site_desc'

onMounted(async () => {
  const [epRes, mentionRes] = await Promise.all([
    supabase.from('episodes').select(EP_COLS).eq('ep_no', props.ep).single(),
    supabase
      .from('mentions')
      .select('*, stocks(ticker, name_zh, market)')
      .eq('episode_id',
        (await supabase.from('episodes').select('id').eq('ep_no', props.ep).single()).data?.id ?? -1
      )
      .order('confidence', { ascending: false }),
  ])
  episode.value = epRes.data as Episode
  mentions.value = (mentionRes.data ?? []) as Mention[]
  loading.value = false
})

// 切到逐字稿分頁才抓 transcript（大欄位，lazy load，只抓一次）
async function openTranscript() {
  activeTab.value = 'transcript'
  if (transcript.value !== null || !episode.value) return
  transcriptLoading.value = true
  const { data } = await supabase
    .from('episodes')
    .select('transcript')
    .eq('id', episode.value.id)
    .single()
  transcript.value = (data?.transcript as string | null) ?? ''
  transcriptLoading.value = false
}
</script>

<template>
  <div>
    <p v-if="loading" class="loading">載入中 …</p>
    <template v-else-if="episode">
      <div class="ep-header">
        <h1 class="ep-title">EP{{ episode.ep_no }} {{ episode.title }}</h1>
        <span class="ep-date" v-if="episode.published_at">{{ episode.published_at }}</span>
        <a :href="episode.source_url" target="_blank" class="src-link">逐字稿原文 ↗</a>
      </div>

      <div class="tags-row">
        <span v-for="t in episode.topics" :key="t" class="tag">{{ t }}</span>
      </div>

      <section class="section">
        <h2 class="section-title">本集重點</h2>
        <ol class="summary-list">
          <li v-for="(s, i) in episode.summary" :key="i">{{ s }}</li>
        </ol>
      </section>

      <div class="tab-bar" role="tablist">
        <button
          :class="['tab', { active: activeTab === 'mentions' }]"
          role="tab" :aria-selected="activeTab === 'mentions'"
          @click="activeTab = 'mentions'"
        >
          提及個股 <span class="tab-count">{{ mentions.length }}</span>
        </button>
        <button
          v-if="episode.transcript_chars"
          :class="['tab', { active: activeTab === 'transcript' }]"
          role="tab" :aria-selected="activeTab === 'transcript'"
          @click="openTranscript"
        >
          逐字稿
          <span class="tab-count">{{ episode.transcript_chars.toLocaleString() }} 字</span>
        </button>
      </div>

      <section v-show="activeTab === 'mentions'" class="section" role="tabpanel">
        <div v-if="mentions.length === 0" class="empty">本集無明確個股提及</div>
        <div class="mention-list">
          <div v-for="m in mentions" :key="m.id" class="app-card mention-card">
            <div class="mention-top">
              <RouterLink v-if="m.stock_id" :to="`/stocks/${m.stock_id}`" class="m-name link">
                {{ m.name_raw }} ↗
              </RouterLink>
              <span v-else class="m-name">{{ m.name_raw }}</span>
              <span class="m-ticker" v-if="m.ticker_guess">{{ m.ticker_guess }}</span>
              <span class="m-market">{{ m.market }}</span>
              <span class="m-dir" :style="{ color: dirColor[m.direction] }">
                {{ m.direction }}
              </span>
              <span class="m-conf">信心 {{ Math.round(m.confidence * 100) }}%</span>
              <span v-if="m.has_position" class="m-pos">有部位</span>
            </div>
            <blockquote class="m-quote">「{{ m.quote }}」</blockquote>
            <p class="m-note" v-if="m.note">{{ m.note }}</p>
          </div>
        </div>
      </section>

      <section
        v-if="episode.transcript_chars"
        v-show="activeTab === 'transcript'"
        class="section" role="tabpanel"
      >
        <p v-if="transcriptLoading" class="empty">逐字稿載入中 …</p>
        <pre v-else class="transcript">{{ transcript }}</pre>
      </section>
    </template>
    <p v-else class="empty">找不到此集數</p>
  </div>
</template>

<style scoped>
.ep-header { display: flex; align-items: baseline; gap: 1rem; margin-bottom: 0.75rem; }
.ep-title { font-size: 1.4rem; font-weight: 700; color: #63b3ed; }
.ep-date { font-size: 0.82rem; color: #718096; }
.src-link { font-size: 0.82rem; color: #90cdf4; text-decoration: none; margin-left: auto; }
.src-link:hover { text-decoration: underline; }

.tags-row { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-bottom: 1.5rem; }

.section { margin-bottom: 2rem; }
.section-title { font-size: 1rem; font-weight: 600; color: #a0aec0; margin-bottom: 0.75rem; border-bottom: 1px solid #2d3748; padding-bottom: 0.4rem; }

.summary-list { padding-left: 1.2rem; line-height: 1.8; color: #cbd5e0; font-size: 0.9rem; }

.mention-list { display: flex; flex-direction: column; gap: 0.75rem; }
.mention-card { padding: 0.9rem 1rem; }

.mention-top { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; margin-bottom: 0.5rem; }
.m-name { font-weight: 600; font-size: 1rem; }
.m-name.link { color: #90cdf4; text-decoration: none; }
.m-name.link:hover { text-decoration: underline; }
.m-ticker { background: #2d3748; color: #90cdf4; font-size: 0.75rem; padding: 0.1rem 0.45rem; border-radius: 4px; font-family: monospace; }
.m-market { font-size: 0.72rem; color: #718096; }
.m-dir { font-weight: 600; font-size: 0.85rem; }
.m-conf { font-size: 0.75rem; color: #718096; margin-left: auto; }
.m-pos { background: #2a4365; color: #90cdf4; font-size: 0.72rem; padding: 0.1rem 0.45rem; border-radius: 4px; }

.m-quote { border-left: 3px solid #4a5568; padding-left: 0.75rem; color: #a0aec0; font-size: 0.85rem; line-height: 1.6; font-style: italic; margin-bottom: 0.4rem; }
.m-note { font-size: 0.8rem; color: #718096; }

.tab-bar { display: flex; gap: 0.25rem; border-bottom: 1px solid #2d3748; margin-bottom: 1.25rem; }
.tab {
  background: none; border: none; cursor: pointer;
  color: #718096; font-size: 0.92rem; font-weight: 600;
  padding: 0.5rem 0.9rem; margin-bottom: -1px;
  border-bottom: 2px solid transparent; transition: color 0.15s, border-color 0.15s;
}
.tab:hover { color: #a0aec0; }
.tab.active { color: #63b3ed; border-bottom-color: #63b3ed; }
.tab-count {
  font-size: 0.72rem; font-weight: 600; color: #a0aec0;
  background: #2d3748; border-radius: 9999px; padding: 0.05rem 0.45rem; margin-left: 0.3rem;
}
.tab.active .tab-count { background: #2a4365; color: #90cdf4; }
.transcript {
  white-space: pre-wrap; word-break: break-word; margin: 0;
  background: #161b27; border: 1px solid #2d3748; border-radius: 8px;
  padding: 1rem 1.1rem; color: #cbd5e0; font-size: 0.86rem; line-height: 1.85;
  font-family: inherit; max-height: 60vh; overflow-y: auto;
}
</style>
