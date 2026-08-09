<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/api/http'
import { extractApiError } from '@/utils/auth'
import type { Notification, PageResult } from '@/types'

const router = useRouter()
const notifications = ref<Notification[]>([])
const loading = ref(true)
const error = ref('')
const unread = computed(() => notifications.value.filter((item) => !item.is_read).length)

async function load() {
  loading.value = true
  error.value = ''
  try {
    notifications.value = (
      await http.get<PageResult<Notification>>('/notifications', {
        params: { page: 1, page_size: 50 },
      })
    ).data.items
  } catch (reason) {
    error.value = extractApiError(reason, '通知暂时无法加载')
  } finally {
    loading.value = false
  }
}

async function open(item: Notification) {
  try {
    if (!item.is_read) {
      await http.put(`/notifications/${item.id}/read`)
      item.is_read = true
    }
    if (item.related_entity_type === 'post' && item.related_entity_id) {
      await router.push(`/posts/${item.related_entity_id}`)
    } else if (item.related_entity_type === 'soup' && item.related_entity_id) {
      await router.push(`/soups/${item.related_entity_id}`)
    }
  } catch (reason) {
    error.value = extractApiError(reason, '通知操作失败')
  }
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-3xl">
      <div class="mb-6 flex items-end justify-between gap-4">
        <div><h1 class="section-title text-3xl">通知</h1><p class="mt-2 text-slate-500">{{ unread ? `${unread} 条未读通知` : '全部通知已读' }}</p></div>
        <button class="btn-secondary" type="button" @click="load">刷新</button>
      </div>
      <div v-if="loading" class="py-16 text-center text-slate-500">正在加载通知…</div>
      <div v-else-if="error" class="py-12 text-center"><p class="text-red-600">{{ error }}</p><button class="btn-secondary mt-4" type="button" @click="load">重新加载</button></div>
      <p v-else-if="!notifications.length" class="py-16 text-center text-slate-500">暂无通知</p>
      <div v-else class="divide-y divide-slate-200 border-y border-slate-200 dark:divide-neutral-800 dark:border-neutral-800">
        <button
          v-for="item in notifications"
          :key="item.id"
          class="block w-full p-5 text-left transition hover:bg-slate-50 dark:hover:bg-neutral-800"
          :class="{ 'border-l-4 border-blue-500 bg-blue-50/40 dark:bg-blue-950/20': !item.is_read }"
          type="button"
          @click="open(item)"
        >
          <div class="flex min-w-0 items-start justify-between gap-4">
            <div class="min-w-0 flex-1"><h2 class="break-words font-semibold">{{ item.title }}</h2><p class="mt-1 break-words whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300">{{ item.content }}</p></div>
            <span v-if="!item.is_read" class="shrink-0 text-xs text-blue-700">未读</span>
          </div>
          <time class="mt-3 block text-xs text-slate-500">{{ new Date(item.created_at).toLocaleString() }}</time>
        </button>
      </div>
    </div>
  </main>
</template>
