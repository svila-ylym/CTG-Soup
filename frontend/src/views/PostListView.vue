<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ChatBubbleOvalLeftIcon, EyeIcon, HeartIcon } from '@heroicons/vue/24/outline'
import http from '@/api/http'
import MentionText from '@/components/MentionText.vue'
import UserBadges from '@/components/UserBadges.vue'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime } from '@/utils/datetime'
import { draftStorageKey, readDraft, removeDraft, writeDraft } from '@/utils/draftStorage'
import type { PageResult, Post } from '@/types'

const router = useRouter()
const authStore = useAuthStore()
const posts = ref<Post[]>([])
const loading = ref(true)
const error = ref('')
const section = ref('')
const sortBy = ref('created_at')
const page = ref(1)
const totalPages = ref(1)
const composerOpen = ref(false)
const submitting = ref(false)
const submitMessage = ref('')

type PostDraft = {
  title: string
  content: string
  section: string
}

const emptyPostDraft = (): PostDraft => ({ title: '', content: '', section: 'general' })
const draft = ref<PostDraft>(emptyPostDraft())

function isPostDraft(value: unknown): value is PostDraft {
  if (typeof value !== 'object' || value === null || Array.isArray(value)) return false
  const record = value as Record<string, unknown>
  return (
    typeof record.title === 'string'
    && typeof record.content === 'string'
    && typeof record.section === 'string'
  )
}

function hasPostDraft(value: PostDraft): boolean {
  const sectionValue = value.section.trim()
  return Boolean(
    value.title.trim()
    || value.content.trim()
    || (sectionValue && sectionValue !== 'general')
  )
}

const postDraftKey = draftStorageKey(
  'post',
  authStore.user?.uid ?? localStorage.getItem('user_uid'),
)
const restoredPostDraft = readDraft(postDraftKey, isPostDraft)
if (restoredPostDraft && hasPostDraft(restoredPostDraft)) {
  draft.value = { ...restoredPostDraft }
  composerOpen.value = true
} else if (restoredPostDraft) {
  removeDraft(postDraftKey)
}

watch(draft, currentDraft => {
  const snapshot = { ...currentDraft }
  if (hasPostDraft(snapshot)) writeDraft(postDraftKey, snapshot)
  else removeDraft(postDraftKey)
}, { deep: true, flush: 'sync' })

async function load() {
  loading.value = true; error.value = ''
  try {
    const result = await http.get<PageResult<Post>>('/posts', { params: { page: page.value, page_size: 20, section: section.value || undefined, sort_by: sortBy.value } })
    posts.value = result.data.items || []; totalPages.value = result.data.total_pages || 1
  } catch (cause) { error.value = extractApiError(cause, '论坛暂时无法加载') } finally { loading.value = false }
}
function changePage(next: number) { page.value = next; load() }
async function createPost() {
  if (!draft.value.title.trim() || !draft.value.content.trim()) return
  submitting.value = true; submitMessage.value = ''
  try {
    await http.post('/posts', { title: draft.value.title, content: draft.value.content, section: draft.value.section.trim() ? draft.value.section : 'general', post_type: 'normal', tags: [] })
    draft.value = emptyPostDraft(); removeDraft(postDraftKey); composerOpen.value = false; submitMessage.value = '帖子发布成功'; await load()
  } catch (cause) { submitMessage.value = extractApiError(cause, '发布失败，请先登录并重试') } finally { submitting.value = false }
}
onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container">
      <div class="mb-6 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 class="section-title text-3xl">论坛</h1>
          <p class="mt-2 text-slate-500">和其他玩家分享线索、复盘与灵感。</p>
        </div>
        <div class="grid w-full grid-cols-1 gap-2 sm:grid-cols-[10rem_10rem_auto] lg:w-auto">
          <input v-model="section" class="form-control" placeholder="版块（可选）" @keyup.enter="load">
          <select v-model="sortBy" class="form-control" @change="load">
            <option value="created_at">最新发布</option>
            <option value="like_count">最多点赞</option>
            <option value="comment_count">最多评论</option>
          </select>
          <button class="btn-primary" @click="composerOpen = !composerOpen">发布帖子</button>
        </div>
      </div>

      <form v-if="composerOpen" class="surface-card mb-6 space-y-4 p-5" @submit.prevent="createPost">
        <h2 class="section-title">发布帖子</h2>
        <input v-model="draft.title" class="form-control" required maxlength="200" placeholder="标题">
        <input v-model="draft.section" class="form-control" maxlength="50" placeholder="版块">
        <textarea v-model="draft.content" class="form-control min-h-32" required placeholder="分享你的内容…"></textarea>
        <div class="flex flex-wrap items-center gap-3">
          <button class="btn-primary" :disabled="submitting || !draft.title.trim() || !draft.content.trim()">{{ submitting ? '发布中…' : '发布' }}</button>
          <button class="btn-secondary" type="button" :disabled="submitting" @click="composerOpen = false">取消</button>
          <span v-if="submitMessage" class="min-w-0 break-words text-sm" :class="submitMessage.includes('成功') ? 'text-emerald-600' : 'text-red-600'">{{ submitMessage }}</span>
        </div>
      </form>

      <div v-if="loading" class="surface-card p-12 text-center text-slate-500">正在加载帖子…</div>
      <div v-else-if="error" class="surface-card p-8 text-center">
        <p class="break-words text-red-600">{{ error }}</p>
        <button class="btn-secondary mt-4" @click="load">重新加载</button>
      </div>
      <div v-else-if="!posts.length" class="surface-card p-12 text-center text-slate-500">还没有帖子，成为第一个分享的人吧。</div>
      <div v-else class="space-y-4">
        <article v-for="post in posts" :key="post.id" class="surface-card cursor-pointer p-5 transition hover:border-blue-400" @click="router.push(`/posts/${post.id}`)">
          <div class="flex min-w-0 flex-wrap items-center gap-2 text-xs text-slate-500">
            <span class="max-w-full break-words rounded-full bg-blue-50 px-2 py-1 text-blue-700">{{ post.section }}</span>
            <router-link :to="`/profile/${post.author_uid}`" class="min-w-0 break-words hover:text-blue-600 hover:underline" @click.stop>{{ post.author?.nickname || post.author?.username || `用户 ${post.author_uid}` }}</router-link>
            <UserBadges :level="post.author?.level" :band="post.author?.level_band" :permission-groups="post.author?.permission_groups" :role="post.author?.role" compact />
            <time>{{ formatChinaDateTime(post.created_at) }}</time>
          </div>
          <h2 class="mt-3 break-words text-lg font-semibold text-slate-900 dark:text-white">{{ post.title }}</h2>
          <p class="mt-2 line-clamp-2 break-words whitespace-pre-wrap text-sm text-slate-600 dark:text-slate-300"><MentionText :text="post.content" :mentions="post.mentions" /></p>
          <div class="mt-4 flex flex-wrap gap-x-5 gap-y-2 text-sm text-slate-500">
            <span class="inline-flex items-center gap-1"><HeartIcon class="h-4 w-4" aria-hidden="true" />{{ post.like_count }}</span>
            <span class="inline-flex items-center gap-1"><ChatBubbleOvalLeftIcon class="h-4 w-4" aria-hidden="true" />{{ post.comment_count }}</span>
            <span class="inline-flex items-center gap-1"><EyeIcon class="h-4 w-4" aria-hidden="true" />{{ post.view_count }}</span>
          </div>
        </article>
        <div class="flex flex-wrap items-center justify-center gap-3">
          <button class="btn-secondary" :disabled="page <= 1" @click.stop="changePage(page - 1)">上一页</button>
          <span class="py-2 text-sm text-slate-500">{{ page }} / {{ totalPages }}</span>
          <button class="btn-secondary" :disabled="page >= totalPages" @click.stop="changePage(page + 1)">下一页</button>
        </div>
      </div>
    </div>
  </main>
</template>
