<template>
  <div class="page-shell">
    <div class="page-container">
      <!-- 页面标题 -->
      <div class="mb-6 flex items-center justify-between">
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">问卷调查</h1>
        <button 
          v-if="isAdmin"
          @click="showCreateDialog = true"
          class="btn-primary glass-button"
        >
          <PlusIcon class="mr-2 h-5 w-5" />
          发布问卷
        </button>
      </div>

      <!-- 问卷列表 -->
      <div v-if="loading" class="flex items-center justify-center py-12">
        <ArrowPathIcon class="h-8 w-8 animate-spin text-blue-600" />
      </div>
      
      <div v-else-if="surveys.length === 0" class="glass-card p-8 text-center">
        <DocumentTextIcon class="mx-auto h-12 w-12 text-slate-400" />
        <p class="mt-4 text-slate-600 dark:text-slate-400">暂无问卷</p>
      </div>
      
      <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        <div 
          v-for="survey in surveys" 
          :key="survey.id"
          class="glass-card cursor-pointer p-5 transition-all hover:-translate-y-1 hover:shadow-lg"
          @click="goToSurvey(survey.id)"
        >
          <div class="mb-3 flex items-start justify-between">
            <h3 class="text-lg font-semibold text-slate-900 dark:text-white line-clamp-1">{{ survey.title }}</h3>
            <span 
              :class="{
                'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400': survey.status === 'active',
                'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300': survey.status === 'draft',
                'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400': survey.status === 'closed' || survey.status === 'expired'
              }"
              class="rounded-full px-2 py-1 text-xs font-medium"
            >
              {{ statusText(survey.status) }}
            </span>
          </div>
          
          <p class="mb-4 text-sm text-slate-600 dark:text-slate-400 line-clamp-2">{{ survey.description || '无描述' }}</p>
          
          <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-500">
            <span class="flex items-center">
              <DocumentTextIcon class="mr-1 h-4 w-4" />
              {{ survey.question_count }} 题
            </span>
            <span class="flex items-center">
              <UserGroupIcon class="mr-1 h-4 w-4" />
              {{ survey.response_count }} 人参与
            </span>
          </div>
          
          <div v-if="survey.expires_at" class="mt-3 text-xs text-slate-500 dark:text-slate-500">
            截止：{{ formatDate(survey.expires_at) }}
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="mt-8 flex justify-center gap-2">
        <button 
          :disabled="currentPage === 1"
          @click="changePage(currentPage - 1)"
          class="glass-button px-4 py-2 disabled:opacity-50"
        >
          上一页
        </button>
        <span class="flex items-center px-4 text-slate-600 dark:text-slate-400">
          第 {{ currentPage }} / {{ totalPages }} 页
        </span>
        <button 
          :disabled="currentPage === totalPages"
          @click="changePage(currentPage + 1)"
          class="glass-button px-4 py-2 disabled:opacity-50"
        >
          下一页
        </button>
      </div>
    </div>

    <!-- 创建问卷对话框 -->
    <div v-if="showCreateDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" @click.self="showCreateDialog = false">
      <div class="glass-panel mx-4 max-w-2xl max-h-[90vh] overflow-y-auto p-6">
        <div class="mb-4 flex items-center justify-between">
          <h2 class="text-xl font-bold">发布新问卷</h2>
          <button @click="showCreateDialog = false" class="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300">
            <XMarkIcon class="h-6 w-6" />
          </button>
        </div>
        
        <form @submit.prevent="createSurvey" class="space-y-4">
          <div>
            <label class="mb-1 block text-sm font-medium">标题</label>
            <input v-model="newSurvey.title" required class="form-control" placeholder="请输入问卷标题" />
          </div>
          
          <div>
            <label class="mb-1 block text-sm font-medium">描述</label>
            <textarea v-model="newSurvey.description" class="form-control" rows="3" placeholder="问卷描述（可选）"></textarea>
          </div>
          
          <div class="flex gap-4">
            <div class="flex-1">
              <label class="mb-1 block text-sm font-medium">开始时间</label>
              <input v-model="newSurvey.starts_at" type="datetime-local" class="form-control" />
            </div>
            <div class="flex-1">
              <label class="mb-1 block text-sm font-medium">截止时间</label>
              <input v-model="newSurvey.expires_at" type="datetime-local" class="form-control" />
            </div>
          </div>
          
          <div>
            <label class="mb-1 block text-sm font-medium">状态</label>
            <select v-model="newSurvey.status" class="form-control">
              <option value="draft">草稿</option>
              <option value="active">发布</option>
            </select>
          </div>
          
          <div class="flex justify-end gap-3 pt-4">
            <button type="button" @click="showCreateDialog = false" class="btn-secondary">取消</button>
            <button type="submit" :disabled="creating" class="btn-primary">
              {{ creating ? '发布中...' : '发布问卷' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { DocumentTextIcon, UserGroupIcon, PlusIcon, XMarkIcon, ArrowPathIcon } from '@heroicons/vue/24/outline'
import { surveysApi } from '@/api/surveys'
import type { SurveySummary } from '@/types'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()

const surveys = ref<SurveySummary[]>([])
const loading = ref(true)
const currentPage = ref(1)
const totalPages = ref(1)
const showCreateDialog = ref(false)
const creating = ref(false)

const isAdmin = computed(() => {
  return authStore.user?.role === 'admin' || authStore.user?.role === 'root'
})

const newSurvey = ref({
  title: '',
  description: '',
  starts_at: '',
  expires_at: '',
  status: 'draft' as 'draft' | 'active'
})

async function loadSurveys() {
  loading.value = true
  try {
    const res = await surveysApi.list({ page: currentPage.value, page_size: 20 })
    surveys.value = res.data.items || []
    totalPages.value = res.data.total_pages || 1
  } catch (err) {
    console.error('Failed to load surveys:', err)
  } finally {
    loading.value = false
  }
}

function changePage(page: number) {
  if (page < 1 || page > totalPages.value) return
  currentPage.value = page
  loadSurveys()
}

function goToSurvey(id: number) {
  router.push(`/surveys/${id}`)
}

function statusText(status: string): string {
  const map: Record<string, string> = {
    active: '进行中',
    draft: '草稿',
    closed: '已关闭',
    expired: '已过期'
  }
  return map[status] || status
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function createSurvey() {
  if (!newSurvey.value.title.trim()) return
  
  creating.value = true
  try {
    await surveysApi.create({
      ...newSurvey.value,
      questions: []
    })
    showCreateDialog.value = false
    newSurvey.value = { title: '', description: '', starts_at: '', expires_at: '', status: 'draft' }
    loadSurveys()
  } catch (err) {
    console.error('Failed to create survey:', err)
    alert('发布失败，请重试')
  } finally {
    creating.value = false
  }
}

onMounted(loadSurveys)
</script>
