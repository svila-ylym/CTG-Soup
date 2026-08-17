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
              <div class="flex flex-wrap items-center gap-3">
                <h1 class="break-words text-2xl font-bold sm:text-3xl" :class="soup.is_hall_of_fame ? 'hall-title' : 'text-gray-900 dark:text-white'"><LinkifiedText :text="soup.title" /></h1>
                <span v-if="soup.is_hall_of_fame" class="hall-seal" aria-label="殿堂神汤">神汤</span>
              </div>
              <p v-if="soup.collection" class="mt-2 break-words text-sm text-slate-500">
                来源于
                <router-link class="font-medium text-blue-600 hover:underline" :to="`/collections/${soup.collection.id}`">「{{ soup.collection.name }}」合集</router-link>
              </p>
              <div class="mt-3 flex flex-wrap gap-2">
                <span :class="genreBadgeClass(soup.genre)">流派 · {{ soup.genre }}</span>
                <span :class="soupColorBadgeClass(soup.soup_color)">汤色 · {{ soup.soup_color }}</span>
              </div>
              <div v-if="soup.tags.length" class="mt-3 flex flex-wrap gap-2" aria-label="标签">
                <span
                  v-for="tag in soup.tags"
                  :key="tag.id"
                  class="max-w-full break-all rounded-full bg-blue-100 px-2 py-1 text-xs text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
                >#{{ tag.name }}</span>
              </div>
            </div>
            <div class="shrink-0 text-right text-sm text-gray-500">
              <div class="text-2xl font-semibold text-amber-500">{{ displayScore.toFixed(1) }} 分</div>
              <div>{{ soup.rating_count }} 人评分</div>
              <button class="mt-2 inline-flex items-center gap-1 text-sm font-medium text-blue-600 hover:text-blue-700" type="button" @click="openRatings"><UserGroupIcon class="h-4 w-4" aria-hidden="true" />查看评分人</button>
            </div>
          </div>

          <section class="mt-8">
            <h2 class="text-lg font-semibold text-gray-900 dark:text-white mb-3">谜面</h2>
            <p v-if="soup.puzzle" class="break-words whitespace-pre-wrap leading-7 text-gray-700 dark:text-gray-300"><LinkifiedText :text="soup.puzzle" /></p>
            <div v-if="soup.puzzle_images.length" class="mt-4 grid gap-4 sm:grid-cols-2">
              <a v-for="(image, index) in soup.puzzle_images" :key="image.id" :href="image.public_url" target="_blank" rel="noopener noreferrer" class="block bg-slate-50 dark:bg-neutral-900">
                <img :src="image.public_url" :alt="`${soup.title} 谜面图片 ${index + 1}`" class="max-h-[32rem] w-full object-contain">
              </a>
            </div>
          </section>

          <dl class="mt-6 grid gap-4 border-y border-slate-200 py-5 dark:border-neutral-800 sm:grid-cols-2">
            <div class="min-w-0">
              <dt class="text-sm font-medium text-slate-500">主要人物</dt>
              <dd class="mt-1 break-words whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200"><LinkifiedText :text="soup.main_player_count || '未填写'" /></dd>
            </div>
            <div class="min-w-0">
              <dt class="text-sm font-medium text-slate-500">次要人物</dt>
              <dd class="mt-1 break-words whitespace-pre-wrap text-sm text-slate-800 dark:text-slate-200"><LinkifiedText :text="soup.secondary_player_count || '未填写'" /></dd>
            </div>
          </dl>

          <section class="mt-8 rounded-lg border border-dashed border-amber-300 bg-amber-50/60 p-5 dark:border-amber-800 dark:bg-amber-950/30">
            <div class="flex items-center justify-between gap-4">
              <h2 class="text-lg font-semibold text-amber-950 dark:text-amber-100">汤底</h2>
              <button v-if="!revealed" :disabled="revealing" class="rounded-md bg-amber-700 px-4 py-2 text-sm text-white hover:bg-amber-800 disabled:cursor-not-allowed disabled:opacity-60" @click="reveal">
                {{ revealing ? '加载中…' : '揭示汤底' }}
              </button>
            </div>
            <p v-if="revealed && soup.solution" class="mt-3 break-words whitespace-pre-wrap leading-7 text-gray-700 dark:text-gray-300"><LinkifiedText :text="soup.solution" /></p>
            <div v-if="revealed && soup.solution_images.length" class="mt-4 grid gap-4 sm:grid-cols-2">
              <a v-for="(image, index) in soup.solution_images" :key="image.id" :href="image.public_url" target="_blank" rel="noopener noreferrer" class="block bg-white/70 dark:bg-neutral-900">
                <img :src="image.public_url" :alt="`${soup.title} 汤底图片 ${index + 1}`" class="max-h-[32rem] w-full object-contain">
              </a>
            </div>
            <p v-if="!revealed" class="mt-3 text-amber-800 dark:text-amber-200">汤底已隐藏，确认后才会显示。</p>
            <p v-if="revealError" class="mt-3 text-sm text-red-600 dark:text-red-400">{{ revealError }}</p>
          </section>

          <div class="mt-8 flex flex-wrap items-center gap-3 border-t border-gray-100 dark:border-neutral-800 pt-5">
            <div class="w-full min-w-0 sm:max-w-md">
              <div class="flex items-center justify-between gap-3 text-sm">
                <label class="font-medium text-gray-700 dark:text-gray-200" for="rating-slider">评分</label>
                <output class="shrink-0 font-semibold text-amber-600 dark:text-amber-400" for="rating-slider">{{ score.toFixed(1) }} 分</output>
              </div>
              <input
                id="rating-slider"
                v-model.number="score"
                aria-label="评分"
                class="mt-2 h-2 w-full cursor-pointer accent-amber-600 disabled:cursor-not-allowed disabled:opacity-60"
                type="range"
                min="1"
                max="10"
                step="0.5"
                :disabled="ratingSubmitting"
              >
              <div class="mt-1 flex justify-between text-xs text-slate-500" aria-hidden="true">
                <span>1 分</span>
                <span>10 分</span>
              </div>
              <div class="mt-3 flex min-h-9 flex-wrap items-center gap-3">
                <p v-if="hasRating" class="text-sm font-medium text-emerald-700 dark:text-emerald-400">当前评分 {{ soup.my_rating?.toFixed(1) }} 分，可随时调整</p>
                <button class="btn-primary" type="button" :disabled="ratingSubmitting || !ratingChanged" @click="openRatingDialog">{{ hasRating ? '修改评分' : '确认评分' }}</button>
              </div>
            </div>
            <button class="inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 py-2 text-sm" :class="soup.is_liked ? 'bg-red-100 text-red-600' : 'bg-gray-100 text-gray-700 dark:bg-neutral-800 dark:text-gray-200'" @click="toggle('like')"><HeartIcon class="h-4 w-4" aria-hidden="true" />{{ soup.like_count }}</button>
            <button class="inline-flex min-h-9 items-center gap-1.5 rounded-md px-3 py-2 text-sm" :class="soup.is_favorited ? 'bg-amber-100 text-amber-700' : 'bg-gray-100 text-gray-700 dark:bg-neutral-800 dark:text-gray-200'" @click="toggle('favorite')"><BookmarkIcon class="h-4 w-4" aria-hidden="true" />{{ soup.favorite_count }}</button>
            <div class="ml-auto flex items-center gap-4">
              <router-link v-if="soup.can_edit" class="inline-flex min-h-9 items-center gap-1.5 text-sm font-medium text-blue-600 hover:text-blue-700" :to="`/soups/${soup.id}/edit`"><PencilSquareIcon class="h-4 w-4" aria-hidden="true" />修改</router-link>
              <button v-if="soup.can_manage" class="inline-flex min-h-9 items-center gap-1.5 text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-50" type="button" :disabled="deleting" @click="deleteSoup"><TrashIcon class="h-4 w-4" aria-hidden="true" />{{ deleting ? '删除中…' : '删除' }}</button>
              <button v-if="auth.isAuthenticated && soup.author_uid !== auth.user?.uid" class="inline-flex min-h-9 items-center gap-1.5 text-sm text-gray-500 hover:text-red-600" type="button" @click="reportOpen = true"><FlagIcon class="h-4 w-4" aria-hidden="true" />举报</button>
            </div>
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
            <article v-for="item in comments" :id="`comment-${item.id}`" :key="item.id" class="py-4">
              <div class="flex items-center justify-between gap-3 text-sm">
                <div class="flex min-w-0 items-center gap-2"><router-link :to="`/profile/${item.author_uid}`" class="font-semibold hover:text-blue-600 hover:underline">{{ item.author?.nickname || item.author?.username || `用户 ${item.author_uid}` }}</router-link><LevelBadge :level="item.author?.level" :band="item.author?.level_band" compact /></div>
                <time class="text-xs text-slate-500">{{ formatChinaDateTime(item.created_at) }}</time>
              </div>
              <p class="mt-2 break-words whitespace-pre-wrap text-slate-700 dark:text-slate-200"><MentionText :text="item.content" :mentions="item.mentions" /></p>
              <div class="mt-2 flex items-center gap-4"><button class="text-xs font-medium text-blue-600 hover:underline" type="button" @click="startReply(item, item)">回复</button><button v-if="canDeleteComment(item)" class="inline-flex items-center gap-1 text-xs text-red-600" type="button" :disabled="deletingCommentId === item.id" @click="deleteComment(item)"><TrashIcon class="h-3.5 w-3.5" aria-hidden="true" />删除</button><button v-if="auth.isAuthenticated && item.author_uid !== auth.user?.uid" class="inline-flex items-center gap-1 text-xs text-red-600" type="button" @click="commentReportId = item.id"><FlagIcon class="h-3.5 w-3.5" aria-hidden="true" />举报</button></div>
              <div v-for="reply in item.replies || []" :id="`comment-${reply.id}`" :key="reply.id" class="mt-3 break-words border-l-2 border-blue-200 pl-3 text-sm">
                <div class="flex flex-wrap items-center justify-between gap-2">
                  <div class="flex min-w-0 items-center gap-2"><router-link :to="`/profile/${reply.author_uid}`" class="font-semibold hover:text-blue-600 hover:underline">{{ reply.author?.nickname || reply.author?.username || `用户 ${reply.author_uid}` }}</router-link><LevelBadge :level="reply.author?.level" :band="reply.author?.level_band" compact /></div>
                  <time class="text-xs text-slate-500">{{ formatChinaDateTime(reply.created_at) }}</time>
                </div>
                <p class="mt-1 whitespace-pre-wrap"><MentionText :text="reply.content" :mentions="reply.mentions" /></p>
                <div class="mt-1 flex items-center gap-4"><button class="text-xs font-medium text-blue-600 hover:underline" type="button" @click="startReply(item, reply)">回复</button><button v-if="canDeleteComment(reply)" class="inline-flex items-center gap-1 text-xs text-red-600" type="button" :disabled="deletingCommentId === reply.id" @click="deleteComment(reply)"><TrashIcon class="h-3.5 w-3.5" aria-hidden="true" />删除</button><button v-if="auth.isAuthenticated && reply.author_uid !== auth.user?.uid" class="inline-flex items-center gap-1 text-xs text-red-600" type="button" @click="commentReportId = reply.id"><FlagIcon class="h-3.5 w-3.5" aria-hidden="true" />举报</button></div>
              </div>
              <div v-if="replyParentId === item.id" class="mt-4 flex flex-col gap-2 sm:flex-row">
                <textarea v-model="replyText" class="form-control min-h-20 flex-1" maxlength="2000" placeholder="回复这条评论" aria-label="回复内容"></textarea>
                <div class="flex items-end gap-2"><button class="btn-primary" type="button" :disabled="replySubmitting || !replyText.trim()" @click="submitReply">{{ replySubmitting ? '发送中…' : '发送回复' }}</button><button class="btn-secondary" type="button" :disabled="replySubmitting" @click="cancelReply">取消</button></div>
              </div>
            </article>
          </div>
        </section>
        <SoupRatingsDialog
          :open="ratingsOpen"
          :soup-id="soup.id"
          :soup-title="soup.title"
          @close="ratingsOpen = false"
        />
        <TransitionRoot appear :show="ratingDialogOpen" as="template">
          <Dialog as="div" class="relative z-[70]" @close="closeRatingDialog">
            <TransitionChild
              as="template"
              enter="duration-150 ease-out"
              enter-from="opacity-0"
              enter-to="opacity-100"
              leave="duration-100 ease-in"
              leave-from="opacity-100"
              leave-to="opacity-0"
            >
              <div class="fixed inset-0 bg-black/45" />
            </TransitionChild>

            <div class="fixed inset-0 overflow-y-auto p-4">
              <div class="flex min-h-full items-center justify-center">
                <TransitionChild
                  as="template"
                  enter="duration-150 ease-out"
                  enter-from="opacity-0 translate-y-2"
                  enter-to="opacity-100 translate-y-0"
                  leave="duration-100 ease-in"
                  leave-from="opacity-100 translate-y-0"
                  leave-to="opacity-0 translate-y-2"
                >
                  <DialogPanel class="w-full max-w-md rounded-md bg-white p-5 shadow-xl dark:bg-neutral-900 sm:p-6">
                    <DialogTitle class="text-lg font-semibold text-slate-900 dark:text-white">{{ hasRating ? '修改评分' : '确认评分' }}</DialogTitle>
                    <p v-if="hasRating" class="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
                      你将评分从 <strong>{{ soup.my_rating?.toFixed(1) }} 分</strong> 修改为 <strong class="text-amber-600 dark:text-amber-400">{{ score.toFixed(1) }} 分</strong>。保存后仍可再次调整。
                    </p>
                    <p v-else class="mt-3 text-sm leading-6 text-slate-600 dark:text-slate-300">
                      你将提交 <strong class="text-amber-600 dark:text-amber-400">{{ score.toFixed(1) }} 分</strong>。保存后仍可按新的感受调整评分。
                    </p>
                    <p v-if="ratingError" class="mt-3 break-words text-sm text-red-600 dark:text-red-400">{{ ratingError }}</p>
                    <div class="mt-6 flex flex-wrap justify-end gap-3">
                      <button class="btn-secondary" type="button" :disabled="ratingSubmitting" @click="closeRatingDialog">取消</button>
                      <button class="btn-primary" type="button" :disabled="ratingSubmitting" @click="submitRating">
                        {{ ratingSubmitting ? '提交中…' : hasRating ? '确认修改' : '确认并提交' }}
                      </button>
                    </div>
                  </DialogPanel>
                </TransitionChild>
              </div>
            </div>
          </Dialog>
        </TransitionRoot>
        <ReportDialog :open="reportOpen" target-type="soup" :target-id="soup.id" @close="reportOpen = false" />
        <ReportDialog v-if="commentReportId" :open="true" target-type="comment" :target-id="commentReportId" @close="commentReportId = null" />
      </template>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { BookmarkIcon, FlagIcon, HeartIcon, PencilSquareIcon, TrashIcon, UserGroupIcon } from '@heroicons/vue/24/outline'
import { Dialog, DialogPanel, DialogTitle, TransitionChild, TransitionRoot } from '@headlessui/vue'
import { soupApi } from '@/api/soup'
import { formatChinaDateTime } from '@/utils/datetime'
import type { Comment, TurtleSoup } from '@/types'
import ReportDialog from '@/components/ReportDialog.vue'
import SoupRatingsDialog from '@/components/SoupRatingsDialog.vue'
import MentionText from '@/components/MentionText.vue'
import LevelBadge from '@/components/LevelBadge.vue'
import LinkifiedText from '@/components/LinkifiedText.vue'
import { extractApiError } from '@/utils/auth'
import { useAuthStore } from '@/stores/auth'
import { genreBadgeClass, soupColorBadgeClass } from '@/utils/soupMetadata'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const soup = ref<TurtleSoup | null>(null)
const loading = ref(true)
const error = ref('')
const revealed = ref(false)
const revealing = ref(false)
const revealError = ref('')
const score = ref(5)
const ratingDialogOpen = ref(false)
const ratingSubmitting = ref(false)
const ratingError = ref('')
const reportOpen = ref(false)
const comments = ref<Comment[]>([])
const commentsLoading = ref(false)
const commentSubmitting = ref(false)
const commentText = ref('')
const replyText = ref('')
const replyParentId = ref<number | null>(null)
const replySubmitting = ref(false)
const commentError = ref('')
const deleting = ref(false)
const deletingCommentId = ref<number | null>(null)
const commentReportId = ref<number | null>(null)
const ratingsOpen = ref(false)
const displayScore = computed(() => soup.value?.average_score ?? 0)
const hasRating = computed(() => soup.value?.my_rating != null)
const ratingChanged = computed(() => !hasRating.value || score.value !== soup.value?.my_rating)

async function load(revealSolution = false) {
  loading.value = true
  error.value = ''
  try {
    const response = await soupApi.getById(Number(route.params.id), revealSolution)
    soup.value = response.data
    revealed.value = soup.value.solution != null
    score.value = soup.value.my_rating ?? 5
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
function openRatingDialog() {
  if (!ratingChanged.value || ratingSubmitting.value) return
  ratingError.value = ''
  ratingDialogOpen.value = true
}
function closeRatingDialog() {
  if (ratingSubmitting.value) return
  ratingDialogOpen.value = false
  ratingError.value = ''
}
async function submitRating() {
  if (!soup.value || !ratingChanged.value || ratingSubmitting.value || score.value < 1 || score.value > 10 || score.value * 2 % 1 !== 0) return
  ratingSubmitting.value = true
  ratingError.value = ''
  try {
    const response = await soupApi.rate(soup.value.id, score.value)
    soup.value = { ...soup.value, ...response.data }
    score.value = response.data.my_rating
    ratingDialogOpen.value = false
  } catch (cause: any) {
    const detail = cause.response?.data?.detail
    ratingError.value = detail?.message || (typeof detail === 'string' ? detail : '') || '评分提交失败'
  } finally {
    ratingSubmitting.value = false
  }
}
async function toggle(kind: 'like' | 'favorite') {
  if (!soup.value) return
  const active = kind === 'like' ? !!soup.value.is_liked : !!soup.value.is_favorited
  const response = await soupApi.setInteraction(soup.value.id, kind, !active)
  soup.value = { ...soup.value, ...response.data }
}
async function deleteSoup() {
  if (!soup.value?.can_manage || deleting.value) return
  if (!window.confirm(`确定删除海龟汤“${soup.value.title}”吗？删除后将不再公开显示。`)) return
  deleting.value = true
  error.value = ''
  try {
    await soupApi.delete(soup.value.id)
    await router.push('/soups')
  } catch (cause) {
    error.value = extractApiError(cause, '海龟汤删除失败')
  } finally {
    deleting.value = false
  }
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
function openRatings() {
  if (!soup.value) return
  ratingsOpen.value = true
}
function canDeleteComment(comment: Comment) {
  return Boolean(auth.user && (comment.author_uid === auth.user.uid || auth.isAdmin))
}
async function deleteComment(comment: Comment) {
  if (!soup.value || !canDeleteComment(comment) || !window.confirm('确定删除这条评论吗？')) return
  deletingCommentId.value = comment.id
  commentError.value = ''
  try {
    await soupApi.deleteComment(soup.value.id, comment.id)
    await loadComments()
  } catch (cause) {
    commentError.value = extractApiError(cause, '评论删除失败')
  } finally {
    deletingCommentId.value = null
  }
}
async function submitComment() {
  if (!soup.value || !commentText.value.trim()) return
  commentSubmitting.value = true
  commentError.value = ''
  try {
    await soupApi.createComment(soup.value.id, commentText.value)
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
    await soupApi.createComment(soup.value.id, replyText.value, replyParentId.value)
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
