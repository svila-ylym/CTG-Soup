<template>
  <main class="flex min-h-screen items-center justify-center bg-white px-4 py-12 dark:bg-black">
    <div class="w-full max-w-md">
      <div class="text-center">
        <p class="text-sm font-semibold text-blue-600 dark:text-blue-400">账号安全</p>
        <h1 class="mt-2 text-3xl font-bold text-slate-900 dark:text-white">找回密码</h1>
        <p class="mt-3 text-sm leading-6 text-slate-500">填写注册邮箱，我们会发送一个 30 分钟内有效的重置链接。</p>
      </div>

      <form class="mt-8 space-y-5 border-y border-slate-200 py-8 dark:border-neutral-800 sm:px-8" @submit.prevent="submit">
        <div>
          <label for="reset-email" class="block text-sm font-medium text-slate-700 dark:text-slate-300">注册邮箱</label>
          <input id="reset-email" v-model.trim="email" class="form-control mt-1" type="email" autocomplete="email" required placeholder="name@example.com">
        </div>
        <p v-if="error" class="break-words rounded-md bg-red-50 p-3 text-sm text-red-600 dark:bg-red-950/30 dark:text-red-300">{{ error }}</p>
        <p v-if="message" class="break-words rounded-md bg-emerald-50 p-3 text-sm leading-6 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300">{{ message }}。请检查收件箱和垃圾邮件。</p>
        <button class="btn-primary w-full" type="submit" :disabled="loading || !email">
          {{ loading ? '正在发送…' : message ? '重新发送重置邮件' : '发送重置邮件' }}
        </button>
        <router-link to="/login" class="block text-center text-sm font-medium text-blue-600 hover:text-blue-700 dark:text-blue-400">返回登录</router-link>
      </form>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { authApi } from '@/api/auth'
import { extractApiError } from '@/utils/auth'

const email = ref('')
const loading = ref(false)
const error = ref('')
const message = ref('')

async function submit() {
  if (!email.value || loading.value) return
  loading.value = true
  error.value = ''
  message.value = ''
  try {
    const response = await authApi.requestPasswordReset(email.value)
    message.value = response.data.message
  } catch (cause) {
    error.value = extractApiError(cause, '重置邮件发送失败，请稍后再试')
  } finally {
    loading.value = false
  }
}
</script>
