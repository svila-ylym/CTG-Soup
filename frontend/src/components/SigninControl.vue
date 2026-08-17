<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { signinApi } from '@/api/signin'
import { extractApiError } from '@/utils/auth'
import type { SigninStatus } from '@/types'
import LevelBadge from '@/components/LevelBadge.vue'

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

const progressLabel = computed(() => `${Math.round(progress.value)}%`)

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
  <div class="group signin-widget rounded-xl border border-slate-200/60 bg-gradient-to-br from-white/70 to-white/50 p-3 shadow-[inset_0_1px_0_rgba(255,255,255,0.9)] backdrop-blur-sm dark:border-neutral-700/60 dark:from-neutral-800/60 dark:to-neutral-900/60 dark:shadow-[inset_0_1px_0_rgba(255,255,255,0.22)]">
    <div class="flex items-center justify-between gap-2">
      <div class="flex min-w-0 items-center gap-2">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-lg bg-gradient-to-br from-sky-400 to-blue-600 text-white shadow-sm">
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="h-3.5 w-3.5">
            <polyline points="20 6 9 17 4 12" />
          </svg>
        </span>
        <div class="min-w-0">
          <p class="truncate text-xs font-semibold text-slate-700 dark:text-slate-300">
            每日签到
          </p>
          <p class="truncate text-[11px] text-slate-400 dark:text-slate-500">
            {{ status?.signed_in ? `今日已签 +${status.experience_gained}经验` : '连续签到 · 获取经验' }}
          </p>
        </div>
      </div>
      <button
        class="shrink-0 rounded-lg px-2.5 py-1 text-[11px] font-semibold transition disabled:opacity-40 disabled:pointer-events-none"
        :class="status?.signed_in
          ? 'bg-emerald-50 text-emerald-700 ring-1 ring-emerald-200 dark:bg-emerald-950/60 dark:text-emerald-400 dark:ring-emerald-900'
          : 'bg-sky-600 text-white shadow-sm hover:bg-sky-500 focus-visible:ring-2 focus-visible:ring-sky-400/40'
        "
        type="button"
        :disabled="loading || !status || status.signed_in"
        :title="status?.signed_in ? '今日已签到' : '每日签到'"
        @click="signIn"
      >
        <span v-if="loading" class="inline-block h-3 w-3 animate-spin rounded-full border-[1.5px] border-white/40 border-t-white"></span>
        <span v-else-if="status?.signed_in">✓ 已签</span>
        <span v-else>签到</span>
      </button>
    </div>

    <div class="mt-2.5 flex items-center gap-2.5">
      <LevelBadge :level="status?.level" compact class="shrink-0" />
      <div class="flex min-w-0 flex-1 items-center gap-2">
        <span class="text-[11px] text-slate-400 dark:text-slate-500">
          Lv.{{ status?.level ?? 0 }}
        </span>
        <span class="h-1 flex-1 overflow-hidden rounded-full bg-slate-200 dark:bg-neutral-700">
          <span
            class="block h-full rounded-full bg-gradient-to-r from-sky-400 to-blue-600 transition-all duration-500"
            :style="{ width: `${progress}%` }"
          ></span>
        </span>
        <span class="text-[11px] tabular-nums text-slate-400 dark:text-slate-500">
          {{ progressLabel }}
        </span>
      </div>
    </div>

    <p v-if="error" class="mt-2 rounded-lg bg-red-50 px-2.5 py-1.5 text-[11px] text-red-600 dark:bg-red-950/60 dark:text-red-400" role="status">{{ error }}</p>
  </div>
</template>
