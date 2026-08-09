import http from './http'
import type { SigninStatus } from '@/types'

export const signinApi = {
  status() {
    return http.get<SigninStatus>('/users/me/signin')
  },

  signin() {
    return http.post<SigninStatus>('/users/me/signin')
  },
}
