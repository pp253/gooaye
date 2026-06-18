<template>
  <div class="app">
    <nav class="nav">
      <span class="nav-brand">股癌追蹤器</span>
      <RouterLink to="/" class="home">決策面板</RouterLink>
      <RouterLink to="/stocks">個股追蹤</RouterLink>
      <RouterLink to="/episodes">集數列表</RouterLink>
    </nav>
    <main class="main">
      <RouterView />
    </main>
  </div>
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

.main { flex: 1; padding: 2rem; max-width: 1100px; margin: 0 auto; width: 100%; }
</style>
