<template>
  <div class="page-shell">
    <div class="page-container">
      <!-- 返回按钮 -->
      <button @click="$router.push('/surveys')" class="mb-4 flex items-center text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white">
        <ArrowLeftIcon class="mr-1 h-5 w-5" />
        返回问卷列表
      </button>

      <div v-if="loading" class="flex items-center justify-center py-12">
        <ArrowPathIcon class="h-8 w-8 animate-spin text-blue-600" />
      </div>

      <div v-else-if="!survey" class="glass-card p-8 text-center">
        <DocumentTextIcon class="mx-auto h-12 w-12 text-slate-400" />
        <p class="mt-4 text-slate-600 dark:text-slate-400">问卷不存在</p>
      </div>

      <div v-else class="glass-panel p-6">
        <!-- 问卷头部 -->
        <div class="mb-6 border-b border-slate-200 pb-4 dark:border-slate-700">
          <h1 class="text-2xl font-bold text-slate-900 dark:text-white">{{ survey.title }}</h1>
          <p v-if="survey.description" class="mt-2 text-slate-600 dark:text-slate-400">{{ survey.description }}</p>
          <div class="mt-3 flex items-center gap-4 text-sm text-slate-500 dark:text-slate-500">
            <span v-if="survey.starts_at">开始：{{ formatDate(survey.starts_at) }}</span>
            <span v-if="survey.expires_at">截止：{{ formatDate(survey.expires_at) }}</span>
            <span :class="{
              'text-green-600 dark:text-green-400': survey.status === 'active',
              'text-slate-600 dark:text-slate-400': survey.status === 'draft',
              'text-red-600 dark:text-red-400': survey.status === 'closed' || survey.status === 'expired'
            }">
              {{ statusText(survey.status) }}
            </span>
          </div>
        </div>

        <!-- 已提交提示 -->
        <div v-if="alreadySubmitted" class="mb-6 rounded-lg bg-green-50 p-4 text-green-800 dark:bg-green-900/20 dark:text-green-300">
          <CheckCircleIcon class="inline-block h-5 w-5" />
          您已完成此问卷
        </div>

        <!-- 问题列表 -->
        <form @submit.prevent="submitSurvey" class="space-y-6">
          <div v-for="(question, index) in survey.questions" :key="question.id" class="glass-card p-5">
            <div class="mb-3 flex items-start justify-between">
              <label class="text-base font-medium text-slate-900 dark:text-white">
                {{ index + 1 }}. {{ question.question_text }}
                <span v-if="question.required" class="text-red-500">*</span>
              </label>
              <span class="rounded-full bg-slate-100 px-2 py-1 text-xs text-slate-600 dark:bg-slate-700 dark:text-slate-400">
                {{ questionTypeText(question.question_type) }}
              </span>
            </div>

            <!-- 单选 -->
            <div v-if="question.question_type === 'single_choice'" class="space-y-2">
              <label v-for="(option, optIndex) in (question.options || [])" :key="optIndex" 
                     class="flex cursor-pointer items-center gap-2 rounded-lg p-2 hover:bg-slate-50 dark:hover:bg-slate-800">
                <input type="radio" :name="'q_' + question.id" :value="optIndex" v-model="answers[question.id]"
                       class="h-4 w-4 text-blue-600" />
                <span class="text-slate-700 dark:text-slate-300">{{ option }}</span>
              </label>
            </div>

            <!-- 多选 -->
            <div v-else-if="question.question_type === 'multiple_choice'" class="space-y-2">
              <label v-for="(option, optIndex) in (question.options || [])" :key="optIndex"
                     class="flex cursor-pointer items-center gap-2 rounded-lg p-2 hover:bg-slate-50 dark:hover:bg-slate-800">
                <input type="checkbox" :value="optIndex" v-model="multiAnswers[question.id]"
                       class="h-4 w-4 rounded text-blue-600" />
                <span class="text-slate-700 dark:text-slate-300">{{ option }}</span>
              </label>
            </div>

            <!-- 评分 -->
            <div v-else-if="question.question_type === 'rating'" class="flex gap-2">
              <button v-for="n in 5" :key="n" type="button"
                      @click="answers[question.id] = n"
                      :class="n <= (answers[question.id] || 0) ? 'text-yellow-500' : 'text-slate-300 dark:text-slate-600'"
                      class="text-2xl transition hover:scale-110">★</button>
            </div>

            <!-- 文本 -->
            <div v-else-if="question.question_type === 'text'">
              <textarea v-model="answers[question.id]" :required="question.required"
                        class="form-control" rows="3" placeholder="请输入您的回答"></textarea>
            </div>
          </div>

          <div class="flex justify-end pt-4">
            <button type="submit" :disabled="submitting || alreadySubmitted" 
                    class="btn-primary glass-button disabled:opacity-50">
              {{ submitting ? '提交中...' : '提交问卷' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { DocumentTextIcon, ArrowPathIcon, ArrowLeftIcon, CheckCircleIcon } from '@heroicons/vue/24/outline'
import { surveysApi, type Survey, type SurveyQuestion } from '@/api/surveys'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const survey = ref<Survey | null>(null)
const loading = ref(true)
const submitting = ref(false)
const alreadySubmitted = ref(false)
const answers = ref<Record<number, any>>({})
const multiAnswers = ref<Record<number, number[]>>({})

async function loadSurvey() {
  loading.value = true
  try {
    const id = Number(route.params.id)
    const res = await surveysApi.getById(id)
    survey.value = res.data
    
    // 初始化答案
    if (res.data.questions) {
      for (const q of res.data.questions) {
        if (q.question_type === 'multiple_choice') {
          multiAnswers.value[q.id] = []
        } else {
          answers.value[q.id] = null
        }
      }
    }
    
    // 检查是否已提交（通过尝试获取统计信息）
    try {
      await surveysApi.getStatistics(id)
    } catch (e: any) {
      if (e.response?.status === 403) {
        alreadySubmitted.value = true
      }
    }
  } catch (err) {
    console.error('Failed to load survey:', err)
  } finally {
    loading.value = false
  }
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

function questionTypeText(type: string): string {
  const map: Record<string, string> = {
    single_choice: '单选题',
    multiple_choice: '多选题',
    text: '文本题',
    rating: '评分题'
  }
  return map[type] || type
}

function formatDate(dateStr: string): string {
  const date = new Date(dateStr)
  return date.toLocaleDateString('zh-CN') + ' ' + date.toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
}

async function submitSurvey() {
  if (!survey.value || !survey.value.questions) return
  
  submitting.value = true
  try {
    const formattedAnswers = survey.value.questions.map(q => {
      let answer: any = {}
      if (q.question_type === 'multiple_choice') {
        answer = { question_id: q.id, answer_option_ids: multiAnswers.value[q.id] || [] }
      } else if (q.question_type === 'rating') {
        answer = { question_id: q.id, answer_rating: answers.value[q.id] }
      } else {
        answer = { question_id: q.id, answer_text: answers.value[q.id] }
      }
      if (q.required && !answer.answer_text && !answer.answer_option_ids?.length && answer.answer_rating === undefined) {
        throw new Error(`请完成必填问题：${q.question_text}`)
      }
      return answer
    })
    
    await surveysApi.submit(survey.value.id, { answers: formattedAnswers })
    alert('问卷提交成功！')
    alreadySubmitted.value = true
  } catch (err: any) {
    console.error('Failed to submit survey:', err)
    alert(err.message || '提交失败，请重试')
  } finally {
    submitting.value = false
  }
}

onMounted(loadSurvey)
</script>
