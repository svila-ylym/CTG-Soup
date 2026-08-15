<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { PlusIcon } from '@heroicons/vue/24/outline'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime } from '@/utils/datetime'
import type { Competition, PageResult } from '@/types'
const router = useRouter(); const competitions = ref<Competition[]>([]); const loading = ref(true); const error = ref(''); const status = ref('')
const auth = useAuthStore()
async function load() { loading.value = true; error.value = ''; try { const res = await http.get<PageResult<Competition>>('/competitions', { params: { page: 1, page_size: 30, status_filter: status.value || undefined } }); competitions.value = res.data.items || [] } catch (cause) { error.value = extractApiError(cause, '比赛暂时无法加载') } finally { loading.value = false } }
onMounted(load)
function statusText(value: string) { return value === 'ongoing' ? '进行中' : value === 'pending' ? '即将开始' : '已结束' }
function descriptionText(value: string) { return value.replace(/<[^>]*>/g, ' ').replace(/\s+/g, ' ').trim() }
</script>
<template>
  <main class="page-shell">
    <div class="page-container">
      <div class="mb-6 flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 class="section-title text-3xl">比赛</h1>
          <p class="mt-2 text-slate-500">按标签参与社区挑战，作品会自动收录。</p>
        </div>
        <div class="flex w-full flex-wrap gap-3 sm:w-auto">
          <router-link v-if="auth.isAdmin" class="btn-primary gap-2" to="/competitions/create">
            <PlusIcon class="h-5 w-5" aria-hidden="true" />
            发布比赛
          </router-link>
          <select v-model="status" class="form-control w-full sm:w-40" @change="load">
            <option value="">全部状态</option>
            <option value="pending">即将开始</option>
            <option value="ongoing">进行中</option>
            <option value="completed">已结束</option>
          </select>
        </div>
      </div>

      <div v-if="loading" class="surface-card p-12 text-center text-slate-500">正在加载比赛…</div>
      <div v-else-if="error" class="surface-card p-8 text-center">
        <p class="break-words text-red-600">{{ error }}</p>
        <button class="btn-secondary mt-4" @click="load">重新加载</button>
      </div>
      <div v-else-if="!competitions.length" class="surface-card p-12 text-center text-slate-500">暂无符合条件的比赛。</div>
      <div v-else class="grid gap-5 md:grid-cols-2 xl:grid-cols-3">
        <article v-for="competition in competitions" :key="competition.id" class="surface-card flex min-h-64 cursor-pointer flex-col overflow-hidden transition hover:border-blue-400" @click="router.push(`/competitions/${competition.id}`)">
          <div class="aspect-[16/7] overflow-hidden bg-slate-100 dark:bg-neutral-900">
            <img v-if="competition.cover_url" :src="competition.cover_url" :alt="`${competition.name} 比赛封面`" class="h-full w-full object-cover transition duration-300 hover:scale-[1.03]" loading="lazy">
            <div v-else class="h-full w-full" :style="{ background: `linear-gradient(135deg, ${competition.competition_color} 0%, color-mix(in srgb, ${competition.competition_color} 35%, #0f172a) 100%)` }" aria-hidden="true"></div>
          </div>
          <div class="flex flex-1 flex-col p-5">
            <div class="flex min-w-0 items-start justify-between gap-3">
              <h2 class="min-w-0 break-words text-xl font-semibold">{{ competition.name }}</h2>
              <span class="shrink-0 rounded-full bg-blue-50 px-2 py-1 text-xs text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">{{ statusText(competition.status) }}</span>
            </div>
            <p class="mt-3 line-clamp-3 flex-1 break-words text-sm leading-6 text-slate-600 dark:text-slate-300">{{ descriptionText(competition.description) }}</p>
            <div class="mt-4 border-t border-slate-200 pt-4 text-xs text-slate-500 dark:border-neutral-800">
              <p>{{ formatChinaDateTime(competition.start_time) }} 至 {{ formatChinaDateTime(competition.end_time) }}（UTC+8）</p>
              <p class="mt-2">{{ competition.required_tag_ids.length }} 个必需标签 · 前 {{ competition.top_n }} 名</p>
            </div>
          </div>
        </article>
      </div>
    </div>
  </main>
</template>
