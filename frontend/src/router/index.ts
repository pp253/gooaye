import { createRouter, createWebHistory } from 'vue-router'
import { watch } from 'vue'
import { authReady, isAdmin } from '@/lib/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: () => import('@/views/DecisionHome.vue') },
    { path: '/episodes', component: () => import('@/views/EpisodeList.vue') },
    { path: '/episodes/:ep', component: () => import('@/views/EpisodeDetail.vue'), props: true },
    { path: '/stocks', component: () => import('@/views/StockList.vue') },
    { path: '/stocks/:id', component: () => import('@/views/StockDetail.vue'), props: true },
    { path: '/backtest', component: () => import('@/views/BacktestView.vue') },
    {
      path: '/login-logs',
      component: () => import('@/views/LoginLogsView.vue'),
      meta: { adminOnly: true },
    },
    {
      path: '/members',
      component: () => import('@/views/MembersView.vue'),
      meta: { adminOnly: true },
    },
  ],
})

function waitForAuthReady(): Promise<void> {
  if (authReady.value) return Promise.resolve()
  return new Promise((resolve) => {
    const unwatch = watch(authReady, (ready) => {
      if (ready) {
        unwatch()
        resolve()
      }
    })
  })
}

// 僅 UX 層的防呆（DB 端 RLS/RPC 已強制權限）：非 ADMIN 直接打網址也導回首頁。
// 直接打網址會整頁重載，initAuth() 的權限判斷是非同步的，
// 守衛要等 authReady 才能下判斷，否則會在 isAdmin 還沒算出來前誤判為非 admin。
router.beforeEach(async (to) => {
  if (!to.meta.adminOnly) return true
  await waitForAuthReady()
  if (!isAdmin.value) return '/'
  return true
})

export default router
