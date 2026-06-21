<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { initAuth, authReady, session, allowed, signOut } from '@/lib/auth'
import LoginView from '@/views/LoginView.vue'

onMounted(initAuth)

const deniedEmail = computed(() =>
  session.value && allowed.value === false ? session.value.user.email ?? '' : null,
)
</script>

<template>
  <!-- 啟動檢查中 -->
  <div v-if="!authReady" class="boot">載入中 …</div>

  <!-- 已登入且在白名單 → 完整 app -->
  <div v-else-if="session && allowed" class="app">
    <nav class="nav">
      <span class="nav-brand">股癌追蹤器</span>
      <RouterLink to="/" class="home">決策面板</RouterLink>
      <RouterLink to="/stocks">個股追蹤</RouterLink>
      <RouterLink to="/backtest">回測</RouterLink>
      <RouterLink to="/episodes">集數列表</RouterLink>
      <button class="logout" @click="signOut">登出</button>
    </nav>
    <main class="main">
      <RouterView />
    </main>
  </div>

  <!-- 未登入 / 無權限 → 登入頁 -->
  <LoginView v-else :denied-email="deniedEmail" />
</template>

<style>
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  background: #0f1117;
  color: #e2e8f0;
  min-height: 100vh;
}

.app { display: flex; flex-direction: column; min-height: 100vh; }

.nav {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 0.75rem 2rem;
  background: #1a1f2e;
  border-bottom: 1px solid #2d3748;
  position: sticky; top: 0; z-index: 10;
}

.nav-brand { font-weight: 700; font-size: 1.1rem; color: #63b3ed; margin-right: auto; }

.boot { min-height: 100svh; display: flex; align-items: center; justify-content: center; color: #718096; }
.logout {
  margin-left: 0.5rem; background: #2d3748; color: #a0aec0; border: none;
  border-radius: 4px; padding: 0.3rem 0.7rem; font-size: 0.82rem; cursor: pointer;
}
.logout:hover { background: #374151; color: #e2e8f0; }

.nav a {
  color: #a0aec0;
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  transition: color 0.15s;
}
.nav a:hover,
.nav a.router-link-active:not(.home),
.nav a.home.router-link-exact-active { color: #e2e8f0; background: #2d3748; }

.main { flex: 1; padding: 1.5rem 2rem; width: 100%; }
</style>
