import http from './http'
import type {
  PageResult,
  SoupCollectionDetail,
  SoupCollectionInput,
  SoupCollectionSummary,
} from '@/types'

export const collectionApi = {
  list(ownerUid: number, page = 1, pageSize = 20) {
    return http.get<PageResult<SoupCollectionSummary>>('/collections', {
      params: { owner_uid: ownerUid, page, page_size: pageSize },
    })
  },

  mine(page = 1, pageSize = 100) {
    return http.get<PageResult<SoupCollectionSummary>>('/collections/mine', {
      params: { page, page_size: pageSize },
    })
  },

  get(id: number, page = 1, pageSize = 20) {
    return http.get<SoupCollectionDetail>(`/collections/${id}`, {
      params: { page, page_size: pageSize },
    })
  },

  create(input: SoupCollectionInput) {
    return http.post<SoupCollectionSummary>('/collections', input)
  },

  update(id: number, input: SoupCollectionInput) {
    return http.put<SoupCollectionSummary>(`/collections/${id}`, input)
  },

  delete(id: number) {
    return http.delete(`/collections/${id}`)
  },
}
