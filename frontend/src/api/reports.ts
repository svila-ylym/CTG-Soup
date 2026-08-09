import http from './http'

export type ReportTarget = 'post' | 'comment' | 'soup' | 'message' | 'user'

export interface ReportCreate {
  target_type: ReportTarget
  target_id: number
  reason: string
}

export const reportsApi = {
  submit(data: ReportCreate) {
    return http.post('/admin/reports', data)
  },
}
