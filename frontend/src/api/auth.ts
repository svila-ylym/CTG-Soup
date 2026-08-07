import http from './http'
import type { LoginRequest, RegisterRequest, TokenResponse, User } from '@/types'

export const authApi = {
  // 登录
  login(data: LoginRequest) {
    return http.post<TokenResponse>('/auth/login', data)
  },

  // 注册
  register(data: RegisterRequest) {
    return http.post<{ uid: number }>('/auth/register', data)
  },

  // 刷新令牌
  refreshToken(refreshToken: string) {
    return http.post<TokenResponse>('/auth/refresh', { refresh_token: refreshToken })
  },

  // 登出
  logout() {
    return http.post('/auth/logout')
  },

  // 获取当前用户信息
  getCurrentUser() {
    return http.get<User>('/users/me')
  },

  // 发送邮箱验证
  sendVerificationEmail(email: string) {
    return http.post('/auth/send-verification', { email })
  },

  // 验证邮箱
  verifyEmail(code: string) {
    return http.post('/auth/verify-email', { code })
  },

  // 修改密码
  changePassword(oldPassword: string, newPassword: string) {
    return http.put('/auth/change-password', { old_password: oldPassword, new_password: newPassword })
  },

  // 重置密码请求
  requestPasswordReset(email: string) {
    return http.post('/auth/reset-password-request', { email })
  },

  // 重置密码
  resetPassword(token: string, newPassword: string) {
    return http.post('/auth/reset-password', { token, new_password: newPassword })
  },
}
