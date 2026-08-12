<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftIcon, PencilSquareIcon, StarIcon } from '@heroicons/vue/24/outline'
import DOMPurify from 'dompurify'
import LinkifiedText from '@/components/LinkifiedText.vue'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime, parseUtcDateTime } from '@/utils/datetime'
import type { Competition } from '@/types'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const competition = ref<Competition | null>(null)
const loading = ref(true)
const error = ref('')
const settling = ref(false)
const settleMessage = ref('')

const safeDescription = computed(() => DOMPurify.sanitize(
  competition.value?.description || '',
  { USE_PROFILES: { html: true }, ADD_TAGS: ['img'], ADD_ATTR: ['src', 'alt', 'title'] },
))
const canSettle = computed(() => competition.value !== null
  && (auth.isAdmin || competition.value.creator_uid === auth.user?.uid)
  && competition.value.settled_at === null
  && competition.value.score_type === 'average'
  && Date.now() >= parseUtcDateTime(competition.value.end_time).getTime()
)
const canEdit = computed(() => competition.value !== null
  && competition.value.creator_uid === auth.user?.uid
  && competition.value.settled_at === null)
const canJudge = computed(() => competition.value?.score_type === 'independent'
  && Boolean(auth.user)
  && (auth.isAdmin || competition.value?.creator_uid === auth.user?.uid))
const awaitingIndependentSettlement = computed(() => competition.value?.score_type === 'independent'
  && !competition.value?.settled_at)
const rankingLabel = computed(() => competition.value?.settled_at ? '最终排行' : '实时排行')

async function load() {
  loading.value = true
  error.value = ''
  try {
    competition.value = (await http.get<Competition>(`/competitions/${route.params.id}`)).data
  } catch (cause) {
    error.value = extractApiError(cause, '比赛不存在或无法加载')
  } finally {
    loading.value = false
  }
}

async function settle() {
  settling.value = true
  settleMessage.value = ''
  try {
    competition.value = (await http.post<Competition>(`/competitions/${route.params.id}/settle`)).data
    settleMessage.value = '比赛已结算'
  } catch (cause) {
    settleMessage.value = extractApiError(cause, '结算失败')
  } finally {
    settling.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-5xl">
      <div v-if="loading" class="surface-card p-12 text-center text-slate-500">正在加载比赛…</div>
      <div v-else-if="error" class="surface-card p-8 text-center">
        <p class="break-words text-red-600">{{ error }}</p>
        <button class="btn-secondary mt-4" @click="load">重新加载</button>
      </div>

      <template v-else-if="competition">
        <button class="mb-5 inline-flex items-center gap-1 text-sm text-blue-600" @click="router.push('/competitions')">
          <ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />
          返回比赛列表
        </button>

        <section class="surface-card border-t-4 p-5 sm:p-8" :style="{ borderTopColor: competition.competition_color }">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="min-w-0 flex-1">
              <span class="text-sm text-blue-600">比赛 #{{ competition.id }}</span>
              <h1 class="mt-2 break-words text-2xl font-bold sm:text-3xl"><LinkifiedText :text="competition.name" /></h1>
            </div>
            <div class="flex shrink-0 items-center gap-2">
              <span class="h-5 w-5 border border-black/10" :style="{ backgroundColor: competition.competition_color }" :title="competition.competition_color"></span>
              <span class="rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">{{ competition.status }}</span>
            </div>
          </div>

          <div class="competition-description mt-6 break-words whitespace-pre-wrap leading-7 text-slate-700 dark:text-slate-200" v-html="safeDescription"></div>

          <dl class="mt-8 grid gap-5 border-t border-slate-200 pt-6 sm:grid-cols-2 lg:grid-cols-4 dark:border-neutral-800">
            <div><dt class="text-sm text-slate-500">时间（UTC+8）</dt><dd class="mt-1 text-sm">{{ formatChinaDateTime(competition.start_time) }}<br>至 {{ formatChinaDateTime(competition.end_time) }}</dd></div>
            <div><dt class="text-sm text-slate-500">评分</dt><dd class="mt-1">{{ competition.score_type === 'independent' ? '独评' : '平均分' }} · 前 {{ competition.top_n }} 名<span v-if="competition.scoring_at" class="mt-1 block text-xs text-slate-500">{{ formatChinaDateTime(competition.scoring_at) }} 开放评分</span></dd></div>
            <div><dt class="text-sm text-slate-500">必选标签</dt><dd class="mt-1 break-words">{{ competition.required_tags.map(tag => tag.name).join('、') }}</dd></div>
            <div><dt class="text-sm text-slate-500">可选分组</dt><dd class="mt-1 break-words">{{ competition.optional_tags.length ? competition.optional_tags.map(tag => tag.name).join('、') : '无' }}</dd></div>
          </dl>

          <div class="mt-8 flex flex-wrap items-center gap-3">
            <router-link v-if="canEdit" class="btn-secondary gap-2" :to="`/competitions/${competition.id}/edit`"><PencilSquareIcon class="h-4 w-4" aria-hidden="true" />修改比赛</router-link>
            <router-link v-if="canJudge" class="btn-secondary gap-2" :to="`/competitions/${competition.id}/judging`"><StarIcon class="h-4 w-4" aria-hidden="true" />比赛方评分</router-link>
            <button v-if="canSettle" class="btn-secondary" :disabled="settling" @click="settle">{{ settling ? '结算中…' : '结算比赛' }}</button>
            <span v-if="settleMessage" class="min-w-0 break-words text-sm" :class="settleMessage.includes('失败') ? 'text-red-600' : 'text-emerald-600'">{{ settleMessage }}</span>
          </div>
        </section>

        <section v-if="awaitingIndependentSettlement" class="mt-8 border-t border-slate-200 pt-7 dark:border-neutral-800">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div><p class="text-xs font-semibold text-slate-500">独评尚未公开</p><h2 class="section-title mt-1">参赛作品</h2></div>
            <span class="text-sm text-slate-500">已收录 {{ competition.entries?.length || 0 }} 部作品</span>
          </div>
          <p class="mt-3 text-sm text-slate-500">等待比赛方完成评分并统一结算。</p>
          <div v-if="competition.entries?.length" class="mt-4 overflow-x-auto">
            <table class="min-w-full text-left text-sm">
              <thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-3 py-2">作品</th><th class="px-3 py-2">作者 UID</th></tr></thead>
              <tbody><tr v-for="entry in competition.entries" :key="entry.id" class="border-b border-slate-100 dark:border-neutral-900"><td class="px-3 py-3"><button class="text-left text-blue-600 hover:underline" @click="router.push(`/soups/${entry.soup_id}`)">{{ entry.soup_title || '已删除作品' }}</button></td><td class="px-3 py-3">{{ entry.author_uid }}</td></tr></tbody>
            </table>
          </div>
        </section>

        <section v-else class="mt-8 border-t border-slate-200 pt-7 dark:border-neutral-800">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-xs font-semibold text-slate-500">{{ rankingLabel }}</p>
              <h2 class="section-title mt-1">总榜</h2>
            </div>
            <span class="text-sm text-slate-500">已收录 {{ competition.entries?.length || 0 }} 部作品</span>
          </div>
          <p v-if="!competition.rankings.total.length" class="py-8 text-center text-slate-500">暂时没有收录作品。</p>
          <div v-else class="mt-4 overflow-x-auto">
            <table class="min-w-full text-left text-sm">
              <thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-3 py-2">名次</th><th class="px-3 py-2">作品</th><th class="px-3 py-2">作者 UID</th><th class="px-3 py-2 text-right">得分</th></tr></thead>
              <tbody><tr v-for="entry in competition.rankings.total" :key="entry.entry_id" class="border-b border-slate-100 dark:border-neutral-900"><td class="px-3 py-3 font-semibold">{{ entry.rank }}</td><td class="px-3 py-3"><button class="text-left text-blue-600 hover:underline" @click="router.push(`/soups/${entry.soup_id}`)">{{ entry.soup_title || '已删除作品' }}</button></td><td class="px-3 py-3">{{ entry.author_uid }}</td><td class="px-3 py-3 text-right font-medium">{{ entry.final_score.toFixed(2) }}</td></tr></tbody>
            </table>
          </div>
        </section>

        <section v-for="group in competition.rankings.groups" :key="group.tag_id" class="mt-8 border-t border-slate-200 pt-7 dark:border-neutral-800">
          <div class="flex flex-wrap items-end justify-between gap-3">
            <div>
              <p class="text-xs font-semibold text-slate-500">{{ rankingLabel }} · 可选标签 #{{ group.tag_id }}</p>
              <h2 class="section-title mt-1 break-words">{{ group.tag_name }} 分组</h2>
            </div>
            <span class="text-sm text-slate-500">{{ group.entries.length }} 部上榜作品</span>
          </div>
          <p v-if="!group.entries.length" class="py-8 text-center text-slate-500">该分组暂无作品。</p>
          <div v-else class="mt-4 overflow-x-auto">
            <table class="min-w-full text-left text-sm">
              <thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-3 py-2">名次</th><th class="px-3 py-2">作品</th><th class="px-3 py-2">作者 UID</th><th class="px-3 py-2 text-right">得分</th></tr></thead>
              <tbody><tr v-for="entry in group.entries" :key="entry.entry_id" class="border-b border-slate-100 dark:border-neutral-900"><td class="px-3 py-3 font-semibold">{{ entry.rank }}</td><td class="px-3 py-3"><button class="text-left text-blue-600 hover:underline" @click="router.push(`/soups/${entry.soup_id}`)">{{ entry.soup_title || '已删除作品' }}</button></td><td class="px-3 py-3">{{ entry.author_uid }}</td><td class="px-3 py-3 text-right font-medium">{{ entry.final_score.toFixed(2) }}</td></tr></tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
