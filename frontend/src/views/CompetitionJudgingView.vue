<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftIcon, ArrowPathIcon, CheckIcon } from '@heroicons/vue/24/outline'
import http from '@/api/http'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime, parseUtcDateTime } from '@/utils/datetime'
import type { Competition, CompetitionJudging, CompetitionJudgingEntry } from '@/types'

const route = useRoute()
const router = useRouter()
const judging = ref<CompetitionJudging | null>(null)
const loading = ref(true)
const error = ref('')
const savingEntryId = ref<number | null>(null)
const rowMessages = ref<Record<number, string>>({})
const settling = ref(false)
const settleMessage = ref('')

const isOpen = computed(() => Boolean(
  judging.value
  && Date.now() >= parseUtcDateTime(judging.value.scoring_at).getTime(),
))
const editable = computed(() => isOpen.value && !judging.value?.settled_at)
const complete = computed(() => Boolean(
  judging.value
  && judging.value.scored_count === judging.value.total_count,
))

async function load() {
  loading.value = true
  error.value = ''
  try {
    judging.value = (await http.get<CompetitionJudging>(`/competitions/${route.params.id}/judging`)).data
  } catch (cause) {
    error.value = extractApiError(cause, '比赛方评分暂时无法加载')
  } finally {
    loading.value = false
  }
}

function validScore(value: number | null) {
  return value !== null
    && Number.isFinite(value)
    && value >= 1
    && value <= 10
    && Number.isInteger(value * 2)
}

async function save(entry: CompetitionJudgingEntry) {
  rowMessages.value[entry.entry_id] = ''
  if (!validScore(entry.judge_score)) {
    rowMessages.value[entry.entry_id] = '请输入 1–10 之间的 0.5 倍数'
    return
  }
  savingEntryId.value = entry.entry_id
  try {
    const response = await http.put<CompetitionJudgingEntry>(
      `/competitions/${route.params.id}/entries/${entry.entry_id}/judge-score`,
      { score: entry.judge_score },
    )
    const previousScored = entry.judged_at !== null
    Object.assign(entry, response.data)
    if (judging.value && !previousScored) judging.value.scored_count += 1
    rowMessages.value[entry.entry_id] = '已保存'
  } catch (cause) {
    rowMessages.value[entry.entry_id] = extractApiError(cause, '保存失败')
  } finally {
    savingEntryId.value = null
  }
}

async function settle() {
  settling.value = true
  settleMessage.value = ''
  try {
    await http.post<Competition>(`/competitions/${route.params.id}/settle`)
    settleMessage.value = '比赛已结算'
    await load()
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
    <div class="page-container max-w-6xl">
      <button class="mb-6 inline-flex items-center gap-1 text-sm text-blue-600" type="button" @click="router.push(`/competitions/${route.params.id}`)">
        <ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />
        返回比赛详情
      </button>

      <p v-if="loading" class="py-16 text-center text-slate-500">正在加载评分工作台…</p>
      <div v-else-if="error" class="border-y border-slate-200 py-12 text-center dark:border-neutral-800">
        <p class="break-words text-red-600">{{ error }}</p>
        <button class="btn-secondary mt-4" type="button" @click="load">重新加载</button>
      </div>

      <template v-else-if="judging">
        <div class="flex flex-wrap items-end justify-between gap-4">
          <div class="min-w-0">
            <p class="text-sm text-blue-600">比赛方评分</p>
            <h1 class="section-title mt-1 break-words">{{ judging.competition_name }}</h1>
            <p class="mt-2 text-sm text-slate-500">{{ formatChinaDateTime(judging.scoring_at) }} 开放</p>
          </div>
          <div class="shrink-0 text-right">
            <strong class="block text-2xl">{{ judging.scored_count }} / {{ judging.total_count }}</strong>
            <span class="text-xs text-slate-500">已完成评分</span>
          </div>
        </div>

        <p v-if="!isOpen" class="mt-6 border-l-4 border-amber-500 bg-amber-50 px-4 py-3 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-300">尚未到评分日期，当前仅可查看参赛作品。</p>
        <p v-else-if="judging.settled_at" class="mt-6 border-l-4 border-emerald-500 bg-emerald-50 px-4 py-3 text-sm text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-300">比赛已结算，评分记录已锁定。</p>

        <div class="mt-7 overflow-x-auto border-y border-slate-200 dark:border-neutral-800">
          <table class="min-w-[860px] w-full text-left text-sm">
            <thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-3 py-3">作品</th><th class="px-3 py-3">作者 UID</th><th class="w-40 px-3 py-3">比赛方评分</th><th class="px-3 py-3">最后保存</th><th class="w-32 px-3 py-3">操作</th></tr></thead>
            <tbody>
              <tr v-for="entry in judging.entries" :key="entry.entry_id" class="border-b border-slate-100 align-top last:border-0 dark:border-neutral-900">
                <td class="px-3 py-4"><router-link class="font-medium text-blue-600 hover:underline" :class="entry.is_hall_of_fame ? 'hall-title' : ''" :to="`/soups/${entry.soup_id}`">{{ entry.soup_title }}</router-link></td>
                <td class="px-3 py-4">{{ entry.author_uid }}</td>
                <td class="px-3 py-3"><input v-model.number="entry.judge_score" class="form-control w-28" type="number" min="1" max="10" step="0.5" :disabled="!editable" :aria-label="`${entry.soup_title} 的评分`"></td>
                <td class="px-3 py-4 text-xs text-slate-500"><template v-if="entry.judged_at">{{ formatChinaDateTime(entry.judged_at) }}<span class="block">UID {{ entry.judged_by_uid ?? '已删除用户' }}</span></template><span v-else>未评分</span></td>
                <td class="px-3 py-3"><button class="btn-secondary min-w-24 gap-1 text-xs" type="button" :disabled="!editable || savingEntryId === entry.entry_id" @click="save(entry)"><ArrowPathIcon v-if="savingEntryId === entry.entry_id" class="h-4 w-4 animate-spin" aria-hidden="true" /><CheckIcon v-else class="h-4 w-4" aria-hidden="true" />{{ savingEntryId === entry.entry_id ? '保存中' : '保存' }}</button><p v-if="rowMessages[entry.entry_id]" class="mt-2 max-w-36 break-words text-xs" :class="rowMessages[entry.entry_id] === '已保存' ? 'text-emerald-600' : 'text-red-600'">{{ rowMessages[entry.entry_id] }}</p></td>
              </tr>
            </tbody>
          </table>
        </div>

        <p v-if="!judging.entries.length" class="py-10 text-center text-slate-500">当前没有参赛作品。</p>
        <div class="mt-7 flex flex-wrap items-center gap-3">
          <button v-if="!judging.settled_at" class="btn-primary" type="button" :disabled="!editable || !complete || settling" @click="settle">{{ settling ? '结算中…' : '统一结算' }}</button>
          <span v-if="!complete && judging.total_count" class="text-sm text-slate-500">全部作品评分后才能结算</span>
          <span v-if="settleMessage" class="break-words text-sm" :class="settleMessage.includes('失败') ? 'text-red-600' : 'text-emerald-600'">{{ settleMessage }}</span>
        </div>
      </template>
    </div>
  </main>
</template>
