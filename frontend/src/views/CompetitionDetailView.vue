<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftIcon } from '@heroicons/vue/24/outline'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime, parseUtcDateTime } from '@/utils/datetime'
import type { Competition } from '@/types'
const route = useRoute(); const router = useRouter(); const competition = ref<Competition | null>(null); const loading = ref(true); const error = ref(''); const settling = ref(false); const settleMessage = ref('')
const auth = useAuthStore()
const canSettle = computed(() => auth.isAdmin
  && competition.value !== null
  && competition.value.settled_at === null
  && Date.now() >= parseUtcDateTime(competition.value.end_time).getTime())
async function load() { loading.value = true; error.value = ''; try { competition.value = (await http.get<Competition>(`/competitions/${route.params.id}`)).data } catch (cause) { error.value = extractApiError(cause, '比赛不存在或无法加载') } finally { loading.value = false } }
async function settle() { settling.value = true; settleMessage.value = ''; try { competition.value = (await http.post<Competition>(`/competitions/${route.params.id}/settle`)).data; settleMessage.value = '比赛已结算' } catch (cause) { settleMessage.value = extractApiError(cause, '结算失败') } finally { settling.value = false } }
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
        <button class="mb-5 inline-flex items-center gap-1 text-sm text-blue-600" @click="router.push('/competitions')"><ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />返回比赛列表</button>
        <section class="surface-card p-5 sm:p-8">
          <div class="flex flex-wrap items-start justify-between gap-4">
            <div class="min-w-0 flex-1">
              <span class="text-sm text-blue-600">比赛 #{{ competition.id }}</span>
              <h1 class="mt-2 break-words text-2xl font-bold sm:text-3xl">{{ competition.name }}</h1>
            </div>
            <span class="shrink-0 rounded-full bg-blue-50 px-3 py-1 text-sm text-blue-700">{{ competition.status }}</span>
          </div>
          <p class="mt-6 break-words whitespace-pre-wrap leading-7 text-slate-700 dark:text-slate-200">{{ competition.description }}</p>
          <dl class="mt-8 grid gap-4 border-t border-slate-200 pt-6 sm:grid-cols-3">
            <div><dt class="text-sm text-slate-500">时间（UTC+8）</dt><dd class="mt-1 text-sm">{{ formatChinaDateTime(competition.start_time) }}<br>至 {{ formatChinaDateTime(competition.end_time) }}</dd></div>
            <div><dt class="text-sm text-slate-500">评分方式</dt><dd class="mt-1">平均分 · 前 {{ competition.top_n }} 名</dd></div>
            <div><dt class="text-sm text-slate-500">标签 ID</dt><dd class="mt-1 break-words">{{ competition.required_tag_ids.join('、') }}</dd></div>
          </dl>
          <div class="mt-8 flex flex-wrap items-center gap-3">
            <button v-if="canSettle" class="btn-secondary" :disabled="settling" @click="settle">{{ settling ? '结算中…' : '管理员结算' }}</button>
            <span v-if="settleMessage" class="min-w-0 break-words text-sm" :class="settleMessage.includes('失败') ? 'text-red-600' : 'text-emerald-600'">{{ settleMessage }}</span>
          </div>
        </section>
        <section class="surface-card mt-6 p-5 sm:p-6">
          <h2 class="section-title break-words">已收录作品（{{ (competition as any).entries?.length || 0 }}）</h2>
          <div v-if="!(competition as any).entries?.length" class="py-8 text-center text-slate-500">暂时没有收录作品。</div>
          <div v-else class="mt-4 overflow-x-auto">
            <table class="min-w-full text-left text-sm">
              <thead><tr class="border-b border-slate-200 text-slate-500"><th class="px-3 py-2">排名</th><th class="px-3 py-2">作品</th><th class="px-3 py-2">作者 UID</th><th class="px-3 py-2">得分</th></tr></thead>
              <tbody><tr v-for="entry in (competition as any).entries" :key="entry.id" class="border-b border-slate-100"><td class="px-3 py-3">{{ entry.rank || '未结算' }}</td><td class="px-3 py-3"><button class="text-blue-600" @click="router.push(`/soups/${entry.soup_id}`)">#{{ entry.soup_id }}</button></td><td class="px-3 py-3">{{ entry.author_uid }}</td><td class="px-3 py-3">{{ entry.final_score.toFixed(2) }}</td></tr></tbody>
            </table>
          </div>
        </section>
      </template>
    </div>
  </main>
</template>
