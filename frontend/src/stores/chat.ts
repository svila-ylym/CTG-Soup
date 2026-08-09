import { computed, ref, shallowRef } from 'vue'
import { defineStore } from 'pinia'
import { chatApi } from '@/api/chat'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import type { ChatMessage, ConversationPage, DirectConversation } from '@/types'

export type ChatSocketStatus = 'offline' | 'connecting' | 'connected'
export type DeliveryStatus = 'sending' | 'failed'

export type ChatItem = ChatMessage & {
  clientId?: string
  deliveryStatus?: DeliveryStatus
  sendError?: string
}

type SocketEvent = {
  type?: string
  message?: ChatMessage | string
  id?: number
  conversation_id?: number
  message_id?: number
  sender_uid?: number
  receiver_uid?: number
  content?: string
  is_read?: boolean
  created_at?: string
  reader_uid?: number
  user_uid?: number
  code?: string
  message_text?: string
}

function sortConversations(items: DirectConversation[]) {
  items.sort((left, right) => {
    const leftTime = left.last_message_at ? Date.parse(left.last_message_at) : 0
    const rightTime = right.last_message_at ? Date.parse(right.last_message_at) : 0
    return rightTime - leftTime || right.id - left.id
  })
}

function sortMessages(items: ChatItem[]) {
  items.sort((left, right) => {
    const timeDifference = Date.parse(left.created_at) - Date.parse(right.created_at)
    return timeDifference || left.id - right.id
  })
}

function newClientId() {
  return `local-${Date.now()}-${Math.random().toString(36).slice(2)}`
}

export const useChatStore = defineStore('chat', () => {
  const auth = useAuthStore()
  const conversations = ref<DirectConversation[]>([])
  const messagesByConversation = ref<Record<number, ChatItem[]>>({})
  const cursors = ref<Record<number, number | null>>({})
  const loadedConversations = ref<Record<number, boolean>>({})
  const activeConversationId = ref<number | null>(null)
  const loadingConversations = ref(false)
  const loadingMessages = ref(false)
  const loadingOlderMessages = ref(false)
  const error = ref('')
  const socketStatus = ref<ChatSocketStatus>('offline')
  const socketError = ref('')
  const remoteTyping = ref<Record<number, boolean>>({})
  const socket = shallowRef<WebSocket | null>(null)

  let shouldReconnect = false
  let reconnectTimer: number | undefined
  let pollTimer: number | undefined

  const activeConversation = computed(() =>
    conversations.value.find((conversation) => conversation.id === activeConversationId.value) || null,
  )
  const activeMessages = computed(() =>
    activeConversationId.value === null
      ? []
      : messagesByConversation.value[activeConversationId.value] || [],
  )
  const hasMoreMessages = computed(() =>
    activeConversationId.value !== null && cursors.value[activeConversationId.value] !== undefined && cursors.value[activeConversationId.value] !== null,
  )
  const isTyping = computed(() =>
    activeConversationId.value !== null && remoteTyping.value[activeConversationId.value] === true,
  )

  function currentUid() {
    const raw = auth.user?.uid ?? localStorage.getItem('user_uid')
    const uid = typeof raw === 'number' ? raw : Number(raw)
    return Number.isInteger(uid) && uid > 0 ? uid : null
  }

  function upsertConversation(conversation: DirectConversation) {
    const index = conversations.value.findIndex((item) => item.id === conversation.id)
    if (index >= 0) {
      conversations.value[index] = {
        ...conversations.value[index],
        ...conversation,
      }
    } else {
      conversations.value.push(conversation)
    }
    sortConversations(conversations.value)
  }

  function upsertMessage(conversationId: number, message: ChatItem) {
    const items = messagesByConversation.value[conversationId] || []
    const existingIndex = message.clientId
      ? items.findIndex((item) => item.clientId === message.clientId)
      : items.findIndex((item) => item.id === message.id)
    const previous = existingIndex >= 0 ? items[existingIndex] : undefined
    if (existingIndex >= 0) {
      items[existingIndex] = { ...items[existingIndex], ...message }
    } else {
      items.push(message)
    }
    messagesByConversation.value[conversationId] = items
    sortMessages(items)

    const conversation = conversations.value.find((item) => item.id === conversationId)
    if (!conversation) return
    const wasNewIncoming = !previous && message.receiver_uid === currentUid()
    conversation.last_message = message
    conversation.last_message_at = message.created_at
    if (wasNewIncoming && activeConversationId.value !== conversationId && !message.is_read) {
      conversation.unread_count += 1
    }
    sortConversations(conversations.value)
  }

  function removeLocalMessage(conversationId: number, clientId: string) {
    const items = messagesByConversation.value[conversationId]
    if (!items) return
    messagesByConversation.value[conversationId] = items.filter((item) => item.clientId !== clientId)
  }

  async function loadConversations() {
    loadingConversations.value = true
    error.value = ''
    try {
      const response = await chatApi.conversations()
      const payload = response.data as ConversationPage
      conversations.value = payload.items || []
      sortConversations(conversations.value)
    } catch (reason) {
      error.value = extractApiError(reason, '会话暂时无法加载')
    } finally {
      loadingConversations.value = false
    }
  }

  async function loadMessages(conversationId: number, beforeId?: number, replace = false) {
    if (beforeId) loadingOlderMessages.value = true
    else loadingMessages.value = true
    try {
      const response = await chatApi.messages(conversationId, beforeId)
      const payload = response.data
      const existing = messagesByConversation.value[conversationId] || []
      if (replace) {
        messagesByConversation.value[conversationId] = payload.items || []
        sortMessages(messagesByConversation.value[conversationId])
      } else {
        for (const message of payload.items || []) upsertMessage(conversationId, message)
        if (!existing.length && payload.items?.length) {
          messagesByConversation.value[conversationId] = [...payload.items]
          sortMessages(messagesByConversation.value[conversationId])
        }
      }
      cursors.value[conversationId] = payload.next_cursor
      loadedConversations.value[conversationId] = true
      return payload
    } catch (reason) {
      error.value = extractApiError(reason, '消息暂时无法加载')
      return null
    } finally {
      loadingMessages.value = false
      loadingOlderMessages.value = false
    }
  }

  async function markRead(conversationId = activeConversationId.value) {
    if (conversationId === null) return
    const uid = currentUid()
    const items = messagesByConversation.value[conversationId] || []
    const lastIncoming = [...items]
      .reverse()
      .find((item) => item.receiver_uid === uid && !item.deliveryStatus)
    if (!lastIncoming) return
    try {
      await chatApi.read(conversationId, lastIncoming.id)
      for (const item of items) {
        if (item.receiver_uid === uid && item.id <= lastIncoming.id) item.is_read = true
      }
      const conversation = conversations.value.find((item) => item.id === conversationId)
      if (conversation) conversation.unread_count = 0
    } catch {
      // A later poll can reconcile the read cursor.
    }
  }

  async function openConversation(conversationId: number) {
    if (!conversations.value.some((conversation) => conversation.id === conversationId)) return
    if (activeConversationId.value !== null && activeConversationId.value !== conversationId) {
      setTyping(false, activeConversationId.value)
    }
    activeConversationId.value = conversationId
    remoteTyping.value[conversationId] = false
    if (!loadedConversations.value[conversationId]) {
      await loadMessages(conversationId, undefined, true)
    }
    await markRead(conversationId)
  }

  async function openConversationForUser(userUid: number) {
    const existing = conversations.value.find((conversation) => conversation.other_user.uid === userUid)
    if (existing) {
      await openConversation(existing.id)
      return existing
    }
    try {
      const response = await chatApi.createConversation(userUid)
      upsertConversation(response.data)
      await openConversation(response.data.id)
      return response.data
    } catch (reason) {
      error.value = extractApiError(reason, '无法打开会话')
      return null
    }
  }

  function updateDeliveryStatus(conversationId: number, clientId: string, status: DeliveryStatus, messageText = '') {
    const item = messagesByConversation.value[conversationId]?.find((message) => message.clientId === clientId)
    if (item) {
      item.deliveryStatus = status
      item.sendError = messageText
    }
  }

  async function sendMessage(content: string, retryClientId?: string) {
    const conversation = activeConversation.value
    const uid = currentUid()
    const normalized = content.trim()
    if (!conversation || !uid || !normalized) return false
    const receiverUid = conversation.other_user.uid
    const clientId = retryClientId || newClientId()
    let localMessage = messagesByConversation.value[conversation.id]?.find((item) => item.clientId === clientId)
    if (localMessage) {
      localMessage.deliveryStatus = 'sending'
      localMessage.sendError = ''
    } else {
      localMessage = {
        id: -Date.now(),
        conversation_id: conversation.id,
        sender_uid: uid,
        receiver_uid: receiverUid,
        content: normalized,
        is_read: false,
        created_at: new Date().toISOString(),
        clientId,
        deliveryStatus: 'sending',
      }
      upsertMessage(conversation.id, localMessage)
    }
    try {
      const response = await chatApi.send(conversation.id, normalized)
      removeLocalMessage(conversation.id, clientId)
      upsertMessage(conversation.id, response.data)
      return true
    } catch (reason) {
      updateDeliveryStatus(conversation.id, clientId, 'failed', extractApiError(reason, '发送失败'))
      return false
    }
  }

  async function retryMessage(message: ChatItem) {
    if (!message.clientId || message.deliveryStatus !== 'failed') return false
    return sendMessage(message.content, message.clientId)
  }

  function sendSocketEvent(event: Record<string, unknown>) {
    if (socket.value?.readyState !== WebSocket.OPEN) return false
    socket.value.send(JSON.stringify(event))
    return true
  }

  function setTyping(typing: boolean, conversationId = activeConversationId.value) {
    if (conversationId === null) return
    sendSocketEvent({
      type: typing ? 'typing.start' : 'typing.stop',
      conversation_id: conversationId,
    })
  }

  function handleSocketEvent(event: SocketEvent) {
    const uid = currentUid()
    if (event.type === 'message.created') {
      const message = typeof event.message === 'object' && event.message !== null
        ? event.message
        : event.id && event.conversation_id && event.sender_uid && event.receiver_uid && event.content !== undefined && event.created_at
          ? {
              id: event.id,
              conversation_id: event.conversation_id,
              sender_uid: event.sender_uid,
              receiver_uid: event.receiver_uid,
              content: event.content,
              is_read: event.is_read ?? false,
              created_at: event.created_at,
            }
          : null
      if (!message) return
      if (!conversations.value.some((conversation) => conversation.id === message.conversation_id)) {
        void loadConversations()
        return
      }
      const known = messagesByConversation.value[message.conversation_id]?.some((item) => item.id === message.id)
      upsertMessage(message.conversation_id, message)
      if (!known && message.receiver_uid === uid && activeConversationId.value === message.conversation_id) {
        void markRead(message.conversation_id)
      }
      return
    }
    if (event.type === 'message.read' && event.conversation_id && event.message_id) {
      const items = messagesByConversation.value[event.conversation_id] || []
      for (const item of items) {
        if (item.sender_uid === uid && item.id > 0 && item.id <= event.message_id) item.is_read = true
      }
      return
    }
    if ((event.type === 'typing.start' || event.type === 'typing.stop') && event.conversation_id) {
      if (event.user_uid !== uid) remoteTyping.value[event.conversation_id] = event.type === 'typing.start'
      return
    }
    if (event.type === 'presence.error') {
      socketError.value = (typeof event.message === 'string' ? event.message : '') || event.message_text || event.code || '实时消息暂不可用'
      if (event.code?.startsWith('WS_AUTH_')) socketStatus.value = 'offline'
    }
  }

  function startPolling() {
    if (pollTimer !== undefined) return
    pollTimer = window.setInterval(() => {
      if (activeConversationId.value !== null) {
        const conversationId = activeConversationId.value
        void (async () => {
          await loadMessages(conversationId)
          await markRead(conversationId)
        })()
      } else {
        void loadConversations()
      }
    }, 5000)
  }

  function scheduleReconnect() {
    if (!shouldReconnect || reconnectTimer !== undefined) return
    reconnectTimer = window.setTimeout(() => {
      reconnectTimer = undefined
      connect()
    }, 5000)
  }

  function connect() {
    shouldReconnect = true
    if (socket.value && (socketStatus.value === 'connecting' || socketStatus.value === 'connected')) return
    const token = localStorage.getItem('access_token')
    if (!token) return
    const wsUrl = new URL('/ws/messages', window.location.href)
    wsUrl.protocol = wsUrl.protocol === 'https:' ? 'wss:' : 'ws:'
    const connection = new WebSocket(wsUrl.toString())
    socket.value = connection
    socketStatus.value = 'connecting'
    socketError.value = ''
    connection.onopen = () => {
      if (socket.value !== connection) return
      connection.send(JSON.stringify({ type: 'auth', token }))
      socketStatus.value = 'connected'
      if (pollTimer !== undefined) {
        window.clearInterval(pollTimer)
        pollTimer = undefined
      }
    }
    connection.onmessage = (message) => {
      try {
        handleSocketEvent(JSON.parse(message.data) as SocketEvent)
      } catch {
        socketError.value = '实时消息格式无效'
      }
    }
    connection.onerror = () => {
      socketError.value = '实时消息连接失败，已切换为轮询'
    }
    connection.onclose = () => {
      if (socket.value === connection) socket.value = null
      socketStatus.value = 'offline'
      remoteTyping.value = {}
      startPolling()
      scheduleReconnect()
    }
  }

  function disconnect() {
    shouldReconnect = false
    if (reconnectTimer !== undefined) window.clearTimeout(reconnectTimer)
    if (pollTimer !== undefined) window.clearInterval(pollTimer)
    reconnectTimer = undefined
    pollTimer = undefined
    setTyping(false)
    socket.value?.close()
    socket.value = null
    socketStatus.value = 'offline'
  }

  function closeConversation() {
    setTyping(false)
    activeConversationId.value = null
  }

  return {
    conversations,
    messagesByConversation,
    activeConversationId,
    activeConversation,
    activeMessages,
    hasMoreMessages,
    loadingConversations,
    loadingMessages,
    loadingOlderMessages,
    error,
    socketStatus,
    socketError,
    isTyping,
    loadConversations,
    loadMessages,
    openConversation,
    openConversationForUser,
    closeConversation,
    markRead,
    sendMessage,
    retryMessage,
    setTyping,
    connect,
    disconnect,
  }
})
