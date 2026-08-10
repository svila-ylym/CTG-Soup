<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import SoupEditorForm from '@/components/SoupEditorForm.vue'
import { soupApi } from '@/api/soup'
import { extractApiError } from '@/utils/auth'
import type { CreateSoupColor, CreateSoupGenre, SoupEditorState } from '@/types'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const state = ref<SoupEditorState>({
  title: '', puzzle: '', solution: '', genre: '' as CreateSoupGenre,
  soup_color: '' as CreateSoupColor, main_player_count: '', secondary_player_count: '',
  tag_ids: [], custom_tags: [], is_revealed: false, puzzle_images: [], solution_images: [],
})

async function load() {
  try {
    const soup = (await soupApi.getById(Number(route.params.id), true)).data
    if (!soup.can_edit) {
      error.value = '只能修改自己的海龟汤'
      return
    }
    state.value = {
      title: soup.title,
      puzzle: soup.puzzle,
      solution: soup.solution || '',
      genre: soup.genre as CreateSoupGenre,
      soup_color: soup.soup_color as CreateSoupColor,
      main_player_count: soup.main_player_count,
      secondary_player_count: soup.secondary_player_count,
      tag_ids: soup.tags.map(tag => tag.id),
      custom_tags: [],
      is_revealed: soup.status === 'revealed',
      puzzle_images: soup.puzzle_images,
      solution_images: soup.solution_images,
    }
  } catch (cause) {
    error.value = extractApiError(cause, '海龟汤加载失败')
  } finally {
    loading.value = false
  }
}

async function submit() {
  submitting.value = true
  error.value = ''
  try {
    const { puzzle_images, solution_images, ...fields } = state.value
    await soupApi.update(Number(route.params.id), {
      ...fields,
      title: fields.title,
      puzzle: fields.puzzle,
      solution: fields.solution,
      puzzle_image_ids: puzzle_images.map(image => image.id),
      solution_image_ids: solution_images.map(image => image.id),
    })
    await router.push(`/soups/${route.params.id}`)
  } catch (cause) {
    error.value = extractApiError(cause, '海龟汤修改失败')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <h1 class="section-title text-3xl">修改海龟汤</h1>
      <p v-if="loading" class="py-16 text-center text-slate-500">正在加载…</p>
      <div v-else-if="error && !state.title" class="py-16 text-center"><p class="text-red-600">{{ error }}</p><router-link class="btn-secondary mt-4" :to="`/soups/${route.params.id}`">返回详情</router-link></div>
      <SoupEditorForm v-else v-model="state" :submitting="submitting" :error="error" submit-label="保存修改" @submit="submit" @cancel="router.push(`/soups/${route.params.id}`)" />
    </div>
  </main>
</template>
