<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { CheckIcon, PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { tagApi } from '@/api/tags'
import SoupImagePicker from '@/components/SoupImagePicker.vue'
import type { SoupEditorState, Tag } from '@/types'

const state = defineModel<SoupEditorState>({ required: true })
const props = defineProps<{
  submitting: boolean
  error: string
  submitLabel: string
}>()
const emit = defineEmits<{ submit: []; cancel: [] }>()

const tags = ref<Tag[]>([])
const newTag = ref('')
const validationError = ref('')
const tagCount = computed(() => state.value.tag_ids.length + state.value.custom_tags.length)

async function loadTags() {
  try {
    const first = await tagApi.list({ page: 1, page_size: 100, sort_by: 'usage_count' })
    const items = [...first.data.items]
    for (let page = 2; page <= (first.data.total_pages ?? 1); page += 1) {
      const response = await tagApi.list({ page, page_size: 100, sort_by: 'usage_count' })
      items.push(...response.data.items)
    }
    tags.value = items
  } catch {
    tags.value = []
  }
}

function addCustomTag() {
  const value = newTag.value.trim()
  if (!value || state.value.custom_tags.includes(value) || tagCount.value >= 10) return
  state.value.custom_tags = [...state.value.custom_tags, value]
  newTag.value = ''
}

function toggleTag(tag: Tag) {
  if (state.value.tag_ids.includes(tag.id)) {
    state.value.tag_ids = state.value.tag_ids.filter(id => id !== tag.id)
  } else if (tagCount.value < 10) {
    state.value.tag_ids = [...state.value.tag_ids, tag.id]
  }
}

function submit() {
  validationError.value = ''
  if (!state.value.title.trim()) validationError.value = '请输入标题'
  else if (!state.value.puzzle.trim() && !state.value.puzzle_images.length) validationError.value = '汤面需要文字或图片'
  else if (!state.value.solution.trim() && !state.value.solution_images.length) validationError.value = '汤底需要文字或图片'
  else if (!state.value.genre) validationError.value = '请选择流派'
  else if (!state.value.soup_color) validationError.value = '请选择汤色'
  if (validationError.value) return
  emit('submit')
}

onMounted(loadTags)
</script>

<template>
  <form class="space-y-6 border-y border-slate-200 py-7 dark:border-neutral-800" @submit.prevent="submit">
    <label class="block">
      <span class="mb-2 block text-sm font-medium">标题</span>
      <input v-model="state.title" class="form-control" maxlength="200" required>
    </label>

    <div>
      <label class="block" for="soup-puzzle"><span class="mb-2 block text-sm font-medium">汤面</span></label>
      <textarea id="soup-puzzle" v-model="state.puzzle" class="form-control min-h-36 resize-y" maxlength="20000"></textarea>
      <SoupImagePicker v-model="state.puzzle_images" label="汤面" :disabled="submitting" />
    </div>

    <div>
      <label class="block" for="soup-solution"><span class="mb-2 block text-sm font-medium">汤底</span></label>
      <textarea id="soup-solution" v-model="state.solution" class="form-control min-h-40 resize-y" maxlength="20000"></textarea>
      <SoupImagePicker v-model="state.solution_images" label="汤底" :disabled="submitting" />
      <p class="mt-2 text-xs text-amber-700 dark:text-amber-300">未揭示前不会向读者返回汤底文字和图片。</p>
    </div>

    <div class="grid gap-4 sm:grid-cols-2">
      <label class="block text-sm font-medium">流派<select v-model="state.genre" class="form-control mt-2" required><option disabled value="">请选择流派</option><option value="本格">本格</option><option value="变格">变格</option><option value="鳖汤">鳖汤</option></select></label>
      <label class="block text-sm font-medium">汤色<select v-model="state.soup_color" class="form-control mt-2" required><option disabled value="">请选择汤色</option><option value="清汤">清汤</option><option value="红汤">红汤</option><option value="黑汤">黑汤</option></select></label>
      <label class="block text-sm font-medium">主要人物<input v-model="state.main_player_count" class="form-control mt-2"></label>
      <label class="block text-sm font-medium">次要人物<input v-model="state.secondary_player_count" class="form-control mt-2"></label>
    </div>

    <fieldset>
      <legend class="text-sm font-medium">标签</legend>
      <div v-if="state.custom_tags.length" class="mt-3 flex flex-wrap gap-2">
        <span v-for="tag in state.custom_tags" :key="tag" class="inline-flex max-w-full items-center gap-1 bg-blue-50 px-2.5 py-1 text-sm text-blue-700 dark:bg-blue-950/40 dark:text-blue-300">
          <span class="break-all">#{{ tag }}</span>
          <button class="flex h-6 w-6 items-center justify-center hover:text-red-600" type="button" :aria-label="`移除标签 ${tag}`" title="移除" @click="state.custom_tags = state.custom_tags.filter(item => item !== tag)"><XMarkIcon class="h-4 w-4" aria-hidden="true" /></button>
        </span>
      </div>
      <div class="mt-3 flex flex-col gap-2 sm:flex-row">
        <input v-model="newTag" class="form-control min-w-0 flex-1" maxlength="30" placeholder="输入自定义标签" @keydown.enter.prevent="addCustomTag">
        <button class="btn-secondary gap-2" type="button" :disabled="tagCount >= 10" @click="addCustomTag"><PlusIcon class="h-4 w-4" aria-hidden="true" />添加</button>
      </div>
      <div v-if="tags.length" class="mt-3 flex flex-wrap gap-2">
        <button v-for="tag in tags" :key="tag.id" class="inline-flex max-w-full items-center gap-1 px-2 py-1 text-xs transition" :class="state.tag_ids.includes(tag.id) ? 'bg-blue-100 text-blue-700 dark:bg-blue-950 dark:text-blue-200' : 'bg-slate-100 text-slate-600 dark:bg-neutral-900 dark:text-slate-300'" type="button" :disabled="!state.tag_ids.includes(tag.id) && tagCount >= 10" @click="toggleTag(tag)">
          <CheckIcon v-if="state.tag_ids.includes(tag.id)" class="h-3.5 w-3.5" aria-hidden="true" />
          <PlusIcon v-else class="h-3.5 w-3.5" aria-hidden="true" />
          <span class="break-all">{{ tag.name }}</span>
        </button>
      </div>
      <p class="mt-2 text-xs text-slate-500">已选择 {{ tagCount }} / 10 个标签</p>
    </fieldset>

    <label class="flex items-center gap-2 text-sm"><input v-model="state.is_revealed" class="h-4 w-4" type="checkbox">立即公开汤底</label>

    <p v-if="validationError || props.error" class="break-words text-sm text-red-600">{{ validationError || props.error }}</p>
    <div class="sticky bottom-0 z-20 -mx-4 flex gap-3 border-t border-slate-200 bg-white px-4 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] dark:border-neutral-800 dark:bg-black sm:static sm:mx-0 sm:flex-wrap sm:border-0 sm:bg-transparent sm:p-0 dark:sm:bg-transparent">
      <button class="btn-primary min-w-0 flex-1 sm:flex-none" type="submit" :disabled="submitting">{{ submitting ? '保存中…' : submitLabel }}</button>
      <button class="btn-secondary min-w-0 flex-1 sm:flex-none" type="button" :disabled="submitting" @click="emit('cancel')">取消</button>
    </div>
  </form>
</template>
