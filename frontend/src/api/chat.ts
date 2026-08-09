import http from './http'
import type {
  ChatMessage,
  ConversationPage,
  DirectConversation,
  MessageCursorPage,
} from '@/types'

interface ReadConversationResult {
  conversation_id: number
  last_read_message_id: number | null
  read_count: number
}

export const chatApi = {
  conversations() {
    return http.get<ConversationPage>('/messages/conversations')
  },

  createConversation(userUid: number) {
    return http.post<DirectConversation>('/messages/conversations', {
      user_uid: userUid,
    })
  },

  messages(conversationId: number, beforeId?: number, limit = 50) {
    return http.get<MessageCursorPage>(
      `/messages/conversations/${conversationId}/messages`,
      { params: { before_id: beforeId, limit } },
    )
  },

  send(conversationId: number, content: string) {
    return http.post<ChatMessage>(
      `/messages/conversations/${conversationId}/messages`,
      { content },
    )
  },

  read(conversationId: number, messageId?: number) {
    return http.put<ReadConversationResult>(`/messages/conversations/${conversationId}/read`, {
      message_id: messageId,
    })
  },
}
