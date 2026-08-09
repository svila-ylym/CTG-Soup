import http from './http'
import type {
  BroadcastUser,
  EmailCampaignCategory,
  EmailCampaignSummary,
  PageResult,
  SystemMessageAttachment,
  SystemMessageDetail,
  SystemMessagePage,
  SystemMessageSendResult,
} from '@/types'

export type RecipientMode = 'selected' | 'all'

export interface SystemMessageInput {
  title: string
  markdown: string
  recipient_mode: RecipientMode
  recipient_uids: number[]
  attachment_ids: number[]
}

export interface EmailCampaignInput {
  subject: string
  markdown: string
  category: EmailCampaignCategory
  recipient_mode: RecipientMode
  recipient_uids: number[]
  attachment_ids: number[]
}

export const systemMessagesApi = {
  list(page = 1, pageSize = 20) {
    return http.get<SystemMessagePage>('/system-messages', {
      params: { page, page_size: pageSize },
    })
  },

  detail(messageId: number) {
    return http.get<SystemMessageDetail>(`/system-messages/${messageId}`)
  },

  read(messageId: number) {
    return http.put<SystemMessageDetail>(`/system-messages/${messageId}/read`)
  },

  attachment(attachmentId: number) {
    return http.get<Blob>(`/system-messages/attachments/${attachmentId}`, {
      responseType: 'blob',
    })
  },
}

export const adminSystemMessagesApi = {
  users(page = 1, pageSize = 100) {
    return http.get<PageResult<BroadcastUser>>('/admin/users', {
      params: { page, page_size: pageSize },
    })
  },

  preview(markdown: string) {
    return http.post<{ rendered_html: string }>('/admin/system-messages/preview', {
      markdown,
    })
  },

  attachments(files: File[]) {
    const form = new FormData()
    for (const file of files) form.append('files', file)
    return http.post<SystemMessageAttachment[]>(
      '/admin/system-messages/attachments/batch',
      form,
    )
  },

  send(data: SystemMessageInput) {
    return http.post<SystemMessageSendResult>('/admin/system-messages', data)
  },
}

export const adminEmailCampaignsApi = {
  list(page = 1, pageSize = 20) {
    return http.get<PageResult<EmailCampaignSummary>>('/admin/email-campaigns', {
      params: { page, page_size: pageSize },
    })
  },

  create(data: EmailCampaignInput) {
    return http.post<EmailCampaignSummary>('/admin/email-campaigns', data)
  },

  queue(campaignId: number) {
    return http.post<EmailCampaignSummary>(`/admin/email-campaigns/${campaignId}/queue`)
  },

  cancel(campaignId: number) {
    return http.post<EmailCampaignSummary>(`/admin/email-campaigns/${campaignId}/cancel`)
  },
}
