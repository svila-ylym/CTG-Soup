import http from './http'
import type { PageResult, SearchPost, SearchSoup, SearchUser } from '@/types'

function params(query: string, page: number, pageSize: number) {
  return { q: query, page, page_size: pageSize }
}

export const searchApi = {
  users(query: string, page = 1, pageSize = 20) {
    return http.get<PageResult<SearchUser>>('/search/users', {
      params: params(query, page, pageSize),
    })
  },

  posts(query: string, page = 1, pageSize = 20) {
    return http.get<PageResult<SearchPost>>('/search/posts', {
      params: params(query, page, pageSize),
    })
  },

  soups(query: string, page = 1, pageSize = 20) {
    return http.get<PageResult<SearchSoup>>('/search/turtle-soups', {
      params: params(query, page, pageSize),
    })
  },
}
