import http from './http'
import type { TurtleSoup, SoupCreate, SoupScore, PageResult, PageParams } from '@/types'

export const soupApi = {
  // 获取海龟汤列表
  getList(params?: PageParams & { tag?: string; sort?: string }) {
    return http.get<PageResult<TurtleSoup>>('/soups', { params })
  },

  // 获取海龟汤详情
  getById(id: number) {
    return http.get<TurtleSoup>(`/soups/${id}`)
  },

  // 创建海龟汤
  create(data: SoupCreate) {
    return http.post<{ id: number }>('/soups', data)
  },

  // 更新海龟汤
  update(id: number, data: Partial<SoupCreate>) {
    return http.put(`/soups/${id}`, data)
  },

  // 删除海龟汤
  delete(id: number) {
    return http.delete(`/soups/${id}`)
  },

  // 评分
  score(data: SoupScore) {
    return http.post('/soups/score', data)
  },

  // 获取我的评分
  getMyScore(soupId: number) {
    return http.get<{ score: number }>(`/soups/${soupId}/my-score`)
  },

  // 点赞
  like(id: number) {
    return http.post(`/soups/${id}/like`)
  },

  // 取消点赞
  unlike(id: number) {
    return http.delete(`/soups/${id}/like`)
  },

  // 收藏
  favorite(id: number) {
    return http.post(`/soups/${id}/favorite`)
  },

  // 取消收藏
  unfavorite(id: number) {
    return http.delete(`/soups/${id}/favorite`)
  },

  // 获取排行榜
  getLeaderboard(params?: { limit?: number; type?: 'average' | 'bayesian' }) {
    return http.get<TurtleSoup[]>('/soups/leaderboard', { params })
  },

  // 搜索海龟汤
  search(keyword: string, params?: PageParams) {
    return http.get<PageResult<TurtleSoup>>('/soups/search', { params: { keyword, ...params } })
  },
}
