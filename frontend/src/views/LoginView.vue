<script setup lang="ts">
import { ref } from 'vue'
import { signInWithGoogle, signOut } from '@/lib/auth'

const props = defineProps<{ deniedEmail?: string | null }>()

const errorMsg = ref('')
const loggingIn = ref(false)

const TICKER_SYMBOLS = [
  '2330', 'NVDA', 'TSM', '2454', 'AAPL', 'MRVL', '2317', 'AMD',
  '2327', 'ON', 'CRWD', 'TXN', '2603', 'VSH', '2382', 'CRM',
]

async function google() {
  errorMsg.value = ''
  loggingIn.value = true
  const { error } = await signInWithGoogle()
  if (error) {
    errorMsg.value = error.message
    loggingIn.value = false
  }
}
</script>

<template>
  <div class="login">
    <!-- 背景動態光暈 -->
    <div class="bg-glow glow-a" />
    <div class="bg-glow glow-b" />
    <div class="bg-glow glow-c" />

    <!-- 跑馬燈：股票代號裝飾，純視覺、非即時報價 -->
    <div class="ticker-tape" aria-hidden="true">
      <div class="ticker-track">
        <span v-for="(t, i) in [...TICKER_SYMBOLS, ...TICKER_SYMBOLS]" :key="i"
          :class="['ticker-item', i % 2 === 0 ? 'bull' : 'bear']">
          <span class="arrow">{{ i % 2 === 0 ? '▲' : '▼' }}</span>{{ t }}
        </span>
      </div>
    </div>

    <div class="card">
      <div class="logo-row">
        <span class="logo-glyph">📈</span>
        <h1 class="brand">股癌追蹤器</h1>
      </div>
      <p class="tagline">把孟恭的每一句「看多」，變成你的進場訊號</p>

      <!-- 已登入但不在白名單 -->
      <template v-if="props.deniedEmail">
        <div class="denied-box">
          <p class="denied">此帳號（{{ props.deniedEmail }}）沒有存取權限。</p>
          <p class="hint">請用獲授權的帳號登入，或聯絡管理員邀請你加入。</p>
        </div>
        <button class="btn ghost" @click="signOut">登出並改用其他帳號</button>
      </template>

      <!-- 未登入 -->
      <template v-else>
        <div class="feature-row">
          <span class="feature-chip">⚡ 訊號分數</span>
          <span class="feature-chip">🎯 跟單回測</span>
          <span class="feature-chip">🔔 即時提及</span>
        </div>

        <button class="btn google" :disabled="loggingIn" @click="google">
          <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.6l6.7-6.7C35.6 2.6 30.2 0 24 0 14.6 0 6.4 5.4 2.5 13.3l7.8 6c1.9-5.6 7.1-9.8 13.7-9.8z"/><path fill="#4285F4" d="M46.1 24.6c0-1.6-.1-3.1-.4-4.6H24v9h12.4c-.5 2.9-2.1 5.3-4.6 7l7.1 5.5c4.2-3.9 6.6-9.6 6.6-16.9z"/><path fill="#FBBC05" d="M10.3 28.3c-.5-1.4-.7-2.9-.7-4.3s.3-3 .7-4.3l-7.8-6C.9 16.9 0 20.3 0 24s.9 7.1 2.5 10.3l7.8-6z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.1-5.5c-2 1.3-4.5 2.1-8.8 2.1-6.6 0-11.8-4.2-13.7-9.8l-7.8 6C6.4 42.6 14.6 48 24 48z"/></svg>
          {{ loggingIn ? '跳轉登入中…' : '使用 Google 登入' }}
        </button>

        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>

        <p class="footnote">僅限受邀 email；登入即代表同意僅供個人決策參考使用</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.login {
  min-height: 100svh;
  display: flex; align-items: center; justify-content: center;
  padding: 2rem;
  position: relative;
  overflow: hidden;
  background: radial-gradient(ellipse at 50% -10%, #16243f 0%, #0f1117 55%);
}

/* ── 背景光暈：緩慢漂浮 ───────────────────────────── */
.bg-glow {
  position: absolute; border-radius: 50%; filter: blur(70px);
  opacity: 0.45; pointer-events: none;
  animation: drift 16s ease-in-out infinite alternate;
}
.glow-a { width: 420px; height: 420px; background: #2b6cb0; top: -10%; left: -8%; }
.glow-b { width: 380px; height: 380px; background: #38a169; top: 50%; right: -10%; animation-duration: 20s; animation-delay: -4s; }
.glow-c { width: 320px; height: 320px; background: #805ad5; bottom: -12%; left: 30%; animation-duration: 24s; animation-delay: -9s; }

@keyframes drift {
  0%   { transform: translate(0, 0) scale(1); }
  100% { transform: translate(40px, 30px) scale(1.12); }
}

/* ── 跑馬燈 ──────────────────────────────────────── */
.ticker-tape {
  position: absolute; top: 0; left: 0; width: 100%;
  overflow: hidden; padding: 0.5rem 0;
  background: rgba(26, 31, 46, 0.55);
  border-bottom: 1px solid rgba(45, 55, 72, 0.6);
  backdrop-filter: blur(4px);
  mask-image: linear-gradient(90deg, transparent, #000 8%, #000 92%, transparent);
}
.ticker-track {
  display: flex; gap: 2rem; white-space: nowrap; width: max-content;
  animation: scroll-left 32s linear infinite;
}
@keyframes scroll-left {
  from { transform: translateX(0); }
  to   { transform: translateX(-50%); }
}
.ticker-item { font-size: 0.78rem; font-weight: 600; font-family: monospace; letter-spacing: 0.02em; }
.ticker-item.bull { color: #68d391; }
.ticker-item.bear { color: #fc8181; }
.arrow { display: inline-block; margin-right: 0.3rem; font-size: 0.7rem; }

/* ── 卡片：玻璃擬態 + 進場動畫 ─────────────────────── */
.card {
  position: relative; z-index: 1;
  width: 100%; max-width: 380px;
  background: rgba(26, 31, 46, 0.72);
  border: 1px solid rgba(99, 179, 237, 0.25);
  border-radius: 16px; padding: 2.25rem 2rem;
  display: flex; flex-direction: column; gap: 1.1rem; text-align: center;
  backdrop-filter: blur(14px);
  box-shadow: 0 0 0 1px rgba(99, 179, 237, 0.06), 0 20px 60px -20px rgba(0, 0, 0, 0.6);
  animation: card-in 0.55s cubic-bezier(0.16, 1, 0.3, 1) both, glow-pulse 4.5s ease-in-out 0.6s infinite;
}

@keyframes card-in {
  from { opacity: 0; transform: translateY(18px) scale(0.97); }
  to   { opacity: 1; transform: translateY(0) scale(1); }
}
@keyframes glow-pulse {
  0%, 100% { box-shadow: 0 0 0 1px rgba(99, 179, 237, 0.06), 0 20px 60px -20px rgba(0, 0, 0, 0.6); }
  50%      { box-shadow: 0 0 0 1px rgba(99, 179, 237, 0.18), 0 20px 70px -16px rgba(43, 108, 176, 0.45); }
}

.logo-row { display: flex; align-items: center; justify-content: center; gap: 0.5rem; }
.logo-glyph { font-size: 1.6rem; animation: float 3s ease-in-out infinite; }
@keyframes float {
  0%, 100% { transform: translateY(0); }
  50%      { transform: translateY(-4px); }
}

.brand {
  font-size: 1.5rem; font-weight: 800; margin: 0;
  background: linear-gradient(90deg, #63b3ed, #9ae6b4 60%, #63b3ed);
  background-size: 200% auto;
  -webkit-background-clip: text; background-clip: text; color: transparent;
  animation: shine 5s linear infinite;
}
@keyframes shine {
  to { background-position: 200% center; }
}

.tagline { color: #a0aec0; font-size: 0.88rem; margin: -0.4rem 0 0.2rem; line-height: 1.5; }

.feature-row { display: flex; flex-wrap: wrap; justify-content: center; gap: 0.5rem; }
.feature-chip {
  font-size: 0.76rem; font-weight: 600; color: #cbd5e0;
  background: rgba(45, 55, 72, 0.7); border: 1px solid rgba(99, 179, 237, 0.18);
  border-radius: 9999px; padding: 0.3rem 0.7rem; white-space: nowrap;
}

.btn {
  display: flex; align-items: center; justify-content: center; gap: 0.6rem;
  padding: 0.75rem 1rem; border-radius: 10px; border: none; cursor: pointer;
  font-size: 0.94rem; font-weight: 700;
  transition: background 0.15s, transform 0.15s, box-shadow 0.15s;
}
.btn.google { background: #fff; color: #1a202c; box-shadow: 0 6px 16px -6px rgba(0, 0, 0, 0.4); }
.btn.google:hover:not(:disabled) { background: #f1f5f9; transform: translateY(-2px); box-shadow: 0 10px 22px -8px rgba(0, 0, 0, 0.5); }
.btn.google:active:not(:disabled) { transform: translateY(0); }
.btn.google:disabled { opacity: 0.7; cursor: default; }
.btn.ghost { background: #2d3748; color: #e2e8f0; }
.btn.ghost:hover { background: #374151; }

.denied-box { display: flex; flex-direction: column; gap: 0.3rem; }
.denied { color: #fc8181; font-size: 0.95rem; font-weight: 600; margin: 0; }
.hint { color: #a0aec0; font-size: 0.82rem; margin: 0; }
.error { color: #fc8181; font-size: 0.82rem; margin: 0; }
.footnote { color: #4a5568; font-size: 0.72rem; margin: 0.2rem 0 0; line-height: 1.4; }

@media (prefers-reduced-motion: reduce) {
  .bg-glow, .ticker-track, .logo-glyph, .brand, .card { animation: none !important; }
}
</style>
