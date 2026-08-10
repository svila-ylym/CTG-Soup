import { defineStore } from 'pinia'
import { ref } from 'vue'
import http from '@/api/http'
import { systemMessagesApi } from '@/api/systemMessages'
import type { PageResult } from '@/types'

type UnreadResponse = PageResult<unknown>

export const useUnreadStore = defineStore('unread', () => {
  const hasNotifications = ref(false)
  const hasSystemMessages = ref(false)
  let pollTimer: number | undefined
  let stateGeneration = 0
  let notificationRequestId = 0
  let systemMessageRequestId = 0

  async function refreshNotifications() {
    const generation = stateGeneration
    const requestId = ++notificationRequestId
    try {
      const response = await http.get<UnreadResponse>('/notifications', {
        params: { page: 1, page_size: 1, unread_only: true },
      })
      if (generation !== stateGeneration || requestId !== notificationRequestId) return
      hasNotifications.value = response.data.total > 0
    } catch {
      // Preserve the last known state when an optional indicator refresh fails.
    }
  }

  async function refreshSystemMessages() {
    const generation = stateGeneration
    const requestId = ++systemMessageRequestId
    try {
      const response = await systemMessagesApi.list(1, 1, true)
      if (generation !== stateGeneration || requestId !== systemMessageRequestId) return
      hasSystemMessages.value = response.data.total > 0
    } catch {
      // Preserve the last known state when an optional indicator refresh fails.
    }
  }

  async function refreshAll() {
    await Promise.all([refreshNotifications(), refreshSystemMessages()])
  }

  function startPolling() {
    if (pollTimer !== undefined) return
    void refreshAll()
    pollTimer = window.setInterval(() => {
      void refreshAll()
    }, 30000)
  }

  function stopPolling() {
    if (pollTimer !== undefined) window.clearInterval(pollTimer)
    pollTimer = undefined
  }

  function markSystemMessagesUnread() {
    systemMessageRequestId += 1
    hasSystemMessages.value = true
  }

  function reset() {
    stateGeneration += 1
    stopPolling()
    hasNotifications.value = false
    hasSystemMessages.value = false
  }

  return {
    hasNotifications,
    hasSystemMessages,
    refreshNotifications,
    refreshSystemMessages,
    refreshAll,
    startPolling,
    stopPolling,
    markSystemMessagesUnread,
    reset,
  }
})
