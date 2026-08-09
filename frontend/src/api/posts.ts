import http from './http'
import type { Comment, PageResult, Post } from '@/types'

export const postsApi = {
  get(postId: number) {
    return http.get<Post>(`/posts/${postId}`)
  },

  comments(postId: number, page = 1, pageSize = 50) {
    return http.get<PageResult<Comment>>(`/posts/${postId}/comments`, {
      params: { page, page_size: pageSize },
    })
  },

  createComment(postId: number, content: string, parentId?: number) {
    return http.post<Comment>(`/posts/${postId}/comments`, {
      content,
      parent_id: parentId,
    })
  },
}
