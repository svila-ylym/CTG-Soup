<template>
  <main class="flex min-h-screen items-center justify-center bg-white px-4 py-12 dark:bg-black">
    <div class="w-full max-w-md">
      <div class="text-center">
        <p class="text-sm font-semibold text-blue-600 dark:text-blue-400">邮箱验证完成后</p>
        <h1 class="mt-2 text-3xl font-bold text-slate-900 dark:text-white">设置新密码</h1>
        <p class="mt-3 text-sm leading-6 text-slate-500">密码至少 8 位，并同时包含大写字母、小写字母和数字。</p>
      </div>

      <form class="mt-8 space-y-5 border-y border-slate-200 py-8 dark:border-neutral-800 sm:px-8" @submit.prevent="submit">
        <div>
          <label for="new-password" class="block text-sm font-medium text-slate-700 dark:text-slate-300">新密码</label>
          <input id="new-password" v-model="password" class="form-control mt-1" type="password" autocomplete="new-password" minlength="8" maxlength="72" required placeholder="请输入新密码">
        </div>
        <div>
          <label for="confirm-password" class="block text-sm font-medium text-slate-700 dark:text-slate-300">确认新密码</label>
          <input id="confirm-password" v-model="confirmation" class="form-control mt-1" type="password" autocomplete="new-password" minlength="8" maxlength="72" required placeholder="再次输入新密码">
        </div>
        <p v-if="error" class="break-words rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-300">{{ error }}</p>
        <button class="btn-primary w-full" type="submit" :disabled="loading || !token">
          {{ loading ? '正在重置…' : '确认重置密码' }}
        </button>
        <router-link to="/forgot-password" class="block text-center text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">重新申请重置链接</router-link>
      </form>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { authApi } from '@/api/auth'
import { extractApiError } from '@/utils/auth'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const token = computed(() => typeof route.query.token === 'string' ? route.query.token : '')
const password = ref('')
const confirmation = ref('')
const loading = ref(false)
const error = ref(token.value ? '' : '重置链接缺少验证信息，请重新申请。')

function validatePassword(value: string): string {
  if (value.length < 8) return '密码长度必须至少为 8 位'
  if (!/[A-Z]/.test(value)) return '密码必须包含大写字母'
  if (!/[a-z]/.test(value)) return '密码必须包含小写字母'
  if (!/\d/.test(value)) return '密码必须包含数字'
  if (new TextEncoder().encode(value).length > 72) return '密码不能超过 72 字节'
  if (value !== confirmation.value) return '两次输入的密码不一致'
  return ''
}

async function submit() {
  if (!token.value || loading.value) return
  error.value = validatePassword(password.value)
  if (error.value) return
  loading.value = true
  try {
    await authApi.resetPassword(token.value, password.value)
    authStore.logout()
    await router.replace({ name: 'Login', query: { reset: 'success' } })
  } catch (cause) {
    error.value = extractApiError(cause, '密码重置失败，请重新申请链接')
  } finally {
    loading.value = false
  }
}
</script>
