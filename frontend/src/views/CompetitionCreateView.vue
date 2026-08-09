<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeftIcon, ArrowPathIcon, PaperAirplaneIcon } from '@heroicons/vue/24/outline'
import http from '@/api/http'
import { tagApi } from '@/api/tags'
import { extractApiError } from '@/utils/auth'
import type { Competition, CompetitionCreate, Tag } from '@/types'

const router = useRouter()
const tags = ref<Tag[]>([])
const loadingTags = ref(true)
const submitting = ref(false)
const error = ref('')

const form = reactive<{
  name: string
  description: string
  start_time: string
  end_time: string
  required_tag_ids: number[]
  score_type: CompetitionCreate['score_type']
  top_n: number
}>({
  name: '',
  description: '',
  start_time: '',
  end_time: '',
  required_tag_ids: [],
  score_type: 'average',
  top_n: 10,
})

async function loadTags() {
  loadingTags.value = true
  try {
    const response = await tagApi.list({ page: 1, page_size: 100, sort_by: 'name' })
    tags.value = response.data.items || []
  } catch (cause) {
    error.value = extractApiError(cause, '标签加载失败')
  } finally {
    loadingTags.value = false
  }
}

async function submit() {
  error.value = ''
  if (!form.required_tag_ids.length) {
    error.value = '请至少选择一个比赛标签'
    return
  }

  const startTime = new Date(form.start_time)
  const endTime = new Date(form.end_time)
  if (Number.isNaN(startTime.getTime()) || Number.isNaN(endTime.getTime())) {
    error.value = '请填写有效的比赛时间'
    return
  }
  if (startTime.getTime() >= endTime.getTime()) {
    error.value = '结束时间必须晚于开始时间'
    return
  }

  submitting.value = true
  try {
    const payload: CompetitionCreate = {
      name: form.name.trim(),
      description: form.description.trim(),
      start_time: startTime.toISOString(),
      end_time: endTime.toISOString(),
      required_tag_ids: form.required_tag_ids,
      score_type: form.score_type,
      top_n: form.top_n,
      custom_page_config: {},
    }
    const response = await http.post<Competition>('/competitions', payload)
    await router.push(`/competitions/${response.data.id}`)
  } catch (cause) {
    error.value = extractApiError(cause, '比赛发布失败')
  } finally {
    submitting.value = false
  }
}

onMounted(loadTags)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <router-link class="mb-6 inline-flex items-center gap-1 text-sm text-blue-600" to="/competitions">
        <ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />
        返回比赛列表
      </router-link>

      <h1 class="section-title text-3xl">发布比赛</h1>

      <form class="mt-7 space-y-6 border-y border-slate-200 py-7 dark:border-neutral-800" @submit.prevent="submit">
        <label class="block">
          <span class="mb-2 block text-sm font-medium">比赛名称</span>
          <input v-model.trim="form.name" class="form-control" maxlength="200" required>
        </label>

        <label class="block">
          <span class="mb-2 block text-sm font-medium">比赛说明</span>
          <textarea v-model="form.description" class="form-control min-h-40 resize-y" maxlength="5000" required></textarea>
        </label>

        <div class="grid gap-5 sm:grid-cols-2">
          <label class="block">
            <span class="mb-2 block text-sm font-medium">开始时间</span>
            <input v-model="form.start_time" class="form-control" type="datetime-local" required>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium">结束时间</span>
            <input v-model="form.end_time" class="form-control" type="datetime-local" required>
          </label>
        </div>

        <fieldset>
          <legend class="mb-3 text-sm font-medium">必需标签</legend>
          <p v-if="loadingTags" class="text-sm text-slate-500">正在加载标签…</p>
          <p v-else-if="!tags.length" class="text-sm text-slate-500">暂无可用标签</p>
          <div v-else class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <label v-for="tag in tags" :key="tag.id" class="flex min-w-0 items-center gap-2 border border-slate-200 px-3 py-2 text-sm dark:border-neutral-800">
              <input v-model="form.required_tag_ids" class="h-4 w-4 shrink-0" type="checkbox" :value="tag.id">
              <span class="min-w-0 break-words">{{ tag.name }}</span>
            </label>
          </div>
        </fieldset>

        <div class="grid gap-5 sm:grid-cols-2">
          <fieldset>
            <legend class="mb-2 text-sm font-medium">评分方式</legend>
            <div class="inline-flex border border-slate-300 dark:border-neutral-700">
              <label class="cursor-pointer px-4 py-2 text-sm" :class="form.score_type === 'average' ? 'bg-blue-600 text-white' : ''">
                <input v-model="form.score_type" class="sr-only" type="radio" value="average">
                平均分
              </label>
              <label class="cursor-pointer px-4 py-2 text-sm" :class="form.score_type === 'top_score' ? 'bg-blue-600 text-white' : ''">
                <input v-model="form.score_type" class="sr-only" type="radio" value="top_score">
                最高分
              </label>
            </div>
          </fieldset>

          <label class="block">
            <span class="mb-2 block text-sm font-medium">获奖名额</span>
            <input v-model.number="form.top_n" class="form-control" type="number" min="1" max="100" required>
          </label>
        </div>

        <p v-if="error" class="break-words text-sm text-red-600">{{ error }}</p>

        <div class="flex flex-wrap gap-3 pt-2">
          <button class="btn-primary gap-2" type="submit" :disabled="submitting || loadingTags || !tags.length">
            <ArrowPathIcon v-if="submitting" class="h-5 w-5 animate-spin" aria-hidden="true" />
            <PaperAirplaneIcon v-else class="h-5 w-5" aria-hidden="true" />
            {{ submitting ? '发布中…' : '发布比赛' }}
          </button>
          <router-link class="btn-secondary" to="/competitions">取消</router-link>
        </div>
      </form>
    </div>
  </main>
</template>
