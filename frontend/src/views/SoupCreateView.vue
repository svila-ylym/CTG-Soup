<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import SoupEditorForm from '@/components/SoupEditorForm.vue'
import { uploadApi } from '@/api/upload'
import { useAuthStore } from '@/stores/auth'
import { useSoupStore } from '@/stores/soup'
import { draftStorageKey, readDraft, removeDraft, writeDraft } from '@/utils/draftStorage'
import { extractApiError } from '@/utils/auth'
import type { CreateSoupColor, CreateSoupGenre, SoupEditorState } from '@/types'

type SoupDraft = Omit<SoupEditorState, 'puzzle_images' | 'solution_images'> & {
  puzzle_image_ids: number[]
  solution_image_ids: number[]
}

const router = useRouter()
const auth = useAuthStore()
const soupStore = useSoupStore()
const submitting = ref(false)
const error = ref('')
const restoring = ref(true)
const state = ref<SoupEditorState>({
  title: '',
  puzzle: '',
  solution: '',
  genre: '' as CreateSoupGenre,
  soup_color: '' as CreateSoupColor,
  main_player_count: '',
  secondary_player_count: '',
  tag_ids: [],
  custom_tags: [],
  is_revealed: false,
  puzzle_images: [],
  solution_images: [],
})
const draftKey = draftStorageKey('soup', auth.user?.uid ?? localStorage.getItem('user_uid'))

function isDraft(value: unknown): value is SoupDraft {
  if (!value || typeof value !== 'object') return false
  const item = value as Record<string, unknown>
  return typeof item.title === 'string'
    && typeof item.puzzle === 'string'
    && typeof item.solution === 'string'
    && Array.isArray(item.tag_ids)
    && Array.isArray(item.custom_tags)
}

function snapshot(): SoupDraft {
  const { puzzle_images, solution_images, ...fields } = state.value
  return {
    ...fields,
    puzzle_image_ids: puzzle_images.map(image => image.id),
    solution_image_ids: solution_images.map(image => image.id),
  }
}

function hasDraft(draft: SoupDraft) {
  return Boolean(
    draft.title.trim()
    || draft.puzzle.trim()
    || draft.solution.trim()
    || draft.genre
    || draft.soup_color
    || draft.main_player_count.trim()
    || draft.secondary_player_count.trim()
    || draft.tag_ids.length
    || draft.custom_tags.length
    || draft.puzzle_image_ids.length
    || draft.solution_image_ids.length
    || draft.is_revealed,
  )
}

async function restoreDraft() {
  const draft = readDraft(draftKey, isDraft)
  if (!draft) {
    restoring.value = false
    return
  }
  try {
    const assets = (await uploadApi.images()).data
    const byId = new Map(assets.map(asset => [asset.id, asset]))
    Object.assign(state.value, {
      ...draft,
      puzzle_images: (draft.puzzle_image_ids || []).flatMap(id => {
        const asset = byId.get(id)
        return asset ? [{ id, public_url: asset.public_url, mime_type: asset.mime_type, size: asset.size }] : []
      }),
      solution_images: (draft.solution_image_ids || []).flatMap(id => {
        const asset = byId.get(id)
        return asset ? [{ id, public_url: asset.public_url, mime_type: asset.mime_type, size: asset.size }] : []
      }),
    })
  } catch {
    Object.assign(state.value, { ...draft, puzzle_images: [], solution_images: [] })
  } finally {
    restoring.value = false
  }
}

watch(state, () => {
  if (restoring.value) return
  const draft = snapshot()
  if (hasDraft(draft)) writeDraft(draftKey, draft)
  else removeDraft(draftKey)
}, { deep: true, flush: 'sync' })

async function submit() {
  if (submitting.value) return
  submitting.value = true
  error.value = ''
  try {
    const { puzzle_images, solution_images, ...fields } = state.value
    const result = await soupStore.createSoup({
      ...fields,
      title: fields.title,
      puzzle: fields.puzzle,
      solution: fields.solution,
      puzzle_image_ids: puzzle_images.map(image => image.id),
      solution_image_ids: solution_images.map(image => image.id),
    })
    removeDraft(draftKey)
    await router.push(`/soups/${result.id}`)
  } catch (cause) {
    error.value = extractApiError(cause, '海龟汤发布失败')
  } finally {
    submitting.value = false
  }
}

onMounted(restoreDraft)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <h1 class="section-title text-3xl">发布海龟汤</h1>
      <p v-if="restoring" class="py-16 text-center text-slate-500">正在恢复草稿…</p>
      <SoupEditorForm v-else v-model="state" :submitting="submitting" :error="error" submit-label="发布海龟汤" @submit="submit" @cancel="router.push('/soups')" />
    </div>
  </main>
</template>
