<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import DOMPurify from 'dompurify'
import {
  ArrowDownTrayIcon,
  ArrowLeftIcon,
  DocumentTextIcon,
  PaperClipIcon,
} from '@heroicons/vue/24/outline'
import { systemMessagesApi } from '@/api/systemMessages'
import { extractApiError } from '@/utils/auth'
import type { SystemMessageAttachment, SystemMessageDetail, SystemMessageSummary } from '@/types'

const messages = ref<SystemMessageSummary[]>([])
const selected = ref<SystemMessageDetail | null>(null)
const loading = ref(true)
const loadingDetail = ref(false)
const downloadingId = ref<number | null>(null)
const error = ref('')
const page = ref(1)
const totalPages = ref(0)
let detailRequestId = 0
const mobileDetail = computed(() => selected.value !== null)
const safeHtml = computed(() => DOMPurify.sanitize(selected.value?.rendered_html || '', {
  ALLOWED_TAGS: ['a', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2', 'h3', 'h4', 'hr', 'li', 'ol', 'p', 'pre', 'strong', 'ul'],
  ALLOWED_ATTR: ['href', 'title'],
  ALLOW_UNKNOWN_PROTOCOLS: false,
}))

function formatDate(value: string) {
  return new Intl.DateTimeFormat('zh-CN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`
}

async function loadList(targetPage = page.value) {
  loading.value = true
  error.value = ''
  try {
    const response = await systemMessagesApi.list(targetPage)
    messages.value = response.data.items || []
    page.value = response.data.page
    totalPages.value = response.data.total_pages
    if (selected.value && !messages.value.some((item) => item.id === selected.value?.id)) {
      selected.value = null
    }
  } catch (reason) {
    error.value = extractApiError(reason, '系统消息暂时无法加载')
  } finally {
    loading.value = false
  }
}

async function openMessage(item: SystemMessageSummary) {
  const requestId = ++detailRequestId
  loadingDetail.value = true
  error.value = ''
  try {
    const detail = (await systemMessagesApi.detail(item.id)).data
    if (requestId !== detailRequestId) return
    selected.value = detail
    if (detail.is_read) {
      item.is_read = true
      return
    }
    try {
      const readDetail = (await systemMessagesApi.read(item.id)).data
      if (requestId !== detailRequestId) return
      selected.value = readDetail
      item.is_read = true
    } catch (reason) {
      if (requestId !== detailRequestId) return
      error.value = extractApiError(reason, '正文已打开，但标记已读失败')
    }
  } catch (reason) {
    if (requestId !== detailRequestId) return
    error.value = extractApiError(reason, '系统消息暂时无法打开')
  } finally {
    loadingDetail.value = false
  }
}

function backToList() {
  selected.value = null
}

async function download(attachment: SystemMessageAttachment) {
  downloadingId.value = attachment.id
  error.value = ''
  try {
    const response = await systemMessagesApi.attachment(attachment.id)
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = attachment.original_name
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => URL.revokeObjectURL(url), 1000)
  } catch (reason) {
    error.value = extractApiError(reason, '附件下载失败')
  } finally {
    downloadingId.value = null
  }
}

onMounted(() => {
  void loadList()
})
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-6xl">
      <header class="border-b border-slate-200 pb-5 dark:border-neutral-800">
        <h1 class="section-title text-2xl">系统消息</h1>
      </header>

      <p v-if="error" class="mt-4 border-l-2 border-red-500 px-3 text-sm text-red-700 dark:text-red-300">{{ error }}</p>

      <div class="mt-5 grid h-[clamp(32rem,calc(100dvh-12rem),43.75rem)] overflow-hidden border border-slate-200 bg-white dark:border-neutral-800 dark:bg-neutral-950 lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside :class="[mobileDetail ? 'hidden lg:flex' : 'flex', 'min-h-0 flex-col border-r border-slate-200 dark:border-neutral-800']">
          <div class="border-b border-slate-200 px-4 py-3 font-semibold dark:border-neutral-800">收件箱</div>
          <div v-if="loading" class="p-6 text-center text-sm text-slate-500">正在加载…</div>
          <div v-else-if="!messages.length" class="p-8 text-center text-sm text-slate-500">暂无系统消息</div>
          <div v-else class="min-h-0 flex-1 overflow-y-auto">
            <button
              v-for="item in messages"
              :key="item.id"
              class="block min-h-20 w-full border-b border-slate-100 px-4 py-3 text-left transition hover:bg-slate-50 dark:border-neutral-800 dark:hover:bg-neutral-800"
              :class="selected?.id === item.id ? 'bg-blue-50 dark:bg-blue-950/30' : ''"
              type="button"
              @click="openMessage(item)"
            >
              <span class="flex items-center justify-between gap-3">
                <strong class="truncate text-sm" :class="item.is_read ? 'font-medium' : 'font-bold'">{{ item.title }}</strong>
                <span v-if="!item.is_read" class="h-2 w-2 shrink-0 rounded-full bg-blue-600" aria-label="未读"></span>
              </span>
              <span class="mt-2 flex items-center justify-between gap-3 text-xs text-slate-500">
                <time>{{ formatDate(item.created_at) }}</time>
                <span v-if="item.attachment_count" class="inline-flex items-center gap-1"><PaperClipIcon class="h-3.5 w-3.5" aria-hidden="true" />{{ item.attachment_count }}</span>
              </span>
            </button>
          </div>
          <div v-if="totalPages > 1" class="flex items-center justify-between border-t border-slate-200 p-3 text-xs dark:border-neutral-800">
            <button type="button" :disabled="page <= 1" class="text-blue-600 disabled:text-slate-400" @click="loadList(page - 1)">上一页</button>
            <span>{{ page }} / {{ totalPages }}</span>
            <button type="button" :disabled="page >= totalPages" class="text-blue-600 disabled:text-slate-400" @click="loadList(page + 1)">下一页</button>
          </div>
        </aside>

        <section :class="[mobileDetail ? 'flex' : 'hidden lg:flex', 'min-h-0 min-w-0 flex-col']">
          <div v-if="loadingDetail" class="flex flex-1 items-center justify-center text-sm text-slate-500">正在打开…</div>
          <template v-else-if="selected">
            <header class="flex items-start gap-3 border-b border-slate-200 px-4 py-4 dark:border-neutral-800 sm:px-6">
              <button class="mt-0.5 p-1 text-slate-500 hover:text-blue-600 lg:hidden" type="button" aria-label="返回消息列表" title="返回消息列表" @click="backToList">
                <ArrowLeftIcon class="h-5 w-5" aria-hidden="true" />
              </button>
              <div class="min-w-0 flex-1">
                <h2 class="break-words text-lg font-semibold">{{ selected.title }}</h2>
                <p class="mt-1 text-xs text-slate-500">{{ formatDate(selected.created_at) }}</p>
              </div>
            </header>
            <div class="min-h-0 flex-1 overflow-y-auto px-4 py-6 sm:px-8">
              <article class="system-message-content max-w-3xl break-words" v-html="safeHtml"></article>
              <section v-if="selected.attachments.length" class="mt-8 border-t border-slate-200 pt-5 dark:border-neutral-800">
                <h3 class="text-sm font-semibold">附件</h3>
                <div class="mt-3 divide-y divide-slate-100 dark:divide-neutral-800">
                  <div v-for="attachment in selected.attachments" :key="attachment.id" class="flex min-w-0 items-center gap-3 py-3">
                    <DocumentTextIcon class="h-5 w-5 shrink-0 text-slate-400" aria-hidden="true" />
                    <div class="min-w-0 flex-1">
                      <p class="truncate text-sm font-medium" :title="attachment.original_name">{{ attachment.original_name }}</p>
                      <p class="text-xs text-slate-500">{{ formatBytes(attachment.size) }}</p>
                    </div>
                    <button class="flex h-9 w-9 shrink-0 items-center justify-center text-slate-500 hover:bg-slate-100 hover:text-blue-600 dark:hover:bg-neutral-800" type="button" :disabled="downloadingId === attachment.id" aria-label="下载附件" title="下载附件" @click="download(attachment)">
                      <ArrowDownTrayIcon class="h-5 w-5" aria-hidden="true" />
                    </button>
                  </div>
                </div>
              </section>
            </div>
          </template>
          <div v-else class="flex flex-1 flex-col items-center justify-center p-10 text-center text-slate-500">
            <DocumentTextIcon class="h-10 w-10" aria-hidden="true" />
            <p class="mt-3 text-sm">选择一条系统消息</p>
          </div>
        </section>
      </div>
    </div>
  </main>
</template>

<style scoped>
.system-message-content :deep(h1),
.system-message-content :deep(h2),
.system-message-content :deep(h3),
.system-message-content :deep(h4) {
  margin: 1.25rem 0 0.5rem;
  font-weight: 700;
  line-height: 1.3;
}
.system-message-content :deep(p),
.system-message-content :deep(ul),
.system-message-content :deep(ol),
.system-message-content :deep(blockquote),
.system-message-content :deep(pre) {
  margin: 0.75rem 0;
}
.system-message-content :deep(ul),
.system-message-content :deep(ol) {
  padding-left: 1.5rem;
}
.system-message-content :deep(ul) { list-style: disc; }
.system-message-content :deep(ol) { list-style: decimal; }
.system-message-content :deep(a) { color: #2563eb; text-decoration: underline; }
.system-message-content :deep(blockquote) { border-left: 3px solid #94a3b8; padding-left: 1rem; color: #64748b; }
.system-message-content :deep(pre) { overflow-x: auto; background: #111111; padding: 1rem; color: #f8fafc; }
.system-message-content :deep(code) { overflow-wrap: anywhere; }
</style>
