<script setup lang="ts">
import { ref } from 'vue'
import { signInWithGoogle, signOut } from '@/lib/auth'

const props = defineProps<{ deniedEmail?: string | null }>()

const errorMsg = ref('')

async function google() {
  errorMsg.value = ''
  const { error } = await signInWithGoogle()
  if (error) errorMsg.value = error.message
}
</script>

<template>
  <div class="login">
    <div class="card">
      <h1 class="brand">股癌追蹤器</h1>

      <!-- 已登入但不在白名單 -->
      <template v-if="props.deniedEmail">
        <p class="denied">此帳號（{{ props.deniedEmail }}）沒有存取權限。</p>
        <p class="hint">請用獲授權的帳號登入。</p>
        <button class="btn ghost" @click="signOut">登出並改用其他帳號</button>
      </template>

      <!-- 未登入 -->
      <template v-else>
        <p class="sub">請登入以使用</p>

        <button class="btn google" @click="google">
          <svg width="18" height="18" viewBox="0 0 48 48"><path fill="#EA4335" d="M24 9.5c3.5 0 6.6 1.2 9 3.6l6.7-6.7C35.6 2.6 30.2 0 24 0 14.6 0 6.4 5.4 2.5 13.3l7.8 6c1.9-5.6 7.1-9.8 13.7-9.8z"/><path fill="#4285F4" d="M46.1 24.6c0-1.6-.1-3.1-.4-4.6H24v9h12.4c-.5 2.9-2.1 5.3-4.6 7l7.1 5.5c4.2-3.9 6.6-9.6 6.6-16.9z"/><path fill="#FBBC05" d="M10.3 28.3c-.5-1.4-.7-2.9-.7-4.3s.3-3 .7-4.3l-7.8-6C.9 16.9 0 20.3 0 24s.9 7.1 2.5 10.3l7.8-6z"/><path fill="#34A853" d="M24 48c6.5 0 11.9-2.1 15.9-5.8l-7.1-5.5c-2 1.3-4.5 2.1-8.8 2.1-6.6 0-11.8-4.2-13.7-9.8l-7.8 6C6.4 42.6 14.6 48 24 48z"/></svg>
          使用 Google 登入
        </button>

        <p v-if="errorMsg" class="error">{{ errorMsg }}</p>
      </template>
    </div>
  </div>
</template>

<style scoped>
.login { min-height: 100svh; display: flex; align-items: center; justify-content: center; padding: 2rem; }
.card {
  width: 100%; max-width: 360px; background: #1a1f2e; border: 1px solid #2d3748;
  border-radius: 12px; padding: 2rem; display: flex; flex-direction: column; gap: 1rem; text-align: center;
}
.brand { font-size: 1.4rem; font-weight: 700; color: #63b3ed; margin: 0; }
.sub { color: #a0aec0; font-size: 0.9rem; margin: 0; }

.btn {
  display: flex; align-items: center; justify-content: center; gap: 0.6rem;
  padding: 0.65rem 1rem; border-radius: 8px; border: none; cursor: pointer;
  font-size: 0.92rem; font-weight: 600;
}
.btn.google { background: #fff; color: #1a202c; }
.btn.google:hover { background: #f1f5f9; }
.btn.ghost { background: #2d3748; color: #e2e8f0; }
.btn.ghost:hover { background: #374151; }

.denied { color: #fc8181; font-size: 0.95rem; font-weight: 600; }
.hint { color: #a0aec0; font-size: 0.82rem; margin: 0; }
.error { color: #fc8181; font-size: 0.82rem; }
</style>
