import http from './http'
import type { PageResult, Tag } from '@/types'

export const tagApi = {
  list(params?: {
    page?: number
    page_size?: number
    kind?: 'system' | 'custom'
    keyword?: string
    sort_by?: 'usage_count' | 'view_count' | 'name'
  }) {
    return http.get<PageResult<Tag>>('/tags', { params })
  },
}
