<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/api/http'
import { useUnreadStore } from '@/stores/unread'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime } from '@/utils/datetime'
import type { Notification, PageResult } from '@/types'
import LinkifiedText from '@/components/LinkifiedText.vue'

const router = useRouter()
const unreadStore = useUnreadStore()
const notifications = ref<Notification[]>([])
const loading = ref(true)
const markingAll = ref(false)
const error = ref('')
const hasUnread = computed(() => unreadStore.hasNotifications || notifications.value.some(item => !item.is_read))

async function load() {
  loading.value = true
  error.value = ''
  try {
    notifications.value = (
      await http.get<PageResult<Notification>>('/notifications', {
        params: { page: 1, page_size: 50 },
      })
    ).data.items
    await unreadStore.refreshNotifications()
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
      await unreadStore.refreshNotifications()
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

async function markAllRead() {
  if (markingAll.value || !hasUnread.value) return
  markingAll.value = true
  error.value = ''
  try {
    await http.put<{ updated_count: number }>('/notifications/read-all')
    notifications.value.forEach((item) => { item.is_read = true })
    unreadStore.markNotificationsRead()
  } catch (reason) {
    error.value = extractApiError(reason, '全部已读操作失败，请稍后重试')
  } finally {
    markingAll.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-3xl">
      <div class="mb-6 flex items-end justify-between gap-4">
        <div><h1 class="section-title text-3xl">通知</h1><p class="mt-2 text-slate-500">{{ unreadStore.hasNotifications ? '有未读通知' : '全部通知已读' }}</p></div>
        <div class="flex shrink-0 flex-wrap justify-end gap-2">
          <button v-if="hasUnread" class="btn-primary" type="button" :disabled="markingAll" @click="markAllRead">{{ markingAll ? '处理中…' : '全部已读' }}</button>
          <button class="btn-secondary" type="button" :disabled="loading || markingAll" @click="load">刷新</button>
        </div>
      </div>
      <div v-if="loading" class="py-16 text-center text-slate-500">正在加载通知…</div>
      <div v-else-if="error && !notifications.length" class="py-12 text-center"><p class="text-red-600">{{ error }}</p><button class="btn-secondary mt-4" type="button" @click="load">重新加载</button></div>
      <template v-else>
        <p v-if="error" class="mb-4 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300" role="alert">{{ error }}</p>
        <p v-if="!notifications.length" class="py-16 text-center text-slate-500">暂无通知</p>
        <div v-else class="divide-y divide-slate-200 border-y border-slate-200 dark:divide-neutral-800 dark:border-neutral-800">
        <article
          v-for="item in notifications"
          :key="item.id"
          class="block w-full cursor-pointer p-5 text-left transition hover:bg-slate-50 dark:hover:bg-neutral-800"
          :class="{ 'border-l-4 border-blue-500 bg-blue-50/40 dark:bg-blue-950/20': !item.is_read }"
          role="button"
          tabindex="0"
          @click="open(item)"
          @keydown.enter.self.prevent="open(item)"
          @keydown.space.self.prevent="open(item)"
        >
          <div class="flex min-w-0 items-start justify-between gap-4">
            <div class="min-w-0 flex-1"><h2 class="break-words font-semibold"><LinkifiedText :text="item.title" /></h2><p class="mt-1 break-words whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300"><LinkifiedText :text="item.content" /></p></div>
            <span v-if="!item.is_read" class="shrink-0 text-xs text-blue-700">未读</span>
          </div>
          <time class="mt-3 block text-xs text-slate-500">{{ formatChinaDateTime(item.created_at) }}</time>
        </article>
        </div>
      </template>
    </div>
  </main>
</template>
