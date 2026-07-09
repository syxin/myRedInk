<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-icon">
        <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <rect x="3" y="11" width="18" height="11" rx="2" ry="2"></rect>
          <path d="M7 11V7a5 5 0 0 1 10 0v4"></path>
        </svg>
      </div>
      <h1 class="login-title">红墨 AI图文生成器</h1>
      <p class="login-subtitle">请输入访问密码</p>

      <form @submit.prevent="handleLogin">
        <input
          v-model="password"
          type="password"
          class="login-input"
          placeholder="访问密码"
          :disabled="loading"
          autofocus
          @keyup.enter="handleLogin"
        />

        <div v-if="error" class="login-error">{{ error }}</div>

        <button type="submit" class="login-btn" :disabled="loading || !password">
          <span v-if="loading" class="spinner"></span>
          {{ loading ? '验证中...' : '进入' }}
        </button>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { login } from '../api/auth'

const router = useRouter()
const route = useRoute()

const password = ref('')
const loading = ref(false)
const error = ref('')

async function handleLogin() {
  if (!password.value || loading.value) return

  loading.value = true
  error.value = ''

  try {
    const result = await login(password.value)
    if (result.success) {
      const redirect = (route.query.redirect as string) || '/'
      router.replace(redirect)
    } else {
      error.value = result.error || '密码错误'
    }
  } catch (e: any) {
    error.value = e.message || '网络错误，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--bg-body);
  padding: 20px;
}

.login-card {
  background: var(--bg-card);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-md);
  padding: 48px 40px;
  width: 100%;
  max-width: 400px;
  text-align: center;
}

.login-icon {
  width: 72px;
  height: 72px;
  margin: 0 auto 24px;
  border-radius: 50%;
  background: var(--primary-light);
  color: var(--primary);
  display: flex;
  align-items: center;
  justify-content: center;
}

.login-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-main);
  margin: 0 0 8px;
}

.login-subtitle {
  font-size: 14px;
  color: var(--text-sub);
  margin: 0 0 32px;
}

.login-input {
  width: 100%;
  padding: 14px 16px;
  font-size: 15px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-sm);
  outline: none;
  transition: border-color 0.2s;
  box-sizing: border-box;
}

.login-input:focus {
  border-color: var(--primary);
}

.login-input:disabled {
  opacity: 0.6;
}

.login-error {
  color: var(--primary);
  font-size: 13px;
  margin: 12px 0;
  text-align: left;
}

.login-btn {
  width: 100%;
  padding: 14px;
  font-size: 15px;
  font-weight: 600;
  color: white;
  background: var(--primary);
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background 0.2s;
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

.login-btn:hover:not(:disabled) {
  background: var(--primary-hover);
}

.login-btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinner {
  display: inline-block;
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
