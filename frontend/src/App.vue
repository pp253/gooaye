<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { initAuth, authReady, session, allowed, isAdmin, signOut } from '@/lib/auth'
import LoginView from '@/views/LoginView.vue'

onMounted(initAuth)

const deniedEmail = computed(() =>
  session.value && allowed.value === false ? session.value.user.email ?? '' : null,
)

const menuOpen = ref(false)
function closeMenu() { menuOpen.value = false }
</script>

<template>
  <!-- 啟動檢查中 -->
  <div v-if="!authReady" class="boot">載入中 …</div>

  <!-- 已登入且在白名單 → 完整 app -->
  <div v-else-if="session && allowed" class="app">
    <nav class="nav">
      <span class="nav-brand">股癌追蹤器</span>

      <!-- 桌面版連結 -->
      <div class="nav-links">
        <RouterLink to="/" class="home">決策面板</RouterLink>
        <RouterLink to="/stocks">個股追蹤</RouterLink>
        <RouterLink to="/backtest">回測</RouterLink>
        <RouterLink to="/episodes">集數列表</RouterLink>
        <RouterLink v-if="isAdmin" to="/login-logs">登入紀錄</RouterLink>
        <RouterLink v-if="isAdmin" to="/members">成員管理</RouterLink>
        <button class="logout" @click="signOut">登出</button>
      </div>

      <!-- 手機版漢堡按鈕 -->
      <button class="hamburger" :class="{ open: menuOpen }" @click="menuOpen = !menuOpen"
        aria-label="選單">
        <span /><span /><span />
      </button>
    </nav>

    <!-- 手機版下拉選單 -->
    <div v-if="menuOpen" class="mobile-menu" @click="closeMenu">
      <RouterLink to="/" class="home mm-link">決策面板</RouterLink>
      <RouterLink to="/stocks" class="mm-link">個股追蹤</RouterLink>
      <RouterLink to="/backtest" class="mm-link">回測</RouterLink>
      <RouterLink to="/episodes" class="mm-link">集數列表</RouterLink>
      <RouterLink v-if="isAdmin" to="/login-logs" class="mm-link">登入紀錄</RouterLink>
      <RouterLink v-if="isAdmin" to="/members" class="mm-link">成員管理</RouterLink>
      <button class="mm-link mm-logout" @click="signOut">登出</button>
    </div>

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

/* ── Nav ────────────────────────────────────────── */
.nav {
  display: flex;
  align-items: center;
  padding: 0 1.25rem;
  height: 52px;
  background: #1a1f2e;
  border-bottom: 1px solid #2d3748;
  position: sticky; top: 0; z-index: 20;
}

.nav-brand {
  font-weight: 700; font-size: 1.05rem; color: #63b3ed;
  margin-right: auto; white-space: nowrap;
}

.nav-links {
  display: flex; align-items: center; gap: 0.25rem;
}

.nav a {
  color: #a0aec0;
  text-decoration: none;
  font-size: 0.9rem;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  transition: color 0.15s, background 0.15s;
  white-space: nowrap;
}
.nav a:hover,
.nav a.router-link-active:not(.home),
.nav a.home.router-link-exact-active { color: #e2e8f0; background: #2d3748; }

.logout {
  margin-left: 0.25rem; background: #2d3748; color: #a0aec0; border: none;
  border-radius: 4px; padding: 0.3rem 0.7rem; font-size: 0.82rem; cursor: pointer;
  white-space: nowrap;
}
.logout:hover { background: #374151; color: #e2e8f0; }

/* ── 漢堡按鈕（手機才顯示） ────────────────────── */
.hamburger {
  display: none;
  flex-direction: column; justify-content: center; gap: 5px;
  background: none; border: none; cursor: pointer;
  padding: 0.4rem; margin-left: 0.5rem;
  width: 36px; height: 36px;
}
.hamburger span {
  display: block; height: 2px; border-radius: 2px;
  background: #a0aec0;
  transition: transform 0.2s, opacity 0.2s;
}
.hamburger.open span:nth-child(1) { transform: translateY(7px) rotate(45deg); }
.hamburger.open span:nth-child(2) { opacity: 0; }
.hamburger.open span:nth-child(3) { transform: translateY(-7px) rotate(-45deg); }

/* ── 手機版下拉選單 ─────────────────────────────── */
.mobile-menu {
  display: none;
  flex-direction: column;
  background: #1a1f2e;
  border-bottom: 1px solid #2d3748;
  padding: 0.5rem 0;
  position: sticky; top: 52px; z-index: 19;
}
.mm-link {
  display: block; padding: 0.75rem 1.5rem;
  color: #a0aec0; text-decoration: none; font-size: 0.95rem;
  border: none; background: none; cursor: pointer; text-align: left; width: 100%;
  transition: background 0.15s, color 0.15s;
}
.mm-link:hover,
.mm-link.router-link-active:not(.home),
.mm-link.home.router-link-exact-active { background: #2d3748; color: #e2e8f0; }
.mm-logout { color: #fc8181; }

/* ── Main ───────────────────────────────────────── */
.boot { min-height: 100svh; display: flex; align-items: center; justify-content: center; color: #718096; }
.main { flex: 1; padding: 1.5rem 2rem; width: 100%; }

/* ── RWD ────────────────────────────────────────── */
@media (max-width: 640px) {
  .nav-links { display: none; }
  .hamburger { display: flex; }
  .mobile-menu { display: flex; }
  .main { padding: 1rem 1rem; }
}
</style>
