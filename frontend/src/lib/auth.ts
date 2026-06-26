import { ref } from 'vue'
import type { Session } from '@supabase/supabase-js'
import { supabase } from './supabase'

export const session = ref<Session | null>(null)
export const allowed = ref<boolean | null>(null) // null=檢查中, true=白名單, false=未登入或無權限
export const isAdmin = ref(false) // 是否為 ADMIN（只有 pp.pp253@gmail.com 預設為 ADMIN）
export const authReady = ref(false)
export const inviteError = ref<string | null>(null) // 邀請連結消費失敗時的提示訊息

const INVITE_TOKEN_KEY = 'gooaye_pending_invite_token'

/** /invite/:token 進站時呼叫，先把 token 存起來，OAuth 轉跳回來後才消費 */
export function storePendingInviteToken(token: string): void {
  localStorage.setItem(INVITE_TOKEN_KEY, token)
}

/**
 * /invite/:token 進站時立即檢查連結是否還有效（不需登入即可知道），
 * 過期/已使用/不存在則直接顯示提示，不必等使用者點完 Google 登入才發現。
 */
export async function precheckInviteToken(token: string): Promise<void> {
  const { data, error } = await supabase.rpc('is_invite_link_valid', { target_token: token })
  if (error || data !== true) {
    inviteError.value = '此邀請連結已失效、已過期，或已被使用，請聯絡管理員重新邀請。'
    localStorage.removeItem(INVITE_TOKEN_KEY)
    return
  }
  storePendingInviteToken(token)
}

/** 消費本機暫存的邀請連結 token；回傳是否成功加入白名單 */
async function consumePendingInviteToken(): Promise<boolean> {
  const token = localStorage.getItem(INVITE_TOKEN_KEY)
  if (!token) return false
  localStorage.removeItem(INVITE_TOKEN_KEY)

  const { data, error } = await supabase.rpc('accept_invite_link', { target_token: token })
  if (error || data !== true) {
    inviteError.value = '邀請連結已失效、已過期，或已被使用，請聯絡管理員重新邀請。'
    return false
  }
  return true
}

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
    // 已是既有成員：本機暫存的邀請連結 token 已無意義，清掉避免下次誤用
    localStorage.removeItem(INVITE_TOKEN_KEY)
  } else if (localStorage.getItem(INVITE_TOKEN_KEY)) {
    const accepted = await consumePendingInviteToken()
    if (accepted) {
      const { data: data2, error: error2 } = await supabase.rpc('is_allowed')
      allowed.value = !error2 && data2 === true
    }
  }

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
