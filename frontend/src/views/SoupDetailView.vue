<template>
  <main class="page-shell">
    <div class="page-container max-w-5xl">
      <div v-if="loading" class="rounded-lg bg-white dark:bg-neutral-900 p-8 text-center">加载中…</div>
      <div v-else-if="error" class="rounded-lg bg-red-50 dark:bg-red-900/20 p-8 text-center text-red-600">{{ error }}</div>
      <template v-else-if="soup">
        <article class="surface-card p-5 sm:p-8">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="min-w-0 flex-1">
              <p class="mb-2 break-words text-sm text-blue-500">海龟汤 · <router-link :to="`/profile/${soup.author_uid}`" class="font-medium hover:underline">{{ soup.author.nickname || soup.author.username || '未知作者' }}</router-link></p>
              <h1 class="break-words text-2xl font-bold text-gray-900 dark:text-white sm:text-3xl">{{ soup.title }}</h1>
            </div>
            <div class="shrink-0 text-right text-sm text-gray-500">
              <div class="text-2xl font-semibold text-amber-500">{{ displayScore.toFixed(1) }} 分</div>
              <div>{{ soup.rating_count }} 人评分</div>
            </div>
          </div>

          <section class="mt-8">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">谜面</h2>
            <p class="break-words whitespace-pre-wrap leading-7 text-gray-700 dark:text-gray-300">{{ soup.puzzle }}</p>
          </section>

          <dl class="mt-6 grid gap-4 border-y border-slate-200 py-5 dark:border-neutral-800 sm:grid-cols-2">
            <div class="min-w-0">
              <dt class="text-sm font-medium text-slate-500">主要人物</dt>
              <dd class="mt-1 break-words whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200">{{ soup.main_player_count || '未填写' }}</dd>
            </div>
            <div class="min-w-0">
              <dt class="text-sm font-medium text-slate-500">次要人物</dt>
              <dd class="mt-1 break-words whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200">{{ soup.secondary_player_count || '未填写' }}</dd>
            </div>
          </dl>

          <section class="mt-8 rounded-lg border border-dashed border-amber-300 bg-amber-50/60 p-5 dark:border-amber-800 dark:bg-amber-950/30">
            <div class="flex items-center justify-between gap-4">
              <h2 class="text-lg font-semibold text-amber-950 dark:text-amber-100">汤底</h2>
              <button v-if="!revealed" :disabled="revealing" class="rounded-md bg-amber-700 px-4 py-2 text-sm text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-60" @click="reveal">
                {{ revealing ? '加载中…' : '揭示汤底' }}
              </button>
            </div>
            <p v-if="revealed" class="mt-3 break-words whitespace-pre-wrap leading-7 text-gray-700 dark:text-gray-300">{{ soup.solution }}</p>
            <p v-else class="mt-3 text-amber-800 dark:text-amber-200">汤底已隐藏，确认后才会显示。</p>
            <p v-if="revealError" class="mt-3 text-sm text-red-600 dark:text-red-400">{{ revealError }}</p>
          </section>

          <div class="mt-8 flex flex-wrap items-center gap-3 border-t border-gray-100 dark:border-neutral-800 pt-5">
            <label class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
              评分
              <input v-model.number="score" type="number" min="1" max="10" step="0.5" class="w-20 rounded border px-2 py-1 dark:bg-neutral-800" @change="rate" />
            </label>
            <button class="inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 py-2 text-sm" :class="soup.is_liked ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-700 dark:bg-neutral-800 dark:text-gray-200'" @click="toggle('like')"><HeartIcon class="h-4 w-4" aria-hidden="true" />{{ soup.like_count }}</button>
            <button class="inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 py-2 text-sm" :class="soup.is_favorited ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-700 dark:bg-neutral-800 dark:text-gray-200'" @click="toggle('favorite')"><BookmarkIcon class="h-4 w-4" aria-hidden="true" />{{ soup.favorite_count }}</button>
            <button class="ml-auto inline-flex min-h-9 items-center gap-1.5 text-sm text-gray-500 hover:text-red-600" @click="reportOpen = true"><FlagIcon class="h-4 w-4" aria-hidden="true" />举报</button>
          </div>
        </article>
        <section class="mt-6 border-t border-slate-200 py-6 dark:border-neutral-800">
          <h2 class="text-xl font-semibold">讨论</h2>
          <div class="mt-4 flex flex-col gap-3 sm:flex-row">
            <textarea v-model="commentText" class="form-control min-h-24 flex-1" maxlength="2000" placeholder="分享你的推理…" aria-label="评论内容"></textarea>
            <button class="btn-primary self-end" :disabled="commentSubmitting || !commentText.trim()" @click="submitComment">
              {{ commentSubmitting ? '发送中…' : '发表评论' }}
            </button>
          </div>
          <p v-if="commentError" class="mt-3 text-sm text-red-600">{{ commentError }}</p>
          <div v-if="commentsLoading" class="py-8 text-center text-gray-500">评论加载中…</div>
          <div v-else-if="!comments.length" class="py-8 text-center text-gray-500">还没有评论，来做第一个推理者吧。</div>
          <div v-else class="mt-6 divide-y divide-slate-200 border-y border-slate-200 dark:divide-neutral-800 dark:border-neutral-800">
            <article v-for="item in comments" :key="item.id" class="py-4">
              <div class="flex items-center justify-between gap-3 text-sm">
                <router-link :to="`/profile/${item.author_uid}`" class="font-semibold hover:text-blue-600 hover:underline">{{ item.author?.nickname || item.author?.username || `用户 ${item.author_uid}` }}</router-link>
                <time class="text-xs text-slate-500">{{ new Date(item.created_at).toLocaleString() }}</time>
              </div>
              <p class="mt-2 break-words whitespace-pre-wrap text-slate-700 dark:text-slate-200"><MentionText :text="item.content" :mentions="item.mentions" /></p>
              <button class="mt-2 text-xs font-medium text-blue-600 hover:underline" type="button" @click="startReply(item, item)">回复</button>
              <div v-for="reply in item.replies || []" :key="reply.id" class="mt-3 break-words border-l-2 border-blue-200 pl-3 text-sm">
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <router-link :to="`/profile/${reply.author_uid}`" class="font-semibold hover:text-blue-600 hover:underline">{{ reply.author?.nickname || reply.author?.username || `用户 ${reply.author_uid}` }}</router-link>
                  <time class="text-xs text-slate-500">{{ new Date(reply.created_at).toLocaleString() }}</time>
                </div>
                <p class="mt-1 whitespace-pre-wrap"><MentionText :text="reply.content" :mentions="reply.mentions" /></p>
                <button class="mt-1 text-xs font-medium text-blue-600 hover:underline" type="button" @click="startReply(item, reply)">回复</button>
              </div>
              <div v-if="replyParentId === item.id" class="mt-4 flex flex-col gap-2 sm:flex-row">
                <textarea v-model="replyText" class="form-control min-h-20 flex-1" maxlength="2000" placeholder="回复这条评论" aria-label="回复内容"></textarea>
                <div class="flex items-end gap-2"><button class="btn-primary" type="button" :disabled="replySubmitting || !replyText.trim()" @click="submitReply">{{ replySubmitting ? '发送中…' : '发送回复' }}</button><button class="btn-secondary" type="button" :disabled="replySubmitting" @click="cancelReply">取消</button></div>
              </div>
            </article>
          </div>
        </section>
        <ReportDialog :open="reportOpen" target-type="soup" :target-id="soup.id" @close="reportOpen = false" />
      </template>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { BookmarkIcon, FlagIcon, HeartIcon } from '@heroicons/vue/24/outline'
import { soupApi } from '@/api/soup'
import type { Comment, TurtleSoup } from '@/types'
import ReportDialog from '@/components/ReportDialog.vue'
import MentionText from '@/components/MentionText.vue'

const route = useRoute()
const soup = ref<TurtleSoup | null>(null)
const loading = ref(true)
const error = ref('')
const revealed = ref(false)
const revealing = ref(false)
const revealError = ref('')
const score = ref<number | null>(null)
const reportOpen = ref(false)
const comments = ref<Comment[]>([])
const commentsLoading = ref(false)
const commentSubmitting = ref(false)
const commentText = ref('')
const replyText = ref('')
const replyParentId = ref<number | null>(null)
const replySubmitting = ref(false)
const commentError = ref('')
const displayScore = computed(() => soup.value?.average_score ?? 0)

async function load(revealSolution = false) {
  loading.value = true
  error.value = ''
  try {
    const response = await soupApi.getById(Number(route.params.id), revealSolution)
    soup.value = response.data
    revealed.value = soup.value.solution != null
    score.value = soup.value.my_rating ?? null
    await loadComments()
  } catch (e: any) {
    error.value = e.response?.data?.detail || '无法加载海龟汤'
  } finally {
    loading.value = false
  }
}
async function reveal() {
  if (!soup.value || revealing.value) return
  revealing.value = true
  revealError.value = ''
  try {
    const response = await soupApi.getById(soup.value.id, true)
    soup.value = response.data
    revealed.value = soup.value.solution != null
    if (!revealed.value) revealError.value = '汤底暂时无法显示'
  } catch (cause: any) {
    revealError.value = cause.response?.data?.detail?.message || cause.response?.data?.detail || '汤底加载失败'
  } finally {
    revealing.value = false
  }
}
async function rate() {
  if (!soup.value || score.value == null || score.value < 1 || score.value > 10 || score.value * 2 % 1 !== 0) return
  const response = await soupApi.rate(soup.value.id, score.value)
  soup.value = { ...soup.value, ...response.data }
}
async function toggle(kind: 'like' | 'favorite') {
  if (!soup.value) return
  const active = kind === 'like' ? !!soup.value.is_liked : !!soup.value.is_favorited
  const response = await soupApi.setInteraction(soup.value.id, kind, !active)
  soup.value = { ...soup.value, ...response.data }
}
async function loadComments() {
  if (!soup.value) return
  commentsLoading.value = true
  try {
    comments.value = (await soupApi.listComments(soup.value.id, { page: 1, page_size: 50 })).data.items || []
  } catch {
    comments.value = []
  } finally {
    commentsLoading.value = false
  }
}
async function submitComment() {
  if (!soup.value || !commentText.value.trim()) return
  commentSubmitting.value = true
  commentError.value = ''
  try {
    await soupApi.createComment(soup.value.id, commentText.value.trim())
    commentText.value = ''
    await loadComments()
  } catch (cause: any) {
    commentError.value = cause.response?.data?.detail?.message || cause.response?.data?.detail || '评论发送失败，请先登录'
  } finally {
    commentSubmitting.value = false
  }
}
function startReply(root: Comment, target: Comment) {
  replyParentId.value = root.id
  const username = target.author?.username
  replyText.value = username ? `@${username} ` : ''
  commentError.value = ''
}
function cancelReply() {
  replyParentId.value = null
  replyText.value = ''
}
async function submitReply() {
  if (!soup.value || !replyParentId.value || !replyText.value.trim()) return
  replySubmitting.value = true
  commentError.value = ''
  try {
    await soupApi.createComment(soup.value.id, replyText.value.trim(), replyParentId.value)
    cancelReply()
    await loadComments()
  } catch (cause: any) {
    commentError.value = cause.response?.data?.detail?.message || cause.response?.data?.detail || '回复发送失败，请先登录'
  } finally {
    replySubmitting.value = false
  }
}
onMounted(() => load())
</script>
