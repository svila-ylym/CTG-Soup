<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftIcon, PencilSquareIcon, TrashIcon } from '@heroicons/vue/24/outline'
import DOMPurify from 'dompurify'
import { postsApi } from '@/api/posts'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime } from '@/utils/datetime'
import type { Post } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const notice = ref<Post | null>(null)
const loading = ref(true)
const error = ref('')
const deletingKey = ref('')

const isAdmin = computed(() => Boolean(auth.user && (auth.user.role === 'admin' || auth.user.role === 'root')))
const canManage = computed(() => Boolean(notice.value && (isAdmin.value || (auth.user && notice.value.author_uid === auth.user.uid))))

const safeHtml = computed(() => {
  if (!notice.value) return ''
  return DOMPurify.sanitize(notice.value.content, {
    ADD_ATTR: ['target', 'download'],
    ADD_TAGS: ['iframe'],
  })
})

async function load() {
  loading.value = true
  error.value = ''
  try {
    notice.value = (await postsApi.get(Number(route.params.id))).data
  } catch (reason) {
    error.value = extractApiError(reason, '公告不存在或暂时不可用')
  } finally {
    loading.value = false
  }
}

async function deleteNotice() {
  if (!notice.value || !canManage.value || !window.confirm(`确定删除公告“${notice.value.title}”吗？`)) return
  deletingKey.value = notice.value.id.toString()
  try {
    await postsApi.delete(notice.value.id)
    await router.push('/posts')
  } catch (reason) {
    error.value = extractApiError(reason, '公告删除失败')
  } finally {
    deletingKey.value = ''
  }
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <div v-if="loading" class="py-20 text-center text-slate-500">正在加载公告…</div>
      <div v-else-if="error" class="py-20 text-center">
        <p class="text-red-600">{{ error }}</p>
        <button class="btn-secondary mt-4" type="button" @click="load">重新加载</button>
      </div>
      <template v-else-if="notice">
        <article class="glass-card p-7 sm:p-9">
          <button class="mb-5 inline-flex items-center gap-1 text-sm text-blue-600 hover:underline" type="button" @click="router.back()">
            <ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />返回公告栏
          </button>

          <div class="flex flex-wrap items-center gap-2 text-sm text-slate-500">
            <span class="inline-flex items-center rounded-full bg-sky-100 px-2.5 py-0.5 text-xs font-semibold text-sky-700 dark:bg-sky-950 dark:text-sky-300">
              📢 官方公告
            </span>
            <span>·</span>
            <router-link :to="`/profile/${notice.author_uid}`" class="font-medium hover:underline">
              {{ notice.author?.username || '管理员' }}
            </router-link>
            <span>·</span>
            <time>{{ formatChinaDateTime(notice.created_at) }}</time>
          </div>

          <h1 class="mt-4 break-words text-2xl font-bold sm:text-3xl text-slate-900 dark:text-white">
            {{ notice.title }}
          </h1>

          <div
            class="mt-6 notice-body"
            v-html="safeHtml"
          ></div>

          <div class="mt-8 flex items-center justify-between gap-4 border-t border-slate-200 pt-4 dark:border-neutral-800">
            <span class="text-sm text-slate-400">已浏览 {{ notice.view_count }} 次</span>
            <div class="flex items-center gap-3">
              <router-link
                v-if="canManage"
                class="btn-secondary inline-flex items-center gap-1"
                :to="`/posts/${notice.id}/edit`"
              >
                <PencilSquareIcon class="h-4 w-4" aria-hidden="true" />修改
              </router-link>
              <button
                v-if="canManage"
                class="btn-danger inline-flex items-center gap-1"
                type="button"
                :disabled="Boolean(deletingKey)"
                @click="deleteNotice"
              >
                <TrashIcon class="h-4 w-4" aria-hidden="true" />删除
              </button>
            </div>
          </div>
        </article>
      </template>
    </div>
  </main>
</template>

<style scoped>
/* Notice body HTML styles — rich rendering for admin-authored content */
.notice-body {
  color: #334155;
  font-size: 1rem;
  line-height: 1.8;
}
.notice-body p { margin: 0.75em 0; }
.notice-body p:first-child { margin-top: 0; }
.notice-body p:last-child { margin-bottom: 0; }
.notice-body h1, .notice-body h2, .notice-body h3 {
  color: #0f172a;
  margin: 1.25em 0 0.5em;
}
.notice-body h1 { font-size: 1.5rem; font-weight: 800; }
.notice-body h2 { font-size: 1.3rem; font-weight: 700; }
.notice-body h3 { font-size: 1.1rem; font-weight: 600; }
.notice-body strong, .notice-body b { font-weight: 700; color: #1e293b; }
.notice-body a { color: #2563eb; text-decoration: underline; }
.notice-body a:hover { color: #1d4ed8; }
.notice-body ul, .notice-body ol { padding-left: 1.5rem; margin: 0.75em 0; }
.notice-body ul { list-style: disc; }
.notice-body ol { list-style: decimal; }
.notice-body li { margin: 0.25em 0; }
.notice-body blockquote {
  border-left: 4px solid #93c5fd;
  background: #eff6ff;
  color: #1e40af;
  padding: 0.75em 1em;
  margin: 1em 0;
  border-radius: 0.5rem;
}
.notice-body code {
  background: #f1f5f9;
  padding: 0.15em 0.4em;
  border-radius: 0.25rem;
  font-size: 0.9em;
  color: #7c2d12;
}
.notice-body pre {
  background: #1e293b;
  color: #e2e8f0;
  padding: 1em 1.25em;
  border-radius: 0.75rem;
  overflow-x: auto;
  margin: 1em 0;
  font-size: 0.875em;
}
.notice-body pre code {
  background: transparent;
  color: inherit;
  padding: 0;
}
.notice-body img {
  max-width: 100%;
  height: auto;
  border-radius: 0.75rem;
  margin: 0.75em 0;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}
.notice-body hr {
  border: none;
  border-top: 1px solid #e2e8f0;
  margin: 1.5em 0;
}
.notice-body table {
  border-collapse: collapse;
  width: 100%;
  margin: 1em 0;
  font-size: 0.9rem;
}
.notice-body th, .notice-body td {
  border: 1px solid #e2e8f0;
  padding: 0.6em 0.8em;
  text-align: left;
}
.notice-body th {
  background: #f8fafc;
  font-weight: 600;
}

.dark .notice-body { color: #e2e8f0; }
.dark .notice-body strong, .dark .notice-body b { color: #f8fafc; }
.dark .notice-body h1, .dark .notice-body h2, .dark .notice-body h3 { color: #f8fafc; }
.dark .notice-body a { color: #60a5fa; }
.dark .notice-body blockquote {
  border-left-color: #1d4ed8;
  background: #1e3a5f;
  color: #93c5fd;
}
.dark .notice-body code { background: #334155; color: #fbbf24; }
.dark .notice-body pre { background: #0f172a; color: #e2e8f0; }
.dark .notice-body hr { border-top-color: #334155; }
.dark .notice-body th, .dark .notice-body td { border-color: #334155; }
.dark .notice-body th { background: #1e293b; }
</style>
