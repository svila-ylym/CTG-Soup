<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <!-- 页面标题 -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">发布海龟汤</h1>
      </div>

      <!-- 发布表单 -->
      <div class="border-y border-slate-200 bg-white py-8 dark:border-neutral-800 dark:bg-black sm:px-8">
        <form @submit.prevent="handleSubmit" class="space-y-6">
          <!-- 标题 -->
          <div>
            <label for="title" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              标题 <span class="text-red-500">*</span>
            </label>
            <input
              id="title"
              v-model="formData.title"
              type="text"
              required
              maxlength="200"
              class="form-control"
              placeholder="给您的海龟汤起一个吸引人的标题"
            />
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">{{ formData.title.length }}/200</p>
          </div>

          <!-- 谜面 -->
          <div>
            <label for="puzzle" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              谜面 <span class="text-red-500">*</span>
            </label>
            <textarea
              id="puzzle"
              v-model="formData.puzzle"
              rows="6"
              required
              class="form-control resize-none"
              placeholder="描述海龟汤的谜面，让玩家通过提问来猜测真相"
            ></textarea>
          </div>

          <!-- 汤底 -->
          <div>
            <label for="solution" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              汤底（答案） <span class="text-red-500">*</span>
            </label>
            <textarea
              id="solution"
              v-model="formData.solution"
              rows="8"
              required
              class="w-full resize-none rounded-md border border-gray-300 bg-white px-4 py-3 text-gray-900 transition focus:outline-none focus:ring-2 focus:ring-blue-500 dark:border-neutral-700 dark:bg-neutral-900 dark:text-white"
              placeholder="这是只有作者能看到的汤底，请详细描述真相"
            ></textarea>
            <p class="mt-1 text-xs text-amber-700 dark:text-amber-300">详情页默认隐藏，读者确认后可以展开。</p>
          </div>

          <div class="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              流派 <span class="text-red-500">*</span>
              <select v-model="formData.genre" required class="form-control mt-2">
                <option disabled value="">请选择流派</option>
                <option value="本格">本格</option>
                <option value="变格">变格</option>
                <option value="鳖汤">鳖汤</option>
              </select>
            </label>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              汤色 <span class="text-red-500">*</span>
              <select v-model="formData.soup_color" required class="form-control mt-2">
                <option disabled value="">请选择汤色</option>
                <option value="清汤">清汤</option>
                <option value="红汤">红汤</option>
                <option value="黑汤">黑汤</option>
              </select>
            </label>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              主要人物 <span class="text-red-500">*</span>
              <input v-model="formData.main_player_count" type="text" class="form-control mt-2" />
            </label>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300">
              次要人物 <span class="text-red-500">*</span>
              <input v-model="formData.secondary_player_count" type="text" class="form-control mt-2" />
            </label>
          </div>

          <!-- 标签 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              标签
            </label>
            <div class="flex flex-wrap gap-2 mb-3">
              <span
                v-for="tag in formData.custom_tags"
                :key="tag"
                class="flex max-w-full items-center break-all rounded-full bg-blue-100 px-3 py-1 text-sm text-blue-600 dark:bg-blue-900/30 dark:text-blue-400"
              >
                #{{ tag }}
                <button type="button" @click="removeTag(tag)" class="ml-2 flex h-5 w-5 items-center justify-center hover:text-blue-800 dark:hover:text-blue-300" aria-label="移除标签" title="移除标签">
                  <XMarkIcon class="h-4 w-4" aria-hidden="true" />
                </button>
              </span>
            </div>
            <div class="flex gap-2">
              <input
                v-model="newTag"
                @keyup.enter="addTag"
                type="text"
                class="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="输入标签后按回车添加"
                maxlength="20"
              />
              <button
                type="button"
                @click="addTag"
                class="rounded-lg bg-gray-100 px-4 py-2 text-gray-700 transition hover:bg-gray-200 dark:bg-neutral-800 dark:text-gray-300 dark:hover:bg-neutral-700"
              >
                添加
              </button>
            </div>
            <!-- 预设标签 -->
            <div class="mt-3 flex flex-wrap gap-2">
              <span class="text-xs text-gray-500 dark:text-gray-400">推荐：</span>
              <button
                v-for="tag in suggestedTags"
                :key="tag.id"
                type="button"
                @click="addSuggestedTag(tag)"
                :class="[
                  'inline-flex max-w-full items-center gap-1 break-all rounded px-2 py-1 text-xs transition',
                  formData.tag_ids.includes(tag.id)
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-300'
                    : 'bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-neutral-800 dark:text-gray-400 dark:hover:bg-neutral-700',
                ]"
              >
                <CheckIcon v-if="formData.tag_ids.includes(tag.id)" class="h-3.5 w-3.5" aria-hidden="true" />
                <PlusIcon v-else class="h-3.5 w-3.5" aria-hidden="true" />
                {{ tag.name }}
              </button>
            </div>
          </div>

          <!-- 是否立即公开汤底 -->
          <div class="flex items-center">
            <input
              id="isRevealed"
              v-model="formData.is_revealed"
              type="checkbox"
              class="h-4 w-4 text-blue-500 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label for="isRevealed" class="ml-2 text-sm text-gray-700 dark:text-gray-300">
              立即公开汤底（玩家可直接查看）
            </label>
          </div>

          <!-- 错误提示 -->
          <div v-if="errorMessage" class="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 text-sm rounded-lg p-4">
            {{ errorMessage }}
          </div>

          <!-- 提交按钮 -->
          <div class="flex gap-4 pt-4">
            <button
              type="submit"
              :disabled="isSubmitting"
              class="flex flex-1 justify-center rounded-md border border-transparent bg-blue-600 px-4 py-3 text-sm font-medium text-white transition hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
            >
              <ArrowPathIcon v-if="isSubmitting" class="mr-2 h-5 w-5 animate-spin" aria-hidden="true" />
              <PaperAirplaneIcon v-else class="mr-2 h-5 w-5" aria-hidden="true" />
              {{ isSubmitting ? '发布中…' : '发布海龟汤' }}
            </button>
            <router-link
              to="/soups"
              class="rounded-lg border border-gray-300 bg-white px-6 py-3 text-sm font-medium text-gray-700 transition hover:bg-slate-50 dark:border-neutral-700 dark:bg-neutral-900 dark:text-gray-300 dark:hover:bg-neutral-800"
            >
              取消
            </router-link>
          </div>
        </form>
      </div>
    </div>
  </main>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowPathIcon, CheckIcon, PaperAirplaneIcon, PlusIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useSoupStore } from '@/stores/soup'
import { useAuthStore } from '@/stores/auth'
import { tagApi } from '@/api/tags'
import type { Tag } from '@/types'

const router = useRouter()
const soupStore = useSoupStore()
const authStore = useAuthStore()

const newTag = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

const suggestedTags = ref<Tag[]>([])

const formData = reactive({
  title: '',
  puzzle: '',
  solution: '',
  genre: '' as '' | '本格' | '变格' | '鳖汤',
  soup_color: '' as '' | '清汤' | '红汤' | '黑汤',
  main_player_count: '',
  secondary_player_count: '',
  tag_ids: [] as number[],
  custom_tags: [] as string[],
  is_revealed: false,
})

const addTag = () => {
  const tag = newTag.value.trim()
  if (tag && !formData.custom_tags.includes(tag) && formData.custom_tags.length + formData.tag_ids.length < 10) {
    formData.custom_tags.push(tag)
    newTag.value = ''
  }
}

const removeTag = (tag: string) => {
  formData.custom_tags = formData.custom_tags.filter(t => t !== tag)
}

const addSuggestedTag = (tag: Tag) => {
  if (formData.tag_ids.includes(tag.id)) {
    formData.tag_ids = formData.tag_ids.filter(id => id !== tag.id)
    return
  }
  if (formData.custom_tags.length + formData.tag_ids.length < 10) {
    formData.tag_ids.push(tag.id)
  }
}

onMounted(async () => {
  try {
    const response = await tagApi.list({ page: 1, page_size: 20, sort_by: 'usage_count' })
    suggestedTags.value = response.data.items
  } catch {
    suggestedTags.value = []
  }
})

const handleSubmit = async () => {
  // 验证登录状态
  if (!authStore.isAuthenticated) {
    errorMessage.value = '请先登录后再发布'
    return
  }

  // 验证表单
  if (!formData.title.trim()) {
    errorMessage.value = '请输入标题'
    return
  }
  if (!formData.puzzle.trim()) {
    errorMessage.value = '请输入谜面'
    return
  }
  if (!formData.solution.trim()) {
    errorMessage.value = '请输入汤底'
    return
  }
  if (!formData.genre || !formData.soup_color) {
    errorMessage.value = '请选择流派和汤色'
    return
  }

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    await soupStore.createSoup({
      title: formData.title.trim(),
      puzzle: formData.puzzle.trim(),
      solution: formData.solution.trim(),
      genre: formData.genre,
      soup_color: formData.soup_color,
      main_player_count: formData.main_player_count,
      secondary_player_count: formData.secondary_player_count,
      tag_ids: formData.tag_ids,
      custom_tags: formData.custom_tags,
      is_revealed: formData.is_revealed,
    })

    // 显示成功提示
    if ((window as any).showToast) {
      (window as any).showToast('发布成功！', 'success')
    }

    // 跳转到海龟汤列表
    router.push('/soups')
  } catch (error: any) {
    errorMessage.value = error.response?.data?.detail || '发布失败，请稍后重试'
  } finally {
    isSubmitting.value = false
  }
}
</script>
