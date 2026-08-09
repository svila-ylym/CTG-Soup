<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeftIcon, ArrowPathIcon, PaperAirplaneIcon, PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import http from '@/api/http'
import { tagApi } from '@/api/tags'
import { extractApiError } from '@/utils/auth'
import { chinaLocalDateTimeToUtcIso } from '@/utils/datetime'
import type { Competition, CompetitionCreate, Tag } from '@/types'

const router = useRouter()
const tags = ref<Tag[]>([])
const loadingTags = ref(true)
const submitting = ref(false)
const error = ref('')
const newKeyword = ref('')

const form = reactive<{
  name: string
  description: string
  start_time: string
  end_time: string
  required_tag_ids: number[]
  custom_tags: string[]
  top_n: number
}>({
  name: '',
  description: '',
  start_time: '',
  end_time: '',
  required_tag_ids: [],
  custom_tags: [],
  top_n: 10,
})
const keywordCount = computed(() => form.required_tag_ids.length + form.custom_tags.length)

function addKeyword() {
  const keyword = newKeyword.value.trim()
  if (!keyword || form.custom_tags.includes(keyword)) return
  if (keywordCount.value >= 10) {
    error.value = '比赛关键词最多 10 个'
    return
  }
  form.custom_tags.push(keyword)
  newKeyword.value = ''
  error.value = ''
}

function removeKeyword(keyword: string) {
  form.custom_tags = form.custom_tags.filter(item => item !== keyword)
}

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
  if (!keywordCount.value) {
    error.value = '请至少选择或新增一个比赛关键词'
    return
  }
  if (keywordCount.value > 10) {
    error.value = '比赛关键词最多 10 个'
    return
  }

  let startTime: string
  let endTime: string
  try {
    startTime = chinaLocalDateTimeToUtcIso(form.start_time)
    endTime = chinaLocalDateTimeToUtcIso(form.end_time)
  } catch {
    error.value = '请填写有效的比赛时间'
    return
  }
  if (new Date(startTime).getTime() >= new Date(endTime).getTime()) {
    error.value = '结束时间必须晚于开始时间'
    return
  }

  submitting.value = true
  try {
    const payload: CompetitionCreate = {
      name: form.name.trim(),
      description: form.description.trim(),
      start_time: startTime,
      end_time: endTime,
      required_tag_ids: form.required_tag_ids,
      custom_tags: form.custom_tags,
      score_type: 'average',
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
            <span class="mb-2 block text-sm font-medium">开始时间（UTC+8）</span>
            <input v-model="form.start_time" class="form-control" type="datetime-local" required>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium">结束时间（UTC+8）</span>
            <input v-model="form.end_time" class="form-control" type="datetime-local" required>
          </label>
        </div>

        <fieldset>
          <legend class="mb-3 text-sm font-medium">比赛关键词</legend>
          <div class="mb-4">
            <div v-if="form.custom_tags.length" class="mb-3 flex flex-wrap gap-2">
              <span v-for="keyword in form.custom_tags" :key="keyword" class="inline-flex max-w-full items-center gap-1 border border-blue-200 bg-blue-50 px-2.5 py-1 text-sm text-blue-700 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-300">
                <span class="break-all">#{{ keyword }}</span>
                <button class="flex h-6 w-6 shrink-0 items-center justify-center hover:text-red-600" type="button" :aria-label="`移除关键词 ${keyword}`" :title="`移除关键词 ${keyword}`" @click="removeKeyword(keyword)">
                  <XMarkIcon class="h-4 w-4" aria-hidden="true" />
                </button>
              </span>
            </div>
            <div class="flex flex-col gap-2 sm:flex-row">
              <input v-model="newKeyword" class="form-control min-w-0 flex-1" maxlength="30" aria-label="新增比赛关键词" placeholder="输入新的比赛关键词" @keydown.enter.prevent="addKeyword">
              <button class="btn-secondary shrink-0 gap-2" type="button" :disabled="keywordCount >= 10" @click="addKeyword">
                <PlusIcon class="h-4 w-4" aria-hidden="true" />
                添加关键词
              </button>
            </div>
            <p class="mt-2 text-xs text-slate-500">已选择 {{ keywordCount }} / 10 个关键词</p>
          </div>
          <p v-if="loadingTags" class="text-sm text-slate-500">正在加载标签…</p>
          <p v-else-if="!tags.length" class="text-sm text-slate-500">暂无已有标签，可使用上方输入框新增。</p>
          <div v-else class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <label v-for="tag in tags" :key="tag.id" class="flex min-w-0 items-center gap-2 border border-slate-200 px-3 py-2 text-sm dark:border-neutral-800">
              <input v-model="form.required_tag_ids" class="h-4 w-4 shrink-0" type="checkbox" :value="tag.id" :disabled="!form.required_tag_ids.includes(tag.id) && keywordCount >= 10">
              <span class="min-w-0 break-words">{{ tag.name }}</span>
            </label>
          </div>
        </fieldset>

        <div class="grid gap-5 sm:grid-cols-2">
          <div>
            <span class="mb-2 block text-sm font-medium">评分方式</span>
            <p class="form-control bg-slate-50 text-slate-700 dark:bg-neutral-900 dark:text-slate-200">平均分</p>
          </div>
          <label class="block">
            <span class="mb-2 block text-sm font-medium">获奖名额</span>
            <input v-model.number="form.top_n" class="form-control" type="number" min="1" max="100" required>
          </label>
        </div>

        <p v-if="error" class="break-words text-sm text-red-600">{{ error }}</p>

        <div class="flex flex-wrap gap-3 pt-2">
          <button class="btn-primary gap-2" type="submit" :disabled="submitting">
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
