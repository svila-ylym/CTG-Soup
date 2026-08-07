<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
    <div class="container mx-auto px-4 max-w-4xl">
      <!-- 页面标题 -->
      <div class="mb-8">
        <h1 class="text-3xl font-bold text-gray-900 dark:text-white mb-2">发布海龟汤</h1>
        <p class="text-gray-600 dark:text-gray-400">分享你的创意谜题，挑战其他玩家的推理能力</p>
      </div>

      <!-- 发布表单 -->
      <div class="bg-white dark:bg-gray-800 rounded-xl shadow-lg p-8">
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
              class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition"
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
              class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500 transition resize-none"
              placeholder="描述海龟汤的谜面，让玩家通过提问来猜测真相"
            ></textarea>
            <p class="mt-1 text-xs text-gray-500 dark:text-gray-400">尽量简洁明了，但包含足够的线索</p>
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
              class="w-full px-4 py-3 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-purple-500 transition resize-none"
              placeholder="这是只有作者能看到的汤底，请详细描述真相"
            ></textarea>
            <p class="mt-1 text-xs text-purple-500 dark:text-purple-400">🔒 汤底仅作者和管理员可见</p>
          </div>

          <!-- 标签 -->
          <div>
            <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              标签
            </label>
            <div class="flex flex-wrap gap-2 mb-3">
              <span
                v-for="tag in formData.tags"
                :key="tag"
                class="px-3 py-1 bg-blue-100 dark:bg-blue-900/30 text-blue-600 dark:text-blue-400 rounded-full text-sm flex items-center"
              >
                #{{ tag }}
                <button type="button" @click="removeTag(tag)" class="ml-2 hover:text-blue-800 dark:hover:text-blue-300">
                  <svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd" />
                  </svg>
                </button>
              </span>
            </div>
            <div class="flex gap-2">
              <input
                v-model="newTag"
                @keyup.enter="addTag"
                type="text"
                class="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:outline-none focus:ring-2 focus:ring-blue-500"
                placeholder="输入标签后按回车添加"
                maxlength="20"
              />
              <button
                type="button"
                @click="addTag"
                class="px-4 py-2 bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition"
              >
                添加
              </button>
            </div>
            <!-- 预设标签 -->
            <div class="mt-3 flex flex-wrap gap-2">
              <span class="text-xs text-gray-500 dark:text-gray-400">推荐：</span>
              <button
                v-for="tag in suggestedTags"
                :key="tag"
                type="button"
                @click="addSuggestedTag(tag)"
                class="px-2 py-1 text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400 rounded hover:bg-gray-200 dark:hover:bg-gray-600 transition"
              >
                + {{ tag }}
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
              class="flex-1 flex justify-center py-3 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-gradient-to-r from-blue-500 to-purple-600 hover:from-blue-600 hover:to-purple-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition transform hover:scale-[1.02]"
            >
              <span v-if="isSubmitting">
                <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-white inline" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
                发布中...
              </span>
              <span v-else>🚀 发布海龟汤</span>
            </button>
            <router-link
              to="/soups"
              class="px-6 py-3 border border-gray-300 dark:border-gray-600 rounded-lg text-sm font-medium text-gray-700 dark:text-gray-300 bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 transition"
            >
              取消
            </router-link>
          </div>
        </form>
      </div>

      <!-- 发布指南 -->
      <div class="mt-8 bg-blue-50 dark:bg-blue-900/20 rounded-xl p-6">
        <h3 class="text-lg font-semibold text-blue-900 dark:text-blue-300 mb-3">💡 发布指南</h3>
        <ul class="space-y-2 text-sm text-blue-800 dark:text-blue-400">
          <li class="flex items-start">
            <span class="mr-2">•</span>
            <span>谜面应该简洁但包含足够的线索，让玩家能够通过提问逐步接近真相</span>
          </li>
          <li class="flex items-start">
            <span class="mr-2">•</span>
            <span>汤底应该逻辑自洽，解释谜面中的所有关键点</span>
          </li>
          <li class="flex items-start">
            <span class="mr-2">•</span>
            <span>选择合适的标签可以帮助玩家找到您的作品</span>
          </li>
          <li class="flex items-start">
            <span class="mr-2">•</span>
            <span>请确保内容为原创或已获得授权</span>
          </li>
        </ul>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useSoupStore } from '@/stores/soup'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const soupStore = useSoupStore()
const authStore = useAuthStore()

const newTag = ref('')
const isSubmitting = ref(false)
const errorMessage = ref('')

const suggestedTags = ['悬疑', '恐怖', '搞笑', '温情', '烧脑', '经典', '原创', '剧情']

const formData = reactive({
  title: '',
  puzzle: '',
  solution: '',
  tags: [] as string[],
  is_revealed: false,
})

const addTag = () => {
  const tag = newTag.value.trim()
  if (tag && !formData.tags.includes(tag) && formData.tags.length < 10) {
    formData.tags.push(tag)
    newTag.value = ''
  }
}

const removeTag = (tag: string) => {
  formData.tags = formData.tags.filter(t => t !== tag)
}

const addSuggestedTag = (tag: string) => {
  if (!formData.tags.includes(tag) && formData.tags.length < 10) {
    formData.tags.push(tag)
  }
}

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

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    await soupStore.createSoup({
      title: formData.title.trim(),
      puzzle: formData.puzzle.trim(),
      solution: formData.solution.trim(),
      tags: formData.tags,
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
