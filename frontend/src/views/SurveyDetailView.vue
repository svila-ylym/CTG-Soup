<template>
  <div class="survey-page page-shell">
    <div class="page-container">
      <button class="mb-4 flex items-center text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white" type="button" @click="$router.push('/surveys')">
        <ArrowLeftIcon class="mr-1 h-5 w-5" aria-hidden="true" />
        返回问卷列表
      </button>

      <div v-if="initialLoading" class="glass-panel p-6" aria-busy="true" aria-label="正在加载问卷详情">
        <div class="border-b border-slate-200 pb-5 dark:border-slate-700">
          <div class="skeleton-block h-8 w-2/5"></div>
          <div class="skeleton-block mt-4 h-4 w-3/4"></div>
          <div class="skeleton-block mt-3 h-4 w-1/2"></div>
        </div>
        <div class="mt-6 space-y-6">
          <div v-for="item in 3" :key="item" class="glass-card min-h-36 p-5">
            <div class="flex justify-between gap-4">
              <span class="skeleton-block h-5 w-3/5"></span>
              <span class="skeleton-block h-6 w-14 rounded-full"></span>
            </div>
            <div class="skeleton-block mt-6 h-11 w-full"></div>
          </div>
        </div>
      </div>

      <div v-else-if="loadError && !survey" class="glass-card p-8 text-center" role="alert">
        <DocumentTextIcon class="mx-auto h-12 w-12 text-slate-400" aria-hidden="true" />
        <p class="mt-4 text-red-700 dark:text-red-300">{{ loadError }}</p>
        <button class="btn-secondary mt-5" type="button" @click="loadSurvey">重新加载</button>
      </div>

      <div v-else-if="survey" class="glass-panel p-6">
        <div class="mb-6 border-b border-slate-200 pb-4 dark:border-slate-700">
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white">{{ survey.title }}</h1>
          <p v-if="survey.description" class="mt-2 text-slate-600 dark:text-slate-400">{{ survey.description }}</p>
          <div class="mt-3 flex flex-wrap items-center gap-4 text-sm text-slate-500 dark:text-slate-400">
            <span v-if="survey.starts_at">开始：{{ formatDate(survey.starts_at) }}</span>
            <span v-if="survey.expires_at">截止：{{ formatDate(survey.expires_at) }}</span>
            <span :class="{
              'text-green-600 dark:text-green-400': survey.status === 'active',
              'text-slate-600 dark:text-slate-400': survey.status === 'draft',
              'text-red-600 dark:text-red-400': survey.status === 'closed' || survey.status === 'expired',
            }">{{ statusText(survey.status) }}</span>
          </div>
        </div>

        <div v-if="alreadySubmitted" class="mb-6 rounded-lg bg-green-50 p-4 text-green-800 dark:bg-green-900/20 dark:text-green-300" role="status">
          <CheckCircleIcon class="mr-1 inline-block h-5 w-5" aria-hidden="true" />
          您已完成此问卷
        </div>

        <form class="space-y-6" @submit.prevent="submitSurvey">
          <div v-for="(question, index) in survey.questions || []" :key="question.id" class="glass-card p-5">
            <div class="mb-3 flex items-start justify-between gap-3">
              <label class="text-base font-medium text-slate-900 dark:text-white">
                {{ index + 1 }}. {{ question.question_text }}
                <span v-if="question.required" class="text-red-500">*</span>
              </label>
              <span class="shrink-0 rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-300">{{ questionTypeText(question.question_type) }}</span>
            </div>

            <div v-if="question.question_type === 'single_choice'" class="space-y-2">
              <label v-for="(option, optIndex) in question.options || []" :key="optIndex" class="flex cursor-pointer items-center gap-2 rounded-lg p-2 hover:bg-slate-50 dark:hover:bg-slate-800">
                <input v-model="answers[question.id]" type="radio" :name="`q_${question.id}`" :value="optIndex" class="h-4 w-4 text-blue-600">
                <span class="text-slate-700 dark:text-slate-300">{{ option }}</span>
              </label>
            </div>

            <div v-else-if="question.question_type === 'multiple_choice'" class="space-y-2">
              <label v-for="(option, optIndex) in question.options || []" :key="optIndex" class="flex cursor-pointer items-center gap-2 rounded-lg p-2 hover:bg-slate-50 dark:hover:bg-slate-800">
                <input v-model="multiAnswers[question.id]" type="checkbox" :value="optIndex" class="h-4 w-4 rounded text-blue-600">
                <span class="text-slate-700 dark:text-slate-300">{{ option }}</span>
              </label>
            </div>

            <div v-else-if="question.question_type === 'rating'" class="flex gap-2">
              <button v-for="rating in 5" :key="rating" type="button" class="text-2xl transition hover:scale-110" :class="rating <= Number(answers[question.id] || 0) ? 'text-yellow-500' : 'text-slate-300 dark:text-slate-600'" :aria-label="`${rating} 星`" @click="answers[question.id] = rating">★</button>
            </div>

            <div v-else>
              <textarea v-model="answers[question.id]" :required="question.required" class="form-control" rows="3" placeholder="请输入您的回答"></textarea>
            </div>
          </div>

          <div class="flex justify-end pt-4">
            <button class="btn-primary" type="submit" :disabled="submitting || alreadySubmitted">{{ submitting ? '提交中…' : '提交问卷' }}</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { ArrowLeftIcon, CheckCircleIcon, DocumentTextIcon } from '@heroicons/vue/24/outline'
import { surveysApi, type Survey, type SurveyAnswer } from '@/api/surveys'

const route = useRoute()
const survey = ref<Survey | null>(null)
const initialLoading = ref(true)
const loadError = ref('')
const submitting = ref(false)
const alreadySubmitted = ref(false)
const answers = ref<Record<number, string | number | null>>({})
const multiAnswers = ref<Record<number, number[]>>({})

async function loadSurvey() {
  initialLoading.value = true
  loadError.value = ''
  try {
    const id = Number(route.params.id)
    if (!Number.isInteger(id) || id <= 0) throw new Error('invalid survey id')
    const response = await surveysApi.getById(id)
    survey.value = response.data
    alreadySubmitted.value = Boolean(response.data.has_submitted)
    answers.value = {}
    multiAnswers.value = {}
    for (const question of response.data.questions || []) {
      if (question.question_type === 'multiple_choice') multiAnswers.value[question.id] = []
      else answers.value[question.id] = null
    }
  } catch (error) {
    console.error('Failed to load survey:', error)
    loadError.value = '问卷加载失败或问卷不存在。'
  } finally {
    initialLoading.value = false
  }
}

function statusText(status: Survey['status']): string {
  return { active: '进行中', draft: '草稿', closed: '已关闭', expired: '已过期' }[status]
}

function questionTypeText(type: string): string {
  return { single_choice: '单选题', multiple_choice: '多选题', text: '文本题', rating: '评分题' }[type] || type
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return `${date.toLocaleDateString('zh-CN')} ${date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })}`
}

async function submitSurvey() {
  if (!survey.value?.questions) return
  submitting.value = true
  try {
    const formattedAnswers: SurveyAnswer[] = survey.value.questions.map((question) => {
      if (question.question_type === 'multiple_choice') {
        const selected = multiAnswers.value[question.id] || []
        if (question.required && selected.length === 0) throw new Error(`请完成必填问题：${question.question_text}`)
        return { question_id: question.id, answer_option_ids: selected }
      }
      if (question.question_type === 'rating') {
        const rating = answers.value[question.id]
        if (question.required && rating == null) throw new Error(`请完成必填问题：${question.question_text}`)
        return { question_id: question.id, answer_rating: typeof rating === 'number' ? rating : null }
      }
      const value = answers.value[question.id]
      const text = value == null ? '' : String(value)
      if (question.required && !text.trim()) throw new Error(`请完成必填问题：${question.question_text}`)
      return { question_id: question.id, answer_text: text }
    })

    await surveysApi.submit(survey.value.id, { answers: formattedAnswers })
    alreadySubmitted.value = true
    alert('问卷提交成功！')
  } catch (error) {
    console.error('Failed to submit survey:', error)
    alert(error instanceof Error ? error.message : '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

onMounted(() => void loadSurvey())
</script>
