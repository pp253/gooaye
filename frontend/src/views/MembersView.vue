<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { supabase, fetchAllPaged } from '@/lib/supabase'
import { session } from '@/lib/auth'
import BaseInput from '@/components/BaseInput.vue'

interface AllowedEmail {
  email: string
  note: string | null
  role: 'admin' | 'user'
  created_at: string
}

interface LoginStat {
  count: number
  lastAt: string
}

interface InviteLink {
  token: string
  created_by: string
  created_at: string
  expires_at: string
  used_by: string | null
  used_at: string | null
}

const members = ref<AllowedEmail[]>([])
const loading = ref(true)
const newEmail = ref('')
const submitting = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

const links = ref<InviteLink[]>([])
const linksLoading = ref(true)
const expiresDays = ref(7)
const generating = ref(false)
const linkErrorMsg = ref('')
const generatedUrl = ref('')
const copyOk = ref(false)

function fmtTime(iso: string) {
  return new Date(iso).toLocaleString('zh-TW', {
    timeZone: 'Asia/Taipei',
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit',
  })
}

function linkStatus(l: InviteLink): { label: string; cls: string } {
  if (l.used_at) return { label: '已使用', cls: 'used' }
  if (new Date(l.expires_at) < new Date()) return { label: '已過期', cls: 'expired' }
  return { label: '待使用', cls: 'pending' }
}

async function loadLinks() {
  linksLoading.value = true
  const { data } = await supabase
    .from('invite_links')
    .select('token, created_by, created_at, expires_at, used_by, used_at')
    .order('created_at', { ascending: false })
  links.value = data ?? []
  linksLoading.value = false
}

async function generateLink() {
  linkErrorMsg.value = ''
  generatedUrl.value = ''
  copyOk.value = false
  generating.value = true

  const { data, error } = await supabase.rpc('create_invite_link', {
    expires_days: expiresDays.value,
  })
  generating.value = false

  if (error || !data?.[0]) {
    linkErrorMsg.value = error?.message ?? '產生連結失敗'
    return
  }
  generatedUrl.value = `${window.location.origin}/invite/${data[0].token}`
  await loadLinks()
}

async function copyLink() {
  if (!generatedUrl.value) return
  await navigator.clipboard.writeText(generatedUrl.value)
  copyOk.value = true
}

async function revokeLink(token: string) {
  if (!confirm('確定要撤銷這個尚未使用的邀請連結？')) return
  linkErrorMsg.value = ''
  const { error } = await supabase.rpc('revoke_invite_link', { target_token: token })
  if (error) {
    linkErrorMsg.value = error.message
    return
  }
  await loadLinks()
}

const loginStats = ref<Record<string, LoginStat>>({})

function loginStatOf(email: string): LoginStat {
  return loginStats.value[email.toLowerCase()] ?? { count: 0, lastAt: '' }
}

async function loadLoginStats() {
  const rows = await fetchAllPaged<{ email: string; logged_in_at: string }>((offset, limit) =>
    supabase
      .from('login_logs')
      .select('email, logged_in_at')
      .range(offset, offset + limit - 1),
  )
  const stats: Record<string, LoginStat> = {}
  for (const r of rows) {
    const email = r.email.toLowerCase()
    const cur = stats[email]
    if (!cur) {
      stats[email] = { count: 1, lastAt: r.logged_in_at }
    } else {
      cur.count += 1
      if (r.logged_in_at > cur.lastAt) cur.lastAt = r.logged_in_at
    }
  }
  loginStats.value = stats
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

onMounted(() => {
  loadMembers()
  loadLinks()
  loadLoginStats()
})
</script>

<template>
  <div class="members-page">
    <div class="page-header">
      <h1 class="page-title">成員管理</h1>
    </div>
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
            <th>登入次數</th>
            <th>上次登入時間</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="m in members" :key="m.email">
            <td>{{ m.email }}</td>
            <td><span class="badge" :class="m.role">{{ m.role === 'admin' ? 'ADMIN' : 'USER' }}</span></td>
            <td class="note">{{ m.note }}</td>
            <td class="time">{{ fmtTime(m.created_at) }}</td>
            <td class="time">{{ loginStatOf(m.email).count }}</td>
            <td class="time">{{ loginStatOf(m.email).lastAt ? fmtTime(loginStatOf(m.email).lastAt) : '從未登入' }}</td>
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

    <hr class="divider" />

    <h2 class="section-title">邀請連結</h2>
    <p class="sub">產生一次性連結，任何人用 Google 登入並點開即可加入；連結用過一次即失效，預設 7 天過期。</p>

    <form class="invite-form" @submit.prevent="generateLink">
      <label class="days-label">
        天數
        <input v-model.number="expiresDays" type="number" min="1" max="90" class="days-input" />
      </label>
      <button type="submit" :disabled="generating">
        {{ generating ? '產生中…' : '產生邀請連結' }}
      </button>
    </form>
    <p v-if="linkErrorMsg" class="error">{{ linkErrorMsg }}</p>

    <div v-if="generatedUrl" class="generated-box">
      <input class="generated-input" :value="generatedUrl" readonly @click="($event.target as HTMLInputElement).select()" />
      <button class="copy-btn" @click="copyLink">{{ copyOk ? '已複製' : '複製' }}</button>
    </div>

    <div v-if="linksLoading" class="state">載入中…</div>
    <div v-else-if="links.length === 0" class="state">尚無邀請連結</div>

    <div v-else class="table-wrap">
      <table class="app-table">
        <thead>
          <tr>
            <th>狀態</th>
            <th>建立者</th>
            <th>建立時間</th>
            <th>過期時間</th>
            <th>使用者</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="l in links" :key="l.token">
            <td><span class="badge" :class="linkStatus(l).cls">{{ linkStatus(l).label }}</span></td>
            <td class="note">{{ l.created_by }}</td>
            <td class="time">{{ fmtTime(l.created_at) }}</td>
            <td class="time">{{ fmtTime(l.expires_at) }}</td>
            <td class="note">{{ l.used_by ?? '—' }}</td>
            <td>
              <button v-if="!l.used_at" class="revoke" @click="revokeLink(l.token)">撤銷</button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<style scoped>
.members-page { max-width: 1100px; margin: 0 auto; padding-bottom: 6rem; }
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

.divider { border: none; border-top: 1px solid #2d3748; margin: 2rem 0 1.5rem; }
.section-title { font-size: 1.05rem; font-weight: 700; margin: 0 0 0.4rem; }

.days-label {
  display: flex; align-items: center; gap: 0.5rem;
  color: #a0aec0; font-size: 0.85rem; white-space: nowrap;
}
.days-input {
  width: 4.5rem; padding: 0.45rem 0.5rem; border-radius: 6px;
  border: 1px solid #4a5568; background: #1a1f2e; color: #e2e8f0; font-size: 0.88rem;
}

.generated-box { display: flex; gap: 0.6rem; margin-bottom: 1.2rem; }
.generated-input {
  flex: 1; padding: 0.55rem 0.7rem; border-radius: 8px;
  border: 1px solid #4a5568; background: #1a1f2e; color: #9ae6b4;
  font-size: 0.82rem; font-family: monospace;
}
.copy-btn {
  padding: 0.55rem 1rem; border-radius: 8px; border: none; cursor: pointer;
  background: #2d3748; color: #e2e8f0; font-weight: 600; font-size: 0.85rem;
}
.copy-btn:hover { background: #374151; }

.badge.pending { background: rgba(99, 179, 237, 0.18); color: #63b3ed; }
.badge.used { background: rgba(154, 230, 180, 0.15); color: #68d391; }
.badge.expired { background: rgba(252, 129, 129, 0.15); color: #fc8181; }
</style>
