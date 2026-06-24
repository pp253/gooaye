import { createRouter, createWebHistory } from 'vue-router'
import DecisionHome from '@/views/DecisionHome.vue'
import EpisodeList from '@/views/EpisodeList.vue'
import EpisodeDetail from '@/views/EpisodeDetail.vue'
import StockList from '@/views/StockList.vue'
import StockDetail from '@/views/StockDetail.vue'
import BacktestView from '@/views/BacktestView.vue'
import LoginLogsView from '@/views/LoginLogsView.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', component: DecisionHome },
    { path: '/episodes', component: EpisodeList },
    { path: '/episodes/:ep', component: EpisodeDetail, props: true },
    { path: '/stocks', component: StockList },
    { path: '/stocks/:id', component: StockDetail, props: true },
    { path: '/backtest', component: BacktestView },
    { path: '/login-logs', component: LoginLogsView },
  ],
})
