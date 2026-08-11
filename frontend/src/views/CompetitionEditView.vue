<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeftIcon, ArrowPathIcon, CheckIcon, PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import CompetitionRichTextEditor from '@/components/CompetitionRichTextEditor.vue'
import http from '@/api/http'
import { tagApi } from '@/api/tags'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { chinaLocalDateTimeToUtcIso, utcIsoToChinaLocalDateTime } from '@/utils/datetime'
import type { Competition, CompetitionUpdate, Tag } from '@/types'

type TagRole = 'required' | 'optional'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const tags = ref<Tag[]>([])
const loading = ref(true)
const loadingTags = ref(true)
const submitting = ref(false)
const error = ref('')
const keywordInput = reactive({ required: '', optional: '' })
const pageConfig = ref<Record<string, unknown>>({})

const form = reactive({
  name: '',
  description: '',
  start_time: '',
  end_time: '',
  required_tag_ids: [] as number[],
  custom_tags: [] as string[],
  optional_tag_ids: [] as number[],
  optional_custom_tags: [] as string[],
  image_asset_ids: [] as number[],
  top_n: 10,
  competition_color: '#2563EB',
})

const requiredCount = computed(() => form.required_tag_ids.length + form.custom_tags.length)
const optionalCount = computed(() => form.optional_tag_ids.length + form.optional_custom_tags.length)

function normalizedKeyword(value: string) {
  return value.trim().toLocaleLowerCase('zh-CN')
}

function roleValues(role: TagRole) {
  return role === 'required'
    ? { ids: form.required_tag_ids, custom: form.custom_tags, otherIds: form.optional_tag_ids, otherCustom: form.optional_custom_tags, count: requiredCount.value }
    : { ids: form.optional_tag_ids, custom: form.optional_custom_tags, otherIds: form.required_tag_ids, otherCustom: form.custom_tags, count: optionalCount.value }
}

function addKeyword(role: TagRole) {
  const keyword = keywordInput[role].trim()
  if (!keyword) return
  const values = roleValues(role)
  const normalized = normalizedKeyword(keyword)
  if (values.custom.some(item => normalizedKeyword(item) === normalized)) return
  if (values.otherCustom.some(item => normalizedKeyword(item) === normalized)) {
    error.value = '同一标签不能同时设为必选和可选'
    return
  }
  const matchingTag = tags.value.find(tag => normalizedKeyword(tag.name) === normalized)
  if (matchingTag && values.otherIds.includes(matchingTag.id)) {
    error.value = '同一标签不能同时设为必选和可选'
    return
  }
  if (matchingTag && values.ids.includes(matchingTag.id)) {
    keywordInput[role] = ''
    return
  }
  if (values.count >= 10) {
    error.value = `${role === 'required' ? '必选' : '可选'}标签最多 10 个`
    return
  }
  if (matchingTag) {
    values.ids.push(matchingTag.id)
  } else {
    values.custom.push(keyword)
  }
  keywordInput[role] = ''
  error.value = ''
}

function removeKeyword(role: TagRole, keyword: string) {
  if (role === 'required') {
    form.custom_tags = form.custom_tags.filter(item => item !== keyword)
  } else {
    form.optional_custom_tags = form.optional_custom_tags.filter(item => item !== keyword)
  }
}

function tagDisabled(tagId: number, role: TagRole) {
  const values = roleValues(role)
  const tag = tags.value.find(item => item.id === tagId)
  const conflictsWithCustom = Boolean(tag && values.otherCustom.some(
    keyword => normalizedKeyword(keyword) === normalizedKeyword(tag.name),
  ))
  return values.otherIds.includes(tagId)
    || conflictsWithCustom
    || (!values.ids.includes(tagId) && values.count >= 10)
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

async function loadCompetition() {
  try {
    if (!auth.user && auth.accessToken) await auth.fetchCurrentUser()
    const competition = (await http.get<Competition>(`/competitions/${route.params.id}`)).data
    if (competition.creator_uid !== auth.user?.uid) {
      error.value = '只能修改自己发布的比赛'
      return
    }
    if (competition.settled_at) {
      error.value = '已结算的比赛不能修改'
      return
    }
    form.name = competition.name
    form.description = competition.description
    form.start_time = utcIsoToChinaLocalDateTime(competition.start_time)
    form.end_time = utcIsoToChinaLocalDateTime(competition.end_time)
    form.required_tag_ids = [...competition.required_tag_ids]
    form.optional_tag_ids = [...competition.optional_tag_ids]
    form.top_n = competition.top_n
    form.competition_color = competition.competition_color
    pageConfig.value = { ...competition.custom_page_config }
    const imageIds = competition.custom_page_config?.image_asset_ids
    form.image_asset_ids = Array.isArray(imageIds)
      ? imageIds.map(Number).filter(Number.isFinite)
      : []
  } catch (cause) {
    error.value = extractApiError(cause, '比赛加载失败')
  } finally {
    loading.value = false
  }
}

async function submit() {
  error.value = ''
  if (!requiredCount.value) {
    error.value = '请至少选择或新增一个必选标签'
    return
  }
  if (requiredCount.value > 10 || optionalCount.value > 10) {
    error.value = '必选和可选标签分别最多 10 个'
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
    const payload: CompetitionUpdate = {
      name: form.name.trim(),
      description: form.description,
      start_time: startTime,
      end_time: endTime,
      required_tag_ids: form.required_tag_ids,
      custom_tags: form.custom_tags,
      optional_tag_ids: form.optional_tag_ids,
      optional_custom_tags: form.optional_custom_tags,
      competition_color: form.competition_color,
      score_type: 'average',
      top_n: form.top_n,
      custom_page_config: {
        ...pageConfig.value,
        format: 'rich_html',
        image_asset_ids: form.image_asset_ids,
      },
    }
    const response = await http.put<Competition>(`/competitions/${route.params.id}`, payload)
    await router.push(`/competitions/${response.data.id}`)
  } catch (cause) {
    error.value = extractApiError(cause, '比赛修改失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => { void Promise.all([loadTags(), loadCompetition()]) })
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <router-link class="mb-6 inline-flex items-center gap-1 text-sm text-blue-600" :to="`/competitions/${route.params.id}`">
        <ArrowLeftIcon class="h-4 w-4" aria-hidden="true" />
        返回比赛详情
      </router-link>

      <h1 class="section-title text-3xl">修改比赛</h1>
      <p v-if="loading" class="py-16 text-center text-slate-500">正在加载比赛…</p>
      <div v-else-if="error && !form.name" class="py-16 text-center">
        <p class="break-words text-red-600">{{ error }}</p>
        <router-link class="btn-secondary mt-4" :to="`/competitions/${route.params.id}`">返回详情</router-link>
      </div>

      <form v-else class="mt-7 space-y-6 border-y border-slate-200 py-7 dark:border-neutral-800" @submit.prevent="submit">
        <label class="block">
          <span class="mb-2 block text-sm font-medium">比赛名称</span>
          <input v-model="form.name" class="form-control" maxlength="200" required>
        </label>

        <div>
          <label class="mb-2 block text-sm font-medium">比赛说明</label>
          <CompetitionRichTextEditor v-model="form.description" v-model:image-asset-ids="form.image_asset_ids" :disabled="submitting" />
        </div>

        <div class="grid gap-5 sm:grid-cols-2">
          <label class="block">
            <span class="mb-2 block text-sm font-medium">开始时间（UTC+8）</span>
            <input v-model="form.start_time" class="form-control" type="datetime-local" step="1" required>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium">结束时间（UTC+8）</span>
            <input v-model="form.end_time" class="form-control" type="datetime-local" step="1" required>
          </label>
        </div>

        <fieldset>
          <legend class="mb-3 text-sm font-medium">必选标签</legend>
          <div v-if="form.custom_tags.length" class="mb-3 flex flex-wrap gap-2">
            <span v-for="keyword in form.custom_tags" :key="keyword" class="inline-flex max-w-full items-center gap-1 border border-blue-200 bg-blue-50 px-2.5 py-1 text-sm text-blue-700 dark:border-blue-900 dark:bg-blue-950/40 dark:text-blue-300">
              <span class="break-all">#{{ keyword }}</span>
              <button class="flex h-6 w-6 shrink-0 items-center justify-center hover:text-red-600" type="button" :aria-label="`移除必选标签 ${keyword}`" :title="`移除必选标签 ${keyword}`" @click="removeKeyword('required', keyword)"><XMarkIcon class="h-4 w-4" aria-hidden="true" /></button>
            </span>
          </div>
          <div class="mb-4 flex flex-col gap-2 sm:flex-row">
            <input v-model="keywordInput.required" class="form-control min-w-0 flex-1" maxlength="30" aria-label="新增必选标签" placeholder="输入新的必选标签" @keydown.enter.prevent="addKeyword('required')">
            <button class="btn-secondary shrink-0 gap-2" type="button" :disabled="requiredCount >= 10" @click="addKeyword('required')"><PlusIcon class="h-4 w-4" aria-hidden="true" />添加</button>
          </div>
          <p class="mb-3 text-xs text-slate-500">已选择 {{ requiredCount }} / 10</p>
          <p v-if="loadingTags" class="text-sm text-slate-500">正在加载标签…</p>
          <div v-else class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <label v-for="tag in tags" :key="`required-${tag.id}`" class="flex min-w-0 items-center gap-2 border border-slate-200 px-3 py-2 text-sm dark:border-neutral-800">
              <input v-model="form.required_tag_ids" class="h-4 w-4 shrink-0" type="checkbox" :value="tag.id" :disabled="tagDisabled(tag.id, 'required')">
              <span class="min-w-0 break-words">{{ tag.name }}</span>
            </label>
          </div>
        </fieldset>

        <fieldset class="border-t border-slate-200 pt-6 dark:border-neutral-800">
          <legend class="mb-3 text-sm font-medium">可选标签分组</legend>
          <div v-if="form.optional_custom_tags.length" class="mb-3 flex flex-wrap gap-2">
            <span v-for="keyword in form.optional_custom_tags" :key="keyword" class="inline-flex max-w-full items-center gap-1 border border-emerald-200 bg-emerald-50 px-2.5 py-1 text-sm text-emerald-700 dark:border-emerald-900 dark:bg-emerald-950/40 dark:text-emerald-300">
              <span class="break-all">#{{ keyword }}</span>
              <button class="flex h-6 w-6 shrink-0 items-center justify-center hover:text-red-600" type="button" :aria-label="`移除可选标签 ${keyword}`" :title="`移除可选标签 ${keyword}`" @click="removeKeyword('optional', keyword)"><XMarkIcon class="h-4 w-4" aria-hidden="true" /></button>
            </span>
          </div>
          <div class="mb-4 flex flex-col gap-2 sm:flex-row">
            <input v-model="keywordInput.optional" class="form-control min-w-0 flex-1" maxlength="30" aria-label="新增可选标签" placeholder="输入新的可选标签" @keydown.enter.prevent="addKeyword('optional')">
            <button class="btn-secondary shrink-0 gap-2" type="button" :disabled="optionalCount >= 10" @click="addKeyword('optional')"><PlusIcon class="h-4 w-4" aria-hidden="true" />添加</button>
          </div>
          <p class="mb-3 text-xs text-slate-500">已选择 {{ optionalCount }} / 10</p>
          <div v-if="!loadingTags" class="grid gap-2 sm:grid-cols-2 lg:grid-cols-3">
            <label v-for="tag in tags" :key="`optional-${tag.id}`" class="flex min-w-0 items-center gap-2 border border-slate-200 px-3 py-2 text-sm dark:border-neutral-800">
              <input v-model="form.optional_tag_ids" class="h-4 w-4 shrink-0" type="checkbox" :value="tag.id" :disabled="tagDisabled(tag.id, 'optional')">
              <span class="min-w-0 break-words">{{ tag.name }}</span>
            </label>
          </div>
        </fieldset>

        <div class="grid gap-5 sm:grid-cols-3">
          <div>
            <span class="mb-2 block text-sm font-medium">评分方式</span>
            <p class="form-control bg-slate-50 text-slate-700 dark:bg-neutral-900 dark:text-slate-200">平均分</p>
          </div>
          <label class="block">
            <span class="mb-2 block text-sm font-medium">获奖名额</span>
            <input v-model.number="form.top_n" class="form-control" type="number" min="1" max="100" required>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium">竞赛色</span>
            <span class="flex h-11 items-center gap-3 border-2 bg-white px-3 dark:bg-neutral-950" :style="{ borderColor: form.competition_color }">
              <input v-model="form.competition_color" class="h-7 w-10 cursor-pointer border-0 bg-transparent p-0" type="color" required>
              <span class="font-mono text-sm">{{ form.competition_color.toUpperCase() }}</span>
            </span>
          </label>
        </div>

        <p v-if="error" class="break-words text-sm text-red-600">{{ error }}</p>

        <div class="flex flex-wrap gap-3 pt-2">
          <button class="btn-primary gap-2" type="submit" :disabled="submitting">
            <ArrowPathIcon v-if="submitting" class="h-5 w-5 animate-spin" aria-hidden="true" />
            <CheckIcon v-else class="h-5 w-5" aria-hidden="true" />
            {{ submitting ? '保存中…' : '保存修改' }}
          </button>
          <router-link class="btn-secondary" :to="`/competitions/${route.params.id}`">取消</router-link>
        </div>
      </form>
    </div>
  </main>
</template>
