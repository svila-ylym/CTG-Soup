<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftIcon, ChatBubbleOvalLeftIcon, EyeIcon, HeartIcon } from '@heroicons/vue/24/outline'
import { postsApi } from '@/api/posts'
import MentionText from '@/components/MentionText.vue'
import { extractApiError } from '@/utils/auth'
import type { Comment, Post } from '@/types'

const route = useRoute()
const router = useRouter()
const post = ref<Post | null>(null)
const comments = ref<Comment[]>([])
const commentText = ref('')
const replyText = ref('')
const replyParentId = ref<number | null>(null)
const loading = ref(true)
const commentsLoading = ref(false)
const submitting = ref(false)
const replySubmitting = ref(false)
const error = ref('')
const commentError = ref('')

async function load() {
  loading.value = true
  error.value = ''
  try {
    post.value = (await postsApi.get(Number(route.params.id))).data
    await loadComments()
  } catch (reason) {
    error.value = extractApiError(reason, '帖子不存在或暂时不可用')
  } finally {
    loading.value = false
  }
}

async function loadComments() {
  if (!post.value) return
  commentsLoading.value = true
  try {
    comments.value = (await postsApi.comments(post.value.id)).data.items
  } catch (reason) {
    commentError.value = extractApiError(reason, '评论加载失败')
  } finally {
    commentsLoading.value = false
  }
}

async function submitComment() {
  if (!post.value || !commentText.value.trim()) return
  submitting.value = true
  commentError.value = ''
  try {
    const created = (await postsApi.createComment(post.value.id, commentText.value)).data
    comments.value = [created, ...comments.value]
    post.value.comment_count += 1
    commentText.value = ''
  } catch (reason) {
    commentError.value = extractApiError(reason, '评论发送失败，请先登录')
  } finally {
    submitting.value = false
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
  if (!post.value || !replyParentId.value || !replyText.value.trim()) return
  replySubmitting.value = true
  commentError.value = ''
  try {
    await postsApi.createComment(post.value.id, replyText.value.trim(), replyParentId.value)
    post.value.comment_count += 1
    cancelReply()
    await loadComments()
  } catch (reason) {
    commentError.value = extractApiError(reason, '回复发送失败，请先登录')
  } finally {
    replySubmitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <div v-if="loading" class="py-20 text-center text-slate-500">正在加载帖子…</div>
      <div v-else-if="error" class="py-20 text-center">
        <p class="text-red-600">{{ error }}</p>
        <button class="btn-secondary mt-4" type="button" @click="load">重新加载</button>
      </div>
      <template v-else-if="post">
        <article class="border-b border-slate-200 pb-8 dark:border-neutral-800">
          <button class="mb-5 inline-flex items-center gap-1 text-sm text-blue-600" type="button" @click="router.back()"><ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />返回论坛</button>
          <div class="flex flex-wrap gap-2 text-sm text-slate-500">
            <span>{{ post.section }}</span><span>·</span>
            <router-link :to="`/profile/${post.author_uid}`" class="hover:underline">
              {{ post.author?.nickname || post.author?.username || `用户 ${post.author_uid}` }}
            </router-link>
            <time>· {{ new Date(post.created_at).toLocaleString() }}</time>
          </div>
          <h1 class="mt-4 break-words text-2xl font-bold sm:text-3xl">{{ post.title }}</h1>
          <p class="mt-6 break-words whitespace-pre-wrap leading-8 text-slate-700 dark:text-slate-200">
            <MentionText :text="post.content" :mentions="post.mentions" />
          </p>
          <div class="mt-8 flex flex-wrap gap-x-5 gap-y-2 border-t border-slate-200 pt-4 text-sm text-slate-500 dark:border-neutral-800">
            <span class="inline-flex items-center gap-1"><HeartIcon class="h-4 w-4" aria-hidden="true" />{{ post.like_count }}</span><span class="inline-flex items-center gap-1"><ChatBubbleOvalLeftIcon class="h-4 w-4" aria-hidden="true" />{{ post.comment_count }}</span><span class="inline-flex items-center gap-1"><EyeIcon class="h-4 w-4" aria-hidden="true" />{{ post.view_count }}</span>
          </div>
        </article>

        <section class="py-7">
          <h2 class="section-title">评论</h2>
          <form class="mt-4 flex flex-col gap-3 sm:flex-row" @submit.prevent="submitComment">
            <textarea
              v-model="commentText"
              class="form-control min-h-24 flex-1"
              maxlength="5000"
              aria-label="评论内容"
            ></textarea>
            <button class="btn-primary self-end" :disabled="submitting || !commentText.trim()">
              {{ submitting ? '发送中…' : '发表评论' }}
            </button>
          </form>
          <p v-if="commentError" class="mt-3 text-sm text-red-600">{{ commentError }}</p>
          <p v-if="commentsLoading" class="py-8 text-center text-slate-500">评论加载中…</p>
          <p v-else-if="!comments.length" class="py-8 text-center text-slate-500">暂无评论</p>
          <div v-else class="mt-6 divide-y divide-slate-200 dark:divide-neutral-800">
            <article v-for="comment in comments" :key="comment.id" class="py-5">
              <div class="flex items-center justify-between gap-3 text-sm">
                <router-link :to="`/profile/${comment.author_uid}`" class="font-semibold hover:underline">
                  {{ comment.author?.nickname || comment.author?.username || `用户 ${comment.author_uid}` }}
                </router-link>
                <time class="text-xs text-slate-500">{{ new Date(comment.created_at).toLocaleString() }}</time>
              </div>
              <p class="mt-2 break-words whitespace-pre-wrap text-slate-700 dark:text-slate-200">
                <MentionText :text="comment.content" :mentions="comment.mentions" />
              </p>
              <button class="mt-2 text-xs font-medium text-blue-600 hover:underline" type="button" @click="startReply(comment, comment)">回复</button>
              <div v-for="reply in comment.replies || []" :key="reply.id" class="mt-3 border-l-2 border-blue-200 pl-4">
                <div class="flex flex-wrap items-center justify-between gap-2 text-sm">
                  <router-link :to="`/profile/${reply.author_uid}`" class="font-semibold hover:underline">{{ reply.author?.nickname || reply.author?.username || `用户 ${reply.author_uid}` }}</router-link>
                  <time class="text-xs text-slate-500">{{ new Date(reply.created_at).toLocaleString() }}</time>
                </div>
                <p class="mt-1 break-words whitespace-pre-wrap text-sm text-slate-700 dark:text-slate-200"><MentionText :text="reply.content" :mentions="reply.mentions" /></p>
                <button class="mt-1 text-xs font-medium text-blue-600 hover:underline" type="button" @click="startReply(comment, reply)">回复</button>
              </div>
              <form v-if="replyParentId === comment.id" class="mt-4 flex flex-col gap-2 sm:flex-row" @submit.prevent="submitReply">
                <textarea v-model="replyText" class="form-control min-h-20 flex-1" maxlength="5000" aria-label="回复内容" placeholder="回复这条评论"></textarea>
                <div class="flex items-end gap-2"><button class="btn-primary" :disabled="replySubmitting || !replyText.trim()">{{ replySubmitting ? '发送中…' : '发送回复' }}</button><button class="btn-secondary" type="button" :disabled="replySubmitting" @click="cancelReply">取消</button></div>
              </form>
            </article>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
