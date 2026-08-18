<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { announcementsApi } from '@/api/announcements'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const successMessage = ref('')

const isNew = computed(() => !route.params.id)
const form = ref({
  title: '',
  content: '<p>请输入公告内容…</p>',
  priority: 0,
})

const isAdmin = computed(() => Boolean(auth.user && (auth.user.role === 'admin' || auth.user.role === 'root')))

async function loadAnnouncement() {
  if (!isNew.value) {
    try {
      const announcement = (await announcementsApi.get(Number(route.params.id))).data
      if (announcement.author_uid !== auth.user?.uid && auth.user?.role !== 'root') {
        error.value = '只有管理员可以编辑公告'
        return
      }
      form.value.title = announcement.title
      form.value.content = announcement.content
      form.value.priority = announcement.priority
    } catch (cause) {
      error.value = extractApiError(cause, '公告加载失败')
    }
  }
  loading.value = false
}

function appendSnippet(kind: string) {
  const snippets: Record<string, string> = {
    p: '<p>段落内容</p>',
    br: '<br>',
    blockquote: '<blockquote>引用内容</blockquote>',
    ul: '<ul>\n  <li>项目一</li>\n  <li>项目二</li>\n</ul>',
    a: '<a href="URL">链接文字</a>',
    img: '<img src="图片URL" alt="说明" />',
  }
  form.value.content = (form.value.content || '') + (snippets[kind] || '')
}

async function save() {
  if (!form.value.title.trim()) return
  submitting.value = true
  error.value = ''
  successMessage.value = ''
  try {
    if (isNew.value) {
      const result = await announcementsApi.create({
        title: form.value.title,
        content: form.value.content,
        priority: form.value.priority,
      })
      // Auto-publish new announcements
      await announcementsApi.publish(result.data.id)
      await router.push('/posts')
    } else {
      await announcementsApi.update(Number(route.params.id), {
        title: form.value.title,
        content: form.value.content,
        priority: form.value.priority,
      })
      successMessage.value = '公告已保存'
      setTimeout(() => router.push(`/posts/${route.params.id}`), 600)
    }
  } catch (cause) {
    error.value = extractApiError(cause, isNew.value ? '发布公告失败' : '修改公告失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadAnnouncement)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-3xl">
      <div v-if="!isAdmin" class="glass-card p-12 text-center">
        <p class="text-xl font-semibold text-slate-600">仅管理员可以发布/编辑公告</p>
        <button class="btn-secondary mt-4" type="button" @click="router.push('/posts')">返回公告栏</button>
      </div>

      <div v-else-if="loading" class="glass-card p-12 text-center text-slate-500">加载中…</div>

      <template v-else-if="form.title !== '' || !isNew">
        <div class="mb-6 flex flex-col gap-2 sm:flex-row sm:items-end sm:justify-between">
          <div>
            <h1 class="section-title text-3xl">{{ isNew ? '发布公告' : '修改公告' }}</h1>
            <p class="mt-1 text-sm text-slate-500">支持 HTML 标签，富文本公告内容</p>
          </div>
          <button class="btn-secondary" type="button" @click="router.push('/posts')">取消</button>
        </div>

        <form class="glass-card p-6 space-y-5" @submit.prevent="save">
          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-300">标题 <span class="text-red-500">*</span></label>
            <input v-model="form.title" class="form-control" required maxlength="200" placeholder="公告标题" />
            <p class="mt-1 text-xs text-slate-400">{{ form.title.length }} / 200</p>
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-300">优先级</label>
            <input v-model.number="form.priority" type="number" class="form-control" min="0" max="999" placeholder="0" />
            <p class="mt-1 text-xs text-slate-400">数字越大优先级越高，置顶公告使用较大的优先级</p>
          </div>

          <div>
            <label class="mb-2 block text-sm font-semibold text-slate-700 dark:text-slate-300">内容（HTML）<span class="text-red-500">*</span></label>
            <div class="flex flex-col gap-2">
              <div class="flex flex-wrap gap-1.5">
                <button type="button" class="rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-slate-300" @click="appendSnippet('p')">
                  <span class="font-mono font-bold">p</span> 段落
                </button>
                <button type="button" class="rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-slate-300" @click="appendSnippet('br')">
                  <span class="font-mono font-bold">br</span> 换行
                </button>
                <button type="button" class="rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-slate-300" @click="appendSnippet('blockquote')">
                  <span class="font-mono font-bold">blockquote</span> 引用
                </button>
                <button type="button" class="rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-slate-300" @click="appendSnippet('ul')">
                  <span class="font-mono font-bold">ul</span> 列表
                </button>
                <button type="button" class="rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-slate-300" @click="appendSnippet('a')">
                  <span class="font-mono font-bold">a</span> 链接
                </button>
                <button type="button" class="rounded border border-slate-200 bg-white px-2 py-1 text-xs font-medium text-slate-600 hover:bg-slate-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-slate-300" @click="appendSnippet('img')">
                  <span class="font-mono font-bold">img</span> 图片
                </button>
              </div>
              <textarea
                v-model="form.content"
                class="form-control min-h-64 font-mono text-sm"
                required
                maxlength="50000"
                placeholder="&lt;p&gt;在这里写公告内容，支持 HTML 标签&lt;/p&gt;"
              ></textarea>
              <p class="mt-1 text-xs text-slate-400">{{ form.content.length }} / 50000 · 支持 HTML 标签</p>
            </div>
          </div>

          <div v-if="error" class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/60 dark:text-red-400">{{ error }}</div>
          <div v-if="successMessage" class="rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/60 dark:text-emerald-400">{{ successMessage }}</div>

          <div class="flex items-center gap-3 pt-2">
            <button class="btn-primary" :disabled="submitting || !form.title.trim()">
              {{ submitting ? '保存中…' : (isNew ? '发布公告' : '保存修改') }}
            </button>
            <button class="btn-secondary" type="button" :disabled="submitting" @click="router.push('/posts')">取消</button>
          </div>
        </form>
      </template>

      <div v-else class="glass-card p-8 text-center">
        <p class="text-red-600">{{ error }}</p>
        <button class="btn-secondary mt-4" type="button" @click="router.push('/posts')">返回公告栏</button>
      </div>
    </div>
  </main>
</template>
