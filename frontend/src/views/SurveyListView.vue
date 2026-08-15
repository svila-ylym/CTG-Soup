<template>
  <div class="survey-page page-shell">
    <div class="page-container">
      <div class="mb-6 flex items-center justify-between gap-4">
        <h1 class="text-2xl font-bold text-slate-900 dark:text-white">问卷调查</h1>
        <button v-if="isAdmin" class="btn-primary" type="button" @click="showCreateDialog = true">
          <PlusIcon class="mr-2 h-5 w-5" aria-hidden="true" />
          发布问卷
        </button>
      </div>

      <section :aria-busy="initialLoading || refreshing" aria-live="polite">
        <div v-if="initialLoading" class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3" aria-label="正在加载问卷">
          <article v-for="item in 6" :key="item" class="glass-card min-h-44 p-5">
            <div class="flex items-center justify-between gap-4">
              <span class="skeleton-block h-6 w-2/3"></span>
              <span class="skeleton-block h-6 w-14 rounded-full"></span>
            </div>
            <div class="skeleton-block mt-5 h-4 w-full"></div>
            <div class="skeleton-block mt-2 h-4 w-4/5"></div>
            <div class="mt-7 flex justify-between">
              <span class="skeleton-block h-4 w-16"></span>
              <span class="skeleton-block h-4 w-20"></span>
            </div>
          </article>
        </div>

        <template v-else>
          <div v-if="loadError" class="mb-4 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-red-200 bg-red-50/90 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/60 dark:text-red-300" role="alert">
            <span>{{ loadError }}</span>
            <button class="font-medium underline underline-offset-2" type="button" @click="loadSurveys">重试</button>
          </div>

          <div v-if="surveys.length === 0" class="glass-card p-8 text-center">
            <DocumentTextIcon class="mx-auto h-12 w-12 text-slate-400" aria-hidden="true" />
            <p class="mt-4 text-slate-600 dark:text-slate-400">暂无问卷</p>
          </div>

          <div v-else class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <article
              v-for="survey in surveys"
              :key="survey.id"
              class="glass-card glass-card-interactive cursor-pointer p-5"
              tabindex="0"
              @click="goToSurvey(survey.id)"
              @keydown.enter="goToSurvey(survey.id)"
              @keydown.space.prevent="goToSurvey(survey.id)"
            >
              <div class="mb-3 flex items-start justify-between gap-3">
                <h2 class="line-clamp-1 text-lg font-semibold text-slate-900 dark:text-white">{{ survey.title }}</h2>
                <span
                  :class="{
                    'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400': survey.status === 'active',
                    'bg-slate-100 text-slate-800 dark:bg-slate-700 dark:text-slate-300': survey.status === 'draft',
                    'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400': survey.status === 'closed' || survey.status === 'expired',
                  }"
                  class="shrink-0 rounded-full px-2 py-1 text-xs font-medium"
                >
                  {{ statusText(survey.status) }}
                </span>
              </div>

              <p class="mb-4 line-clamp-2 text-sm text-slate-600 dark:text-slate-400">{{ survey.description || '无描述' }}</p>

              <div class="flex items-center justify-between text-xs text-slate-500 dark:text-slate-400">
                <span class="flex items-center"><DocumentTextIcon class="mr-1 h-4 w-4" aria-hidden="true" />{{ survey.question_count || 0 }} 题</span>
                <span class="flex items-center"><UserGroupIcon class="mr-1 h-4 w-4" aria-hidden="true" />{{ survey.response_count || 0 }} 人参与</span>
              </div>

              <div v-if="survey.expires_at" class="mt-3 text-xs text-slate-500 dark:text-slate-400">
                截止：{{ formatDate(survey.expires_at) }}
              </div>
            </article>
          </div>
        </template>
      </section>

      <div v-if="totalPages > 1 && !initialLoading" class="mt-8 flex flex-wrap items-center justify-center gap-2">
        <button class="glass-button px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50" type="button" :disabled="currentPage === 1 || refreshing" @click="changePage(currentPage - 1)">上一页</button>
        <span class="flex min-w-32 items-center justify-center gap-2 px-4 text-slate-600 dark:text-slate-400">
          <ArrowPathIcon v-if="refreshing" class="h-4 w-4 animate-spin" aria-hidden="true" />
          第 {{ currentPage }} / {{ totalPages }} 页
        </span>
        <button class="glass-button px-4 py-2 disabled:cursor-not-allowed disabled:opacity-50" type="button" :disabled="currentPage === totalPages || refreshing" @click="changePage(currentPage + 1)">下一页</button>
      </div>
    </div>

    <div v-if="showCreateDialog" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm" @click.self="showCreateDialog = false">
      <div class="glass-panel mx-4 max-h-[90vh] w-full max-w-2xl overflow-y-auto p-6" role="dialog" aria-modal="true" aria-labelledby="create-survey-title">
        <div class="mb-4 flex items-center justify-between">
          <h2 id="create-survey-title" class="text-xl font-bold">发布新问卷</h2>
          <button class="text-slate-500 hover:text-slate-700 dark:hover:text-slate-300" type="button" aria-label="关闭" @click="showCreateDialog = false"><XMarkIcon class="h-6 w-6" aria-hidden="true" /></button>
        </div>

        <form class="space-y-4" @submit.prevent="createSurvey">
          <div>
            <label class="mb-1 block text-sm font-medium" for="survey-title">标题</label>
            <input id="survey-title" v-model="newSurvey.title" required class="form-control" placeholder="请输入问卷标题">
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium" for="survey-description">描述</label>
            <textarea id="survey-description" v-model="newSurvey.description" class="form-control" rows="3" placeholder="问卷描述（可选）"></textarea>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <div>
              <label class="mb-1 block text-sm font-medium" for="survey-start">开始时间</label>
              <input id="survey-start" v-model="newSurvey.starts_at" type="datetime-local" class="form-control">
            </div>
            <div>
              <label class="mb-1 block text-sm font-medium" for="survey-end">截止时间</label>
              <input id="survey-end" v-model="newSurvey.expires_at" type="datetime-local" class="form-control">
            </div>
          </div>
          <div>
            <label class="mb-1 block text-sm font-medium" for="survey-status">状态</label>
            <select id="survey-status" v-model="newSurvey.status" class="form-control">
              <option value="draft">草稿</option>
              <option value="active">发布</option>
            </select>
          </div>
          <div class="flex justify-end gap-3 pt-4">
            <button class="btn-secondary" type="button" @click="showCreateDialog = false">取消</button>
            <button class="btn-primary" type="submit" :disabled="creating">{{ creating ? '发布中…' : '发布问卷' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowPathIcon, DocumentTextIcon, PlusIcon, UserGroupIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { surveysApi, type Survey } from '@/api/surveys'
import { useAuthStore } from '@/stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const surveys = ref<Survey[]>([])
const initialLoading = ref(true)
const refreshing = ref(false)
const loadError = ref('')
const currentPage = ref(1)
const totalPages = ref(1)
const showCreateDialog = ref(false)
const creating = ref(false)
let requestId = 0

const isAdmin = computed(() => authStore.user?.role === 'admin' || authStore.user?.role === 'root')
const newSurvey = ref({
  title: '',
  description: '',
  starts_at: '',
  expires_at: '',
  status: 'draft' as 'draft' | 'active',
})

async function loadSurveys() {
  const currentRequest = ++requestId
  const hasContent = surveys.value.length > 0
  initialLoading.value = !hasContent
  refreshing.value = hasContent
  loadError.value = ''
  try {
    const response = await surveysApi.list({ page: currentPage.value, page_size: 20 })
    if (currentRequest !== requestId) return
    surveys.value = response.data.items || []
    totalPages.value = Math.max(response.data.total_pages || 1, 1)
  } catch (error) {
    if (currentRequest !== requestId) return
    console.error('Failed to load surveys:', error)
    loadError.value = '问卷加载失败，请稍后重试。'
  } finally {
    if (currentRequest === requestId) {
      initialLoading.value = false
      refreshing.value = false
    }
  }
}

function changePage(page: number) {
  if (page < 1 || page > totalPages.value || refreshing.value) return
  currentPage.value = page
  void loadSurveys()
}

function goToSurvey(id: number) {
  void router.push(`/surveys/${id}`)
}

function statusText(status: Survey['status']): string {
  return { active: '进行中', draft: '草稿', closed: '已关闭', expired: '已过期' }[status]
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return `${date.toLocaleDateString('zh-CN')} ${date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
}

async function createSurvey() {
  if (!newSurvey.value.title.trim()) return
  creating.value = true
  try {
    await surveysApi.create({
      title: newSurvey.value.title.trim(),
      description: newSurvey.value.description.trim() || null,
      starts_at: newSurvey.value.starts_at || null,
      expires_at: newSurvey.value.expires_at || null,
      status: newSurvey.value.status,
      questions: [],
    })
    showCreateDialog.value = false
    newSurvey.value = { title: '', description: '', starts_at: '', expires_at: '', status: 'draft' }
    void loadSurveys()
  } catch (error) {
    console.error('Failed to create survey:', error)
    alert('发布失败，请重试')
  } finally {
    creating.value = false
  }
}

onMounted(() => void loadSurveys())
</script>
