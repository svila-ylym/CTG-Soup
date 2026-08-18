<script setup lang=ts>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { PencilSquareIcon, ClockIcon } from '@heroicons/vue/24/outline'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime } from '@/utils/datetime'
import type { PageResult, Announcement } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const notices = ref<Announcement[]>([])
const loading = ref(true)
const error = ref('')
const page = ref(1)
const totalPages = ref(1)

const canCreate = computed(() => Boolean(authStore.user && (authStore.user.role === 'admin' || authStore.user.role === 'root')))
const isAdmin = computed(() => Boolean(authStore.user && (authStore.user.role === 'admin' || authStore.user.role === 'root')))

const stripHtml = (text: string): string => {
  const tmp = document.createElement('div')
  tmp.innerHTML = text
  return tmp.textContent || tmp.innerText || ''
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const result = await http.get<PageResult<Announcement>>('/announcements', {
      params: {
        page: page.value,
        page_size: 10,
      },
    })
    notices.value = result.data.items || []
    totalPages.value = result.data.total_pages || 1
  } catch (cause) {
    error.value = extractApiError(cause, '公告栏暂时无法加载')
  } finally {
    loading.value = false
  }
}

function changePage(next: number) {
  page.value = next
  load()
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <!-- Header -->
      <div class="mb-6 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h1 class="section-title text-3xl">📢 公告栏</h1>
          <p class="mt-1 text-sm text-slate-500">官方公告、活动通知、规则更新</p>
        </div>
        <router-link
          v-if="canCreate"
          to="/posts/create"
          class="btn-primary inline-flex items-center gap-2"
        >
          <PencilSquareIcon class="h-5 w-5" aria-hidden="true" />
          发布公告
        </router-link>
      </div>

      <!-- Notice list -->
      <div v-if="loading" class="flex flex-col gap-3">
        <div v-for="i in 5" :key="i" class="glass-card p-5">
          <div class="skeleton-block h-6 w-1/2"></div>
          <div class="mt-3 skeleton-block h-4 w-3/4"></div>
          <div class="mt-2 skeleton-block h-3 w-1/4"></div>
        </div>
      </div>

      <div v-else-if="error" class="glass-card p-8 text-center text-red-600">{{ error }}</div>

      <div v-else-if="!notices.length" class="glass-card p-16 text-center">
        <p class="text-xl font-medium text-slate-500">暂无公告</p>
        <p v-if="isAdmin" class="mt-2 text-sm text-slate-400">快去发布第一则公告吧</p>
      </div>

      <template v-else>
        <ul class="flex flex-col gap-3">
          <li v-for="notice in notices" :key="notice.id">
            <router-link
              :to="`/posts/${notice.id}`"
              class="block glass-card p-5 transition hover:border-sky-300 dark:hover:border-slate-500"
            >
              <div class="flex items-start justify-between gap-4">
                <div class="min-w-0 flex-1">
                  <h2 class="text-lg font-bold leading-tight text-slate-900 dark:text-white hover:text-sky-600 dark:hover:text-sky-400">
                    {{ notice.title }}
                  </h2>
                  <p class="mt-2 line-clamp-2 text-sm leading-6 text-slate-600 dark:text-slate-300">
                    {{ stripHtml(notice.content) }}
                  </p>
                  <div class="mt-3 flex items-center gap-2 text-xs text-slate-400">
                    <ClockIcon class="h-3.5 w-3.5" aria-hidden="true" />
                    <span>管理员</span>
                    <span>·</span>
                    <span>{{ formatChinaDateTime(notice.published_at || notice.created_at) }}</span>
                  </div>
                </div>
                <span
                  v-if="isAdmin && (notice.author_uid === authStore.user?.uid || authStore.user?.role === 'root')"
                  class="flex-shrink-0"
                  @click.prevent="router.push(`/posts/${notice.id}/edit`)"
                >
                  <button
                    type="button"
                    class="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-3 py-1.5 text-xs font-medium text-slate-600 shadow-[inset_0_1px_0_rgba(255,255,255,0.88)] hover:bg-slate-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-slate-300 dark:shadow-[inset_0_1px_0_rgba(255,255,255,0.22)]"
                    @click.stop="router.push(`/posts/${notice.id}/edit`)"
                  >
                    <PencilSquareIcon class="h-3.5 w-3.5" aria-hidden="true" />
                    编辑
                  </button>
                </span>
              </div>
            </router-link>
          </li>
        </ul>

        <!-- Pagination -->
        <div v-if="totalPages > 1" class="mt-5 flex flex-wrap items-center justify-center gap-3">
          <button class="btn-secondary" :disabled="page <= 1" @click.stop="changePage(page - 1)">上一页</button>
          <span class="py-2 text-sm text-slate-500">{{ page }} / {{ totalPages }}</span>
          <button class="btn-secondary" :disabled="page >= totalPages" @click.stop="changePage(page + 1)">下一页</button>
        </div>
      </template>
    </div>
  </main>
</template>
