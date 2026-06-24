import { ref } from 'vue'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './supabase'

export const session = ref<Session | null>(null)
export const allowed = ref<boolean | null>(null) // null=檢查中, true=白名單, false=未登入或無權限
export const authReady = ref(false)

/** 呼叫 DB 的 is_allowed()，判斷目前登入者是否在白名單 */
async function refreshAllowed(): Promise<void> {
  if (!session.value) {
    allowed.value = false
    return
  }
  const { data, error } = await supabase.rpc('is_allowed')
  allowed.value = !error && data === true
}

/** 寫入 login_logs（best-effort，失敗不影響登入流程） */
async function recordLogin(s: Session): Promise<void> {
  const method = s.user.app_metadata?.provider ?? 'unknown'
  await supabase.from('login_logs').insert({
    user_id: s.user.id,
    email: s.user.email ?? '',
    method,
  }).then(undefined, () => {/* ignore */})
}

/** App 啟動時呼叫一次：取得 session + 訂閱變化 */
export async function initAuth(): Promise<void> {
  const { data } = await supabase.auth.getSession()
  session.value = data.session
  await refreshAllowed()
  authReady.value = true

  supabase.auth.onAuthStateChange(async (event, s) => {
    session.value = s
    await refreshAllowed()
    if (event === 'SIGNED_IN' && s) await recordLogin(s)
  })
}

export function signInWithGoogle() {
  return supabase.auth.signInWithOAuth({
    provider: 'google',
    options: { redirectTo: window.location.origin },
  })
}

export async function signOut(): Promise<void> {
  await supabase.auth.signOut()
}
