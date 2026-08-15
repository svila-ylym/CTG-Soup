import http from './http'
import type { PageParams, PageResult } from '@/types'

export interface SurveyQuestion {
  id: number
  survey_id?: number
  question_text: string
  question_type: 'single_choice' | 'multiple_choice' | 'text' | 'rating'
  options?: string[] | null
  required: boolean
  sort_order: number
  created_at?: string
}

export interface Survey {
  id: number
  title: string
  description?: string | null
  status: 'draft' | 'active' | 'closed' | 'expired'
  starts_at?: string | null
  expires_at?: string | null
  notification_sent: boolean
  author_uid: number
  created_at: string
  updated_at: string
  questions?: SurveyQuestion[]
  question_count?: number
  response_count?: number
  has_submitted?: boolean
}

export type SurveyQuestionInput = Omit<SurveyQuestion, 'id' | 'survey_id' | 'created_at'>

export interface SurveyCreate {
  title: string
  description?: string | null
  status?: 'draft' | 'active' | 'closed' | 'expired'
  starts_at?: string | null
  expires_at?: string | null
  questions?: SurveyQuestionInput[]
}

export interface SurveyUpdate {
  title?: string | null
  description?: string | null
  status?: 'draft' | 'active' | 'closed' | 'expired'
  starts_at?: string | null
  expires_at?: string | null
}

export interface SurveyAnswer {
  question_id: number
  answer_text?: string | null
  answer_option_ids?: number[] | null
  answer_rating?: number | null
}

export interface SurveySubmit {
  answers: SurveyAnswer[]
}

export interface SurveyStatistics {
  survey_id: number
  total_responses: number
  question_stats: Array<{
    question_id: number
    question_text: string
    total_answers: number
    option_distribution?: Record<number, number>
    average_rating?: number
  }>
}

export const surveysApi = {
  list(params: PageParams & { status?: 'active' | 'all' }) {
    return http.get<PageResult<Survey>>('/surveys', { params })
  },

  getById(id: number) {
    return http.get<Survey>(`/surveys/${id}`)
  },

  create(data: SurveyCreate) {
    return http.post<Survey>('/surveys', data)
  },

  update(id: number, data: SurveyUpdate) {
    return http.put<Survey>(`/surveys/${id}`, data)
  },

  submit(id: number, data: SurveySubmit) {
    return http.post<{ message: string }>(`/surveys/${id}/submit`, data)
  },

  getStatistics(id: number) {
    return http.get<SurveyStatistics>(`/surveys/${id}/statistics`)
  },
}
