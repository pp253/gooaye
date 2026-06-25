import { ref } from 'vue'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './supabase'

export const session = ref<Session | null>(null)
export const allowed = ref<boolean | null>(null) // null=檢查中, true=白名單, false=未登入或無權限
export const isAdmin = ref(false) // 是否為 ADMIN（只有 pp.pp253@gmail.com 預設為 ADMIN）
export const authReady = ref(false)

/** 呼叫 DB 的 is_allowed() / is_admin()，判斷目前登入者的權限 */
async function refreshAllowed(): Promise<void> {
  if (!session.value) {
    allowed.value = false
    isAdmin.value = false
    return
  }
  const { data, error } = await supabase.rpc('is_allowed')
  allowed.value = !error && data === true

  if (allowed.value) {
    const { data: adminData, error: adminError } = await supabase.rpc('is_admin')
    isAdmin.value = !adminError && adminData === true
  } else {
    isAdmin.value = false
  }
}


/** App 啟動時呼叫一次：取得 session + 訂閱變化 */
export async function initAuth(): Promise<void> {
  const { data } = await supabase.auth.getSession()
  session.value = data.session
  await refreshAllowed()
  authReady.value = true

  supabase.auth.onAuthStateChange(async (_event, s) => {
    session.value = s
    await refreshAllowed()
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
