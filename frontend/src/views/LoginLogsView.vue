<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase } from '@/lib/supabase'

interface LoginLog {
  id: number
  email: string
  method: string
  logged_in_at: string
}

const logs = ref<LoginLog[]>([])
const loading = ref(true)

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function methodLabel(m: string) {
  if (m === 'google') return 'Google'
  if (m === 'email') return 'Email'
  return m
}

onMounted(async () => {
  const { data } = await supabase
    .from('login_logs')
    .select('id, email, method, logged_in_at')
    .order('logged_in_at', { ascending: false })
    .limit(100)
  logs.value = data ?? []
  loading.value = false
})
</script>

<template>
  <div class="logs-page">
    <h1 class="page-title">登入紀錄</h1>

    <div v-if="loading" class="state">載入中…</div>

    <div v-else-if="logs.length === 0" class="state">尚無登入紀錄</div>

    <div v-else class="table-wrap">
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
  </div>
</template>

<style scoped>
.logs-page { max-width: 720px; margin: 0 auto; }
.time { color: #a0aec0; font-variant-numeric: tabular-nums; font-size: 0.84rem; }
</style>
