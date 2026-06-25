import { createRouter, createWebHistory } from 'vue-router'
import { watch } from 'vue'
import DecisionHome from '@/views/DecisionHome.vue'
import EpisodeList from '@/views/EpisodeList.vue'
import EpisodeDetail from '@/views/EpisodeDetail.vue'
import StockList from '@/views/StockList.vue'
import StockDetail from '@/views/StockDetail.vue'
import BacktestView from '@/views/BacktestView.vue'
import LoginLogsView from '@/views/LoginLogsView.vue'
import MembersView from '@/views/MembersView.vue'
import { authReady, isAdmin } from '@/lib/auth'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DecisionHome },
    { path: '/episodes', component: EpisodeList },
    { path: '/episodes/:ep', component: EpisodeDetail, props: true },
    { path: '/stocks', component: StockList },
    { path: '/stocks/:id', component: StockDetail, props: true },
    { path: '/backtest', component: BacktestView },
    { path: '/login-logs', component: LoginLogsView, meta: { adminOnly: true } },
    { path: '/members', component: MembersView, meta: { adminOnly: true } },
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
