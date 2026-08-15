import http from './http'
import type { HomeDiscovery } from '@/types'

export const homeApi = {
  discovery(refresh = false) {
    return http.get<HomeDiscovery>('/home/discovery', {
      params: refresh ? { refresh: true } : undefined,
    })
  },
}
