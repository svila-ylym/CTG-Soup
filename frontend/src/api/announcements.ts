import http from './http'
import type { Announcement, PageResult } from '@/types'

export const announcementsApi = {
  list(params?: { page?: number; page_size?: number }) {
    return http.get<PageResult<Announcement>>('/announcements', { params })
  },
}
