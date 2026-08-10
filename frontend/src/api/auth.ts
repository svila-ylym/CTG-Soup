import http from './http'
import type { LoginRequest, RegisterRequest, TokenResponse, User } from '@/types'

export const authApi = {
  // 登录
  login(data: LoginRequest) {
    const form = new URLSearchParams()
    form.set('username', data.username)
    form.set('password', data.password)
    return http.post<TokenResponse>('/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    })
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
    return http.get<User>('/auth/me')
  },

  // 发送邮箱验证
  sendVerificationEmail(email: string) {
    return http.post('/auth/send-verification', { email })
  },

  // 验证邮箱
  verifyEmail(token: string) {
    return http.post<{ message: string }>('/auth/verify-email', { token })
  },

  // 修改密码
  changePassword(oldPassword: string, newPassword: string) {
    return http.put('/auth/change-password', { old_password: oldPassword, new_password: newPassword })
  },

  // 重置密码请求
  requestPasswordReset(email: string) {
    return http.post<{ message: string }>('/auth/reset-password-request', { email })
  },

  // 重置密码
  resetPassword(token: string, newPassword: string) {
    return http.post<{ message: string }>('/auth/reset-password', { token, new_password: newPassword })
  },
}
