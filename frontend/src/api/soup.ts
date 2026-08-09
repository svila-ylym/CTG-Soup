import http from './http'
import type { TurtleSoup, SoupCreate, SoupScore, PageResult, PageParams, SoupGenre, SoupColor, Comment } from '@/types'

export interface SoupListParams extends Partial<PageParams> {
  tag?: string
  tag_id?: number
  genre?: Exclude<SoupGenre, '未分类'>
  soup_color?: Exclude<SoupColor, '未分类'>
  sort_by?: string
}

export const soupApi = {
  // 获取海龟汤列表
  getList(params?: SoupListParams) {
    return http.get<PageResult<TurtleSoup>>('/turtle-soups', { params })
  },

  // 获取海龟汤详情
  getById(id: number, reveal = false) {
    return http.get<TurtleSoup>(`/turtle-soups/${id}`, { params: { reveal } })
  },

  // 创建海龟汤
  create(data: SoupCreate) {
    return http.post<TurtleSoup>('/turtle-soups', data)
  },

  // 更新海龟汤
  update(id: number, data: Partial<SoupCreate>) {
    return http.put(`/turtle-soups/${id}`, data)
  },

  // 删除海龟汤
  delete(id: number) {
    return http.delete(`/turtle-soups/${id}`)
  },

  // 评分
  score(data: SoupScore) {
    return http.put(`/turtle-soups/${data.soup_id}/rating`, { score: data.score })
  },

  // 获取我的评分
  // 点赞
  like(id: number) {
    return http.put(`/turtle-soups/${id}/like`, { active: true })
  },

  // 取消点赞
  unlike(id: number) {
    return http.put(`/turtle-soups/${id}/like`, { active: false })
  },

  // 收藏
  favorite(id: number) {
    return http.put(`/turtle-soups/${id}/favorite`, { active: true })
  },

  // 取消收藏
  unfavorite(id: number) {
    return http.put(`/turtle-soups/${id}/favorite`, { active: false })
  },

  rate(id: number, score: number) {
    return http.put<{ average_score: number; rating_count: number; my_rating: number }>(`/turtle-soups/${id}/rating`, { score })
  },

  setInteraction(id: number, kind: 'like' | 'favorite', active: boolean) {
    return http.put<{ is_liked?: boolean; is_favorited?: boolean; like_count: number; favorite_count: number }>(`/turtle-soups/${id}/${kind}`, { active })
  },

  listComments(id: number, params?: { page?: number; page_size?: number }) {
    return http.get<PageResult<Comment>>(`/turtle-soups/${id}/comments`, { params })
  },

  createComment(id: number, content: string, parentId?: number) {
    return http.post<Comment>(`/turtle-soups/${id}/comments`, {
      content,
      parent_id: parentId,
    })
  },

  deleteComment(id: number, commentId: number) {
    return http.delete(`/turtle-soups/${id}/comments/${commentId}`)
  },

  getLeaderboard(params?: { limit?: number; type?: 'average' | 'bayesian' }) {
    const sort_by = params?.type === 'average' ? 'score' : 'bayesian'
    return http.get<PageResult<TurtleSoup>>('/turtle-soups', {
      params: { page: 1, page_size: params?.limit ?? 10, sort_by },
    })
  },

  search(keyword: string, params?: PageParams) {
    return http.get<PageResult<TurtleSoup>>('/search/turtle-soups', { params: { q: keyword, ...params } })
  },
}
