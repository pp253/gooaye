<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase } from '@/lib/supabase'
import { session } from '@/lib/auth'
import BaseInput from '@/components/BaseInput.vue'

interface AllowedEmail {
  email: string
  note: string | null
  role: 'admin' | 'user'
  created_at: string
}

const members = ref<AllowedEmail[]>([])
const loading = ref(true)
const newEmail = ref('')
const submitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

async function loadMembers() {
  loading.value = true
  const { data } = await supabase
    .from('allowed_emails')
    .select('email, note, role, created_at')
    .order('created_at', { ascending: false })
  members.value = data ?? []
  loading.value = false
}

async function invite() {
  errorMsg.value = ''
  successMsg.value = ''
  const email = newEmail.value.trim()
  if (!email) return

  submitting.value = true
  const { error } = await supabase.rpc('invite_email', { target_email: email })
  submitting.value = false

  if (error) {
    errorMsg.value = error.message
    return
  }
  successMsg.value = `已邀請 ${email}`
  newEmail.value = ''
  await loadMembers()
}

async function revoke(email: string) {
  if (!confirm(`確定要移除 ${email} 的存取權限？`)) return
  errorMsg.value = ''
  const { error } = await supabase.rpc('revoke_email', { target_email: email })
  if (error) {
    errorMsg.value = error.message
    return
  }
  await loadMembers()
}

onMounted(loadMembers)
</script>

<template>
  <div class="members-page">
    <h1 class="page-title">成員管理</h1>
    <p class="sub">邀請其他 email 加入白名單，才能登入並查看資料。</p>

    <form class="invite-form" @submit.prevent="invite">
      <BaseInput
        v-model="newEmail"
        type="email"
        class="invite-input"
        placeholder="輸入要邀請的 email"
        required
      />
      <button type="submit" :disabled="submitting">
        {{ submitting ? '邀請中…' : '邀請' }}
      </button>
    </form>
    <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
    <p v-if="successMsg" class="success">{{ successMsg }}</p>

    <div v-if="loading" class="state">載入中…</div>
    <div v-else-if="members.length === 0" class="state">尚無成員</div>

    <div v-else class="table-wrap">
      <table class="app-table">
        <thead>
          <tr>
            <th>Email</th>
            <th>角色</th>
            <th>備註</th>
            <th>加入時間</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in members" :key="m.email">
            <td>{{ m.email }}</td>
            <td><span class="badge" :class="m.role">{{ m.role === 'admin' ? 'ADMIN' : 'USER' }}</span></td>
            <td class="note">{{ m.note }}</td>
            <td class="time">{{ fmtTime(m.created_at) }}</td>
            <td>
              <button
                v-if="m.email !== session?.user.email?.toLowerCase()"
                class="revoke"
                @click="revoke(m.email)"
              >
                移除
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.members-page { max-width: 720px; margin: 0 auto; }
.sub { color: #a0aec0; font-size: 0.88rem; margin-bottom: 1.2rem; }

.invite-form { display: flex; gap: 0.6rem; margin-bottom: 0.8rem; }
.invite-form .invite-input { flex: 1; margin-bottom: 0; }
.invite-form button {
  padding: 0.55rem 1.1rem; border-radius: 8px; border: none; cursor: pointer;
  background: #3182ce; color: #fff; font-weight: 600; font-size: 0.88rem;
}
.invite-form button:disabled { background: #2c5282; cursor: default; }
.invite-form button:not(:disabled):hover { background: #2b6cb0; }

.error { color: #fc8181; font-size: 0.85rem; margin-bottom: 0.8rem; }
.success { color: #68d391; font-size: 0.85rem; margin-bottom: 0.8rem; }

.note { color: #a0aec0; font-size: 0.84rem; }
.time { color: #a0aec0; font-variant-numeric: tabular-nums; font-size: 0.84rem; }

.revoke {
  background: none; border: 1px solid #4a5568; color: #fc8181;
  border-radius: 6px; padding: 0.2rem 0.6rem; font-size: 0.78rem; cursor: pointer;
}
.revoke:hover { background: #2d3748; }
</style>
