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
    <h1>登入紀錄</h1>

    <div v-if="loading" class="state">載入中…</div>

    <div v-else-if="logs.length === 0" class="state">尚無登入紀錄</div>

    <div v-else class="table-wrap">
      <table>
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
h1 { font-size: 1.3rem; font-weight: 700; margin-bottom: 1rem; }

.state { color: #718096; padding: 3rem 0; text-align: center; }

.table-wrap {
  background: #1a1f2e; border: 1px solid #2d3748; border-radius: 10px;
  overflow: hidden;
}

table { width: 100%; border-collapse: collapse; font-size: 0.88rem; }
thead { background: #232a3b; }
th { text-align: left; padding: 0.6rem 1rem; color: #a0aec0; font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.03em; }
td { padding: 0.55rem 1rem; border-top: 1px solid #2d3748; color: #e2e8f0; }
tr:hover td { background: #232a3b; }

.badge {
  display: inline-block; padding: 0.15rem 0.5rem; border-radius: 4px;
  font-size: 0.78rem; font-weight: 600;
}
.badge.google { background: #2b4c7e33; color: #63b3ed; }
.badge.email { background: #2d604533; color: #68d391; }

.time { color: #a0aec0; font-variant-numeric: tabular-nums; font-size: 0.84rem; }
</style>
