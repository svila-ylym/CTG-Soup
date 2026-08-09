import http from './http'
import type { ProfileSoupSummary, PublicProfile } from '@/types'

export const profileApi = {
  get(uid: number, page = 1, pageSize = 20) {
    return http.get<PublicProfile>(`/users/${uid}/profile`, {
      params: { page, page_size: pageSize },
    })
  },

  updateFeaturedSoups(soupIds: number[]) {
    return http.put<ProfileSoupSummary[]>('/users/me/featured-soups', {
      soup_ids: soupIds,
    })
  },

  follow(uid: number) {
    return http.post('/social/follow', { target_uid: uid })
  },

  unfollow(uid: number) {
    return http.delete(`/social/follow/${uid}`)
  },
}
