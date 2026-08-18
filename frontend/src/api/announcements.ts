import http from './http'
import type { Announcement, PageResult } from '@/types'

export const announcementsApi = {
  list(params?: { page?: number; page_size?: number }) {
    return http.get<PageResult<Announcement>>('/announcements', { params })
  },

  get(id: number) {
    return http.get<Announcement>(`/announcements/${id}`)
  },

  create(data: { title: string; content: string; priority?: number }) {
    return http.post<Announcement>('/announcements', data)
  },

  update(id: number, data: { title: string; content: string; priority?: number }) {
    return http.put<Announcement>(`/announcements/${id}`, data)
  },

  delete(id: number) {
    return http.delete(`/announcements/${id}`)
  },

  publish(id: number) {
    return http.post(`/announcements/${id}/publish`)
  },

  withdraw(id: number) {
    return http.post(`/announcements/${id}/withdraw`)
  },
}
