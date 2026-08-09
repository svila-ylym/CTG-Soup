<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { signinApi } from '@/api/signin'
import { extractApiError } from '@/utils/auth'
import type { SigninStatus } from '@/types'

const status = ref<SigninStatus | null>(null)
const loading = ref(false)
const error = ref('')
const progress = computed(() => {
  if (!status.value || status.value.next_level_start === null) return 100
  const span = status.value.next_level_start - status.value.level_start
  return span > 0
    ? Math.min(100, Math.max(0, ((status.value.experience_points - status.value.level_start) / span) * 100))
    : 0
})

async function load() {
  try {
    status.value = (await signinApi.status()).data
    error.value = ''
  } catch (reason) {
    error.value = extractApiError(reason, '签到状态加载失败')
  }
}

async function signIn() {
  loading.value = true
  error.value = ''
  try {
    status.value = (await signinApi.signin()).data
    window.dispatchEvent(new Event('signinchange'))
  } catch (reason) {
    error.value = extractApiError(reason, '签到失败')
    await load()
  } finally {
    loading.value = false
  }
}

function refresh() {
  void load()
}

onMounted(() => {
  void load()
  window.addEventListener('signinchange', refresh)
})

onUnmounted(() => {
  window.removeEventListener('signinchange', refresh)
})
</script>

<template>
  <div class="relative w-36 shrink-0">
    <button
      class="w-full border border-slate-200 px-2 py-1.5 text-left text-xs dark:border-neutral-800"
      type="button"
      :disabled="loading || !status || status.signed_in"
      :title="status?.signed_in ? '今日已签到' : '每日签到'"
      @click="signIn"
    >
      <span class="flex items-center justify-between gap-2">
        <strong>Lv.{{ status?.level ?? '-' }}</strong>
        <span>{{ status?.signed_in ? '已签到' : '签到' }}</span>
      </span>
      <span class="mt-1 block h-1 bg-slate-200 dark:bg-neutral-800">
        <span class="block h-full bg-blue-600" :style="{ width: `${progress}%` }"></span>
      </span>
    </button>
    <p v-if="error" class="absolute right-0 top-full z-20 mt-1 w-56 break-words border border-red-200 bg-white p-2 text-[11px] text-red-700 shadow-lg dark:border-red-900 dark:bg-neutral-900 dark:text-red-300" role="status">{{ error }}</p>
  </div>
</template>
