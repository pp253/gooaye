<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { supabase } from '@/lib/supabase'
import BaseChip from '@/components/BaseChip.vue'

interface LoginLog {
  id: number
  email: string
  method: string
  logged_in_at: string
}

const logs = ref<LoginLog[]>([])
const loading = ref(true)

// Pagination & Filtering state
const page = ref(1)
const pageSize = 20
const totalCount = ref(0)
const selectedEmail = ref('ALL')
const emails = ref<string[]>([])

const totalPages = computed(() => Math.ceil(totalCount.value / pageSize) || 1)

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function methodLabel(m: string) {
  if (m === 'google') return 'Google'
  if (m === 'email') return 'Email'
  return m
}

async function fetchLogs() {
  loading.value = true
  let query = supabase
    .from('login_logs')
    .select('id, email, method, logged_in_at', { count: 'exact' })
    .order('logged_in_at', { ascending: false })

  if (selectedEmail.value !== 'ALL') {
    query = query.eq('email', selectedEmail.value)
  }

  const from = (page.value - 1) * pageSize
  const to = from + pageSize - 1

  const { data, count, error } = await query.range(from, to)
  if (!error) {
    logs.value = data ?? []
    totalCount.value = count ?? 0
  }
  loading.value = false
}

async function changePage(p: number) {
  if (p < 1 || p > totalPages.value) return
  page.value = p
  await fetchLogs()
}

async function onEmailChange() {
  page.value = 1
  await fetchLogs()
}

onMounted(async () => {
  // Load email lists for dropdown filtering
  const emailSet = new Set<string>()

  // 1. Get from allowed_emails
  const { data: members } = await supabase.from('allowed_emails').select('email')
  if (members) {
    members.forEach((m) => emailSet.add(m.email.toLowerCase()))
  }

  // 2. Get from recent login logs (in case some members were deleted but logs still exist)
  const { data: recentLogs } = await supabase
    .from('login_logs')
    .select('email')
    .order('logged_in_at', { ascending: false })
    .limit(100)
  if (recentLogs) {
    recentLogs.forEach((l) => emailSet.add(l.email.toLowerCase()))
  }

  emails.value = Array.from(emailSet).sort()

  await fetchLogs()
})
</script>

<template>
  <div class="logs-page">
    <div class="page-header">
      <h1 class="page-title">登入紀錄</h1>
    </div>

    <div class="log-controls">
      <div class="filter-group">
        <span class="filter-label">篩選使用者</span>
        <select v-model="selectedEmail" class="filter-select" @change="onEmailChange">
          <option value="ALL">所有使用者</option>
          <option v-for="email in emails" :key="email" :value="email">
            {{ email }}
          </option>
        </select>
      </div>
    </div>

    <div v-if="loading && logs.length === 0" class="state">載入中…</div>

    <div v-else-if="logs.length === 0" class="state">尚無登入紀錄</div>

    <template v-else>
      <div class="table-wrap">
        <table class="app-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>登入方式</th>
              <th>登入時間</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="log in logs" :key="log.id">
              <td>{{ log.email }}</td>
              <td>
                <span class="badge" :class="log.method">{{ methodLabel(log.method) }}</span>
              </td>
              <td class="time">{{ fmtTime(log.logged_in_at) }}</td>
            </tr>
          </tbody>
        </table>
      </div>

      <!-- Pagination Component -->
      <div v-if="totalPages > 1" class="pagination-bar">
        <BaseChip :disabled="page === 1" @click="changePage(page - 1)">上一頁</BaseChip>
        <span class="page-info">第 {{ page }} / {{ totalPages }} 頁 (共 {{ totalCount }} 筆)</span>
        <BaseChip :disabled="page >= totalPages" @click="changePage(page + 1)">下一頁</BaseChip>
      </div>
    </template>
  </div>
</template>

<style scoped>
.logs-page {
  max-width: 720px;
  margin: 0 auto;
  padding-bottom: 6rem;
}
.time {
  color: #a0aec0;
  font-variant-numeric: tabular-nums;
  font-size: 0.84rem;
}

.log-controls {
  display: flex;
  margin-bottom: 1.25rem;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.filter-label {
  font-size: 0.82rem;
  color: var(--text-muted);
  font-weight: 600;
}

.filter-select {
  padding: 0.45rem 2.25rem 0.45rem 0.75rem;
  border-radius: 8px;
  border: 1px solid var(--border-color);
  background: var(--bg-card);
  color: var(--text-primary);
  font-size: 0.88rem;
  outline: none;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml;charset=utf-8,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 24 24' fill='none' stroke='%23cbd5e0' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Cpolyline points='6 9 12 15 18 9'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 0.75rem center;
  background-size: 1rem;
  transition: border-color 0.15s;
}

.filter-select:focus {
  border-color: var(--color-google);
}

.pagination-bar {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
}

.page-info {
  font-size: 0.84rem;
  color: var(--text-muted);
}
</style>
