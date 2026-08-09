<template>
  <main class="page-shell">
    <section class="page-container max-w-md">
      <h1 class="text-2xl font-bold text-gray-900 dark:text-white">验证邮箱</h1>

      <form class="mt-8 space-y-4" @submit.prevent="verify">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300" for="token">
          验证令牌
        </label>
        <textarea
          id="token"
          v-model.trim="token"
          required
          rows="3"
          class="block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
        />
        <button
          class="w-full rounded-md bg-blue-600 px-4 py-3 font-medium text-white disabled:opacity-50"
          type="submit"
          :disabled="loading"
        >
          {{ loading ? '验证中…' : '验证邮箱' }}
        </button>
      </form>

      <div class="mt-8 border-t border-gray-200 pt-6 dark:border-neutral-800">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300" for="email">
          未收到邮件
        </label>
        <input
          id="email"
          v-model.trim="email"
          type="email"
          class="mt-2 block w-full rounded-md border border-gray-300 bg-white px-3 py-2 text-gray-900 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
        />
        <button
          class="mt-3 w-full rounded-md border border-gray-300 px-4 py-2 text-gray-800 disabled:opacity-50 dark:border-neutral-700 dark:text-gray-200"
          type="button"
          :disabled="loading || !email"
          @click="resend"
        >
          重新发送
        </button>
      </div>

      <p v-if="message" class="mt-5 break-words text-sm text-green-700 dark:text-green-400">{{ message }}</p>
      <p v-if="error" class="mt-5 break-words text-sm text-red-700 dark:text-red-400">{{ error }}</p>
      <router-link v-if="verified" class="mt-6 inline-block text-blue-600" to="/login">前往登录</router-link>
    </section>
  </main>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { authApi } from '@/api/auth'
import { extractApiError } from '@/utils/auth'

const route = useRoute()
const token = ref(typeof route.query.token === 'string' ? route.query.token : '')
const email = ref(typeof route.query.email === 'string' ? route.query.email : '')
const loading = ref(false)
const verified = ref(false)
const message = ref('')
const error = ref('')
const verificationRequests = new Map<string, Promise<void>>()

function verify() {
  const currentToken = token.value
  if (!currentToken || verified.value) return

  const existingRequest = verificationRequests.get(currentToken)
  if (existingRequest) return existingRequest

  loading.value = true
  message.value = ''
  error.value = ''
  const request = authApi.verifyEmail(currentToken)
    .then((response) => {
      message.value = response.data.message
      error.value = ''
      verified.value = true
    })
    .catch((reason) => {
      if (!verified.value) {
        error.value = extractApiError(reason, '邮箱验证失败')
      }
    })
    .finally(() => {
      verificationRequests.delete(currentToken)
      loading.value = verificationRequests.size > 0
    })

  verificationRequests.set(currentToken, request)
  return request
}

async function resend() {
  loading.value = true
  message.value = ''
  error.value = ''
  try {
    const response = await authApi.sendVerificationEmail(email.value)
    message.value = response.data.message
  } catch (reason) {
    error.value = extractApiError(reason, '验证邮件发送失败')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (token.value) verify()
})
</script>
