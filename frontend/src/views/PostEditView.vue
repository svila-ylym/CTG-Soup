<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { postsApi } from '@/api/posts'
import { extractApiError } from '@/utils/auth'

const route = useRoute()
const router = useRouter()
const loading = ref(true)
const submitting = ref(false)
const error = ref('')
const form = reactive({ title: '', section: '', content: '' })

async function load() {
  try {
    const post = (await postsApi.get(Number(route.params.id))).data
    if (!post.can_edit) {
      error.value = '只能修改自己的帖子'
      return
    }
    form.title = post.title
    form.section = post.section
    form.content = post.content
  } catch (cause) {
    error.value = extractApiError(cause, '帖子加载失败')
  } finally {
    loading.value = false
  }
}

async function submit() {
  if (!form.title.trim() || !form.section.trim() || !form.content.trim()) return
  submitting.value = true
  error.value = ''
  try {
    await postsApi.update(Number(route.params.id), {
      title: form.title,
      section: form.section,
      content: form.content,
    })
    await router.push(`/posts/${route.params.id}`)
  } catch (cause) {
    error.value = extractApiError(cause, '帖子修改失败')
  } finally {
    submitting.value = false
  }
}

onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <h1 class="section-title text-3xl">修改帖子</h1>
      <p v-if="loading" class="py-16 text-center text-slate-500">正在加载…</p>
      <form v-else-if="form.title" class="mt-7 space-y-5 border-y border-slate-200 py-7 dark:border-neutral-800" @submit.prevent="submit">
        <label class="block"><span class="mb-2 block text-sm font-medium">标题</span><input v-model="form.title" class="form-control" maxlength="200" required></label>
        <label class="block"><span class="mb-2 block text-sm font-medium">版块</span><input v-model="form.section" class="form-control" maxlength="50" required></label>
        <label class="block"><span class="mb-2 block text-sm font-medium">内容</span><textarea v-model="form.content" class="form-control min-h-72 resize-y" maxlength="20000" required></textarea></label>
        <p v-if="error" class="break-words text-sm text-red-600">{{ error }}</p>
        <div class="flex gap-3"><button class="btn-primary" :disabled="submitting">{{ submitting ? '保存中…' : '保存修改' }}</button><button class="btn-secondary" type="button" :disabled="submitting" @click="router.push(`/posts/${route.params.id}`)">取消</button></div>
      </form>
      <div v-else class="py-16 text-center"><p class="text-red-600">{{ error }}</p><router-link class="btn-secondary mt-4" :to="`/posts/${route.params.id}`">返回详情</router-link></div>
    </div>
  </main>
</template>
