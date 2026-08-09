<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import DOMPurify from 'dompurify'
import { useRoute, useRouter } from 'vue-router'
import {
  EyeIcon,
  PaperAirplaneIcon,
  PaperClipIcon,
  XMarkIcon,
} from '@heroicons/vue/24/outline'
import {
  adminEmailCampaignsApi,
  adminSystemMessagesApi,
  type EmailCampaignInput,
  type RecipientMode,
  type SystemMessageInput,
} from '@/api/systemMessages'
import { extractApiError } from '@/utils/auth'
import type {
  BroadcastUser,
  EmailCampaignCategory,
  EmailCampaignSummary,
  SystemMessageAttachment,
} from '@/types'

type CenterTab = 'system' | 'email'

const route = useRoute()
const router = useRouter()
const activeTab = ref<CenterTab>(route.query.tab === 'email' ? 'email' : 'system')
const users = ref<BroadcastUser[]>([])
const selectedUids = ref<number[]>([])
const emailSelectedUids = ref<number[]>([])
const attachments = ref<SystemMessageAttachment[]>([])
const emailAttachments = ref<SystemMessageAttachment[]>([])
const title = ref('')
const markdown = ref('')
const subject = ref('')
const emailMarkdown = ref('')
const recipientMode = ref<RecipientMode>('selected')
const emailRecipientMode = ref<RecipientMode>('selected')
const emailCategory = ref<EmailCampaignCategory>('notice')
const previewHtml = ref('')
const emailPreviewHtml = ref('')
const campaigns = ref<EmailCampaignSummary[]>([])
const loadingUsers = ref(true)
const loadingCampaigns = ref(false)
const uploading = ref(false)
const previewing = ref(false)
const emailPreviewing = ref(false)
const sending = ref(false)
const savingEmail = ref(false)
const actingCampaignId = ref<number | null>(null)
const error = ref('')
const success = ref('')
const fileInput = ref<HTMLInputElement | null>(null)

const sanitizeOptions = {
  ALLOWED_TAGS: ['a', 'blockquote', 'br', 'code', 'del', 'em', 'h1', 'h2', 'h3', 'h4', 'hr', 'li', 'ol', 'p', 'pre', 'strong', 'ul'],
  ALLOWED_ATTR: ['href', 'title'],
  ALLOW_UNKNOWN_PROTOCOLS: false,
}
const safePreview = computed(() => DOMPurify.sanitize(previewHtml.value, sanitizeOptions))
const safeEmailPreview = computed(() => DOMPurify.sanitize(emailPreviewHtml.value, sanitizeOptions))
const activeUsers = computed(() => users.value.filter((user) => user.status === 'active'))
const emailEligibleUsers = computed(() => activeUsers.value.filter((user) => user.allow_bulk_email === true))
const recipientCount = computed(() => recipientMode.value === 'all' ? activeUsers.value.length : selectedUids.value.length)
const emailSelectedCount = computed(() => emailRecipientMode.value === 'all' ? activeUsers.value.length : emailSelectedUids.value.length)
const emailEligibleCount = computed(() => emailRecipientMode.value === 'all'
  ? emailEligibleUsers.value.length
  : emailSelectedUids.value.filter((uid) => emailEligibleUsers.value.some((user) => user.uid === uid)).length)
const emailFilteredCount = computed(() => Math.max(0, emailSelectedCount.value - emailEligibleCount.value))

function formatBytes(value: number) {
  if (value < 1024) return `${value} B`
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KiB`
  return `${(value / (1024 * 1024)).toFixed(1)} MiB`
}

function formatDate(value: string | null) {
  if (!value) return '-'
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

function statusLabel(status: EmailCampaignSummary['status']) {
  return {
    draft: '草稿', queued: '排队中', sending: '发送中', completed: '已完成', cancelled: '已取消',
  }[status]
}

function clearFeedback() {
  error.value = ''
  success.value = ''
}

function setActiveTab(tab: CenterTab) {
  activeTab.value = tab
  clearFeedback()
  void router.replace({ query: { ...route.query, tab } })
}

async function loadUsers() {
  loadingUsers.value = true
  error.value = ''
  try {
    const first = await adminSystemMessagesApi.users(1, 100)
    const allUsers = [...(first.data.items || [])]
    for (let page = 2; page <= (first.data.total_pages || 0); page += 1) {
      const response = await adminSystemMessagesApi.users(page, 100)
      allUsers.push(...(response.data.items || []))
    }
    users.value = allUsers
  } catch (reason) {
    error.value = extractApiError(reason, '用户列表加载失败')
  } finally {
    loadingUsers.value = false
  }
}

async function loadCampaigns() {
  loadingCampaigns.value = true
  try {
    campaigns.value = (await adminEmailCampaignsApi.list(1, 50)).data.items || []
  } catch (reason) {
    error.value = extractApiError(reason, '邮件活动加载失败')
  } finally {
    loadingCampaigns.value = false
  }
}

function toggleRecipient(uid: number, email = false) {
  const target = email ? emailSelectedUids : selectedUids
  const index = target.value.indexOf(uid)
  if (index >= 0) target.value.splice(index, 1)
  else target.value.push(uid)
}

async function previewSystemMessage() {
  if (!markdown.value.trim()) return
  previewing.value = true
  error.value = ''
  try {
    previewHtml.value = (await adminSystemMessagesApi.preview(markdown.value)).data.rendered_html
  } catch (reason) {
    error.value = extractApiError(reason, '预览生成失败')
  } finally {
    previewing.value = false
  }
}

async function previewEmail() {
  if (!emailMarkdown.value.trim()) return
  emailPreviewing.value = true
  error.value = ''
  try {
    emailPreviewHtml.value = (await adminSystemMessagesApi.preview(emailMarkdown.value)).data.rendered_html
  } catch (reason) {
    error.value = extractApiError(reason, '预览生成失败')
  } finally {
    emailPreviewing.value = false
  }
}

async function chooseFiles(event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  input.value = ''
  if (!files.length) return
  const target = activeTab.value === 'email' ? emailAttachments : attachments
  const existingSize = target.value.reduce((sum, item) => sum + item.size, 0)
  const newSize = files.reduce((sum, file) => sum + file.size, 0)
  if (
    target.value.length + files.length > 5
    || files.some((file) => file.size <= 0 || file.size > 10 * 1024 * 1024)
    || existingSize + newSize > 25 * 1024 * 1024
  ) {
    error.value = '附件最多 5 个，单个不能超过 10 MiB，总大小不能超过 25 MiB'
    return
  }
  uploading.value = true
  error.value = ''
  try {
    target.value.push(...(await adminSystemMessagesApi.attachments(files)).data)
  } catch (reason) {
    error.value = extractApiError(reason, '附件上传失败')
  } finally {
    uploading.value = false
  }
}

function removeAttachment(id: number, email = false) {
  if (email) emailAttachments.value = emailAttachments.value.filter((item) => item.id !== id)
  else attachments.value = attachments.value.filter((item) => item.id !== id)
}

async function sendSystemMessage() {
  if (!title.value.trim() || !markdown.value.trim()) return
  if (recipientMode.value === 'selected' && !selectedUids.value.length) {
    error.value = '请至少选择一个收件人'
    return
  }
  sending.value = true
  clearFeedback()
  try {
    const data: SystemMessageInput = {
      title: title.value,
      markdown: markdown.value,
      recipient_mode: recipientMode.value,
      recipient_uids: recipientMode.value === 'selected' ? selectedUids.value : [],
      attachment_ids: attachments.value.map((item) => item.id),
    }
    const response = await adminSystemMessagesApi.send(data)
    success.value = `已发送给 ${response.data.recipient_count} 位用户`
    title.value = ''
    markdown.value = ''
    previewHtml.value = ''
    selectedUids.value = []
    attachments.value = []
  } catch (reason) {
    error.value = extractApiError(reason, '系统消息发送失败')
  } finally {
    sending.value = false
  }
}

async function createEmailCampaign(queueAfter = false) {
  if (!subject.value.trim() || !emailMarkdown.value.trim()) return
  if (emailRecipientMode.value === 'selected' && !emailSelectedUids.value.length) {
    error.value = '请至少选择一个收件人'
    return
  }
  savingEmail.value = true
  clearFeedback()
  try {
    const data: EmailCampaignInput = {
      subject: subject.value,
      markdown: emailMarkdown.value,
      category: emailCategory.value,
      recipient_mode: emailRecipientMode.value,
      recipient_uids: emailRecipientMode.value === 'selected' ? emailSelectedUids.value : [],
      attachment_ids: emailAttachments.value.map((item) => item.id),
    }
    const created = (await adminEmailCampaignsApi.create(data)).data
    subject.value = ''
    emailMarkdown.value = ''
    emailPreviewHtml.value = ''
    emailSelectedUids.value = []
    emailAttachments.value = []
    if (queueAfter) {
      try {
        await adminEmailCampaignsApi.queue(created.id)
      } catch (reason) {
        error.value = extractApiError(reason, '草稿已保存，但加入发件队列失败')
        await loadCampaigns()
        return
      }
    }
    success.value = queueAfter ? '邮件活动已加入发件队列' : '邮件活动草稿已保存'
    await loadCampaigns()
  } catch (reason) {
    error.value = extractApiError(reason, '邮件活动保存失败')
  } finally {
    savingEmail.value = false
  }
}

async function queueCampaign(id: number) {
  actingCampaignId.value = id
  clearFeedback()
  try {
    await adminEmailCampaignsApi.queue(id)
    success.value = '邮件活动已加入发件队列'
    await loadCampaigns()
  } catch (reason) {
    error.value = extractApiError(reason, '邮件活动入队失败')
  } finally {
    actingCampaignId.value = null
  }
}

async function cancelCampaign(id: number) {
  actingCampaignId.value = id
  clearFeedback()
  try {
    await adminEmailCampaignsApi.cancel(id)
    success.value = '邮件活动已取消'
    await loadCampaigns()
  } catch (reason) {
    error.value = extractApiError(reason, '邮件活动取消失败')
  } finally {
    actingCampaignId.value = null
  }
}

onMounted(() => {
  void loadUsers()
  void loadCampaigns()
})

watch(() => route.query.tab, (tab) => {
  activeTab.value = tab === 'email' ? 'email' : 'system'
})
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-6xl">
      <header class="flex flex-wrap items-center justify-between gap-4 border-b border-slate-200 pb-5 dark:border-neutral-800">
        <div>
          <h1 class="section-title text-2xl">广播中心</h1>
          <p class="mt-1 text-sm text-slate-500">根用户工作台</p>
        </div>
        <router-link class="btn-secondary text-sm" to="/admin">返回管理后台</router-link>
      </header>

      <div class="mt-5 flex gap-1 border-b border-slate-200 dark:border-neutral-800" role="tablist" aria-label="广播类型">
        <button class="min-h-10 border-b-2 px-4 text-sm font-medium" :class="activeTab === 'system' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500'" type="button" role="tab" :aria-selected="activeTab === 'system'" @click="setActiveTab('system')">系统消息</button>
        <button class="min-h-10 border-b-2 px-4 text-sm font-medium" :class="activeTab === 'email' ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500'" type="button" role="tab" :aria-selected="activeTab === 'email'" @click="setActiveTab('email')">邮件群发</button>
      </div>

      <p v-if="error" class="mt-4 border-l-2 border-red-500 px-3 text-sm text-red-700 dark:text-red-300">{{ error }}</p>
      <p v-if="success" class="mt-4 border-l-2 border-emerald-500 px-3 text-sm text-emerald-700 dark:text-emerald-300">{{ success }}</p>
      <input ref="fileInput" class="hidden" type="file" multiple accept=".png,.jpg,.jpeg,.gif,.webp,.pdf,.txt,.zip" @change="chooseFiles">

      <div v-if="activeTab === 'system'" class="mt-6 grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
        <form class="min-w-0 space-y-6" @submit.prevent="sendSystemMessage">
          <section class="border-b border-slate-200 pb-6 dark:border-neutral-800">
            <h2 class="text-sm font-semibold">收件人</h2>
            <div class="mt-3 inline-flex border border-slate-300 p-1 dark:border-neutral-700" role="group" aria-label="收件人范围">
              <button class="min-h-9 px-4 text-sm" :class="recipientMode === 'selected' ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300'" type="button" @click="recipientMode = 'selected'">指定用户</button>
              <button class="min-h-9 px-4 text-sm" :class="recipientMode === 'all' ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300'" type="button" @click="recipientMode = 'all'">全部用户</button>
            </div>
            <div v-if="recipientMode === 'selected'" class="mt-4 max-h-64 overflow-y-auto border-y border-slate-200 dark:border-neutral-800">
              <p v-if="loadingUsers" class="p-4 text-sm text-slate-500">正在加载用户…</p>
              <label v-for="user in users" v-else :key="user.uid" class="flex min-h-12 items-center gap-3 border-b border-slate-100 px-2 py-2 last:border-0 dark:border-neutral-800">
                <input type="checkbox" :checked="selectedUids.includes(user.uid)" :disabled="user.status !== 'active'" @change="toggleRecipient(user.uid)">
                <span class="min-w-0 flex-1"><strong class="block truncate text-sm">{{ user.nickname }}</strong><span class="block truncate text-xs text-slate-500">@{{ user.username }} · UID {{ user.uid }}</span></span>
                <span v-if="user.status !== 'active'" class="shrink-0 text-xs text-slate-400">{{ user.status }}</span>
              </label>
            </div>
            <p class="mt-2 text-xs text-slate-500">收件人数：{{ recipientCount }}</p>
          </section>

          <section class="space-y-4 border-b border-slate-200 pb-6 dark:border-neutral-800">
            <label class="block text-sm font-medium">标题<input v-model="title" class="form-control mt-2" maxlength="200" required></label>
            <label class="block text-sm font-medium">正文<textarea v-model="markdown" class="form-control mt-2 min-h-64 font-mono text-sm" maxlength="50000" required></textarea></label>
            <button class="btn-secondary gap-2 text-sm" type="button" :disabled="previewing || !markdown.trim()" @click="previewSystemMessage"><EyeIcon class="h-4 w-4" aria-hidden="true" />{{ previewing ? '生成中…' : '预览' }}</button>
          </section>

          <section class="border-b border-slate-200 pb-6 dark:border-neutral-800">
            <div class="flex items-center justify-between gap-4"><h2 class="text-sm font-semibold">附件</h2><button class="btn-secondary gap-2 text-sm" type="button" :disabled="uploading || attachments.length >= 5" @click="fileInput?.click()"><PaperClipIcon class="h-4 w-4" aria-hidden="true" />{{ uploading ? '上传中…' : '选择文件' }}</button></div>
            <div v-if="attachments.length" class="mt-3 divide-y divide-slate-100 dark:divide-neutral-800"><div v-for="attachment in attachments" :key="attachment.id" class="flex min-w-0 items-center gap-3 py-2"><span class="min-w-0 flex-1 truncate text-sm" :title="attachment.original_name">{{ attachment.original_name }}</span><span class="shrink-0 text-xs text-slate-500">{{ formatBytes(attachment.size) }}</span><button class="p-1 text-slate-400 hover:text-red-600" type="button" aria-label="移除附件" title="移除附件" @click="removeAttachment(attachment.id)"><XMarkIcon class="h-4 w-4" /></button></div></div>
          </section>
          <button class="btn-primary gap-2" type="submit" :disabled="sending || uploading || !title.trim() || !markdown.trim() || (recipientMode === 'selected' && !selectedUids.length)"><PaperAirplaneIcon class="h-4 w-4" aria-hidden="true" />{{ sending ? '发送中…' : '发送系统消息' }}</button>
        </form>
        <aside class="min-w-0 border-slate-200 dark:border-neutral-800 lg:border-l lg:pl-6"><h2 class="text-sm font-semibold">预览</h2><div v-if="safePreview" class="broadcast-preview mt-4 break-words" v-html="safePreview"></div><p v-else class="mt-4 text-sm text-slate-500">暂无预览</p></aside>
      </div>

      <div v-else class="mt-6 space-y-10">
        <div class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_360px]">
          <form class="min-w-0 space-y-6" @submit.prevent="createEmailCampaign(false)">
            <section class="border-b border-slate-200 pb-6 dark:border-neutral-800">
              <h2 class="text-sm font-semibold">收件人</h2>
              <div class="mt-3 inline-flex border border-slate-300 p-1 dark:border-neutral-700" role="group" aria-label="邮件收件人范围"><button class="min-h-9 px-4 text-sm" :class="emailRecipientMode === 'selected' ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300'" type="button" @click="emailRecipientMode = 'selected'">指定用户</button><button class="min-h-9 px-4 text-sm" :class="emailRecipientMode === 'all' ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300'" type="button" @click="emailRecipientMode = 'all'">全部用户</button></div>
              <div v-if="emailRecipientMode === 'selected'" class="mt-4 max-h-64 overflow-y-auto border-y border-slate-200 dark:border-neutral-800"><p v-if="loadingUsers" class="p-4 text-sm text-slate-500">正在加载用户…</p><label v-for="user in users" v-else :key="user.uid" class="flex min-h-12 items-center gap-3 border-b border-slate-100 px-2 py-2 last:border-0 dark:border-neutral-800" :title="user.status !== 'active' ? '用户未激活' : user.allow_bulk_email !== true ? '用户未开启批量邮件' : undefined"><input type="checkbox" :checked="emailSelectedUids.includes(user.uid)" :disabled="user.status !== 'active' || user.allow_bulk_email !== true" @change="toggleRecipient(user.uid, true)"><span class="min-w-0 flex-1"><strong class="block truncate text-sm">{{ user.nickname }}</strong><span class="block truncate text-xs text-slate-500">@{{ user.username }} · UID {{ user.uid }}</span></span><span v-if="user.status !== 'active'" class="shrink-0 text-xs text-slate-400">{{ user.status }}</span><span v-else-if="user.allow_bulk_email !== true" class="shrink-0 text-xs text-slate-400">未订阅</span></label></div>
              <p class="mt-2 break-words text-xs text-slate-500">已选择 {{ emailSelectedCount }}，符合条件 {{ emailEligibleCount }}，已过滤 {{ emailFilteredCount }}</p>
            </section>

            <section class="space-y-4 border-b border-slate-200 pb-6 dark:border-neutral-800">
              <div><span class="block text-sm font-medium">邮件类别</span><div class="mt-2 inline-flex border border-slate-300 p-1 dark:border-neutral-700" role="group" aria-label="邮件类别"><button class="min-h-9 px-4 text-sm" :class="emailCategory === 'notice' ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300'" type="button" @click="emailCategory = 'notice'">通知</button><button class="min-h-9 px-4 text-sm" :class="emailCategory === 'promotion' ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300'" type="button" @click="emailCategory = 'promotion'">推广</button></div></div>
              <label class="block text-sm font-medium">主题<input v-model="subject" class="form-control mt-2" maxlength="200" required></label>
              <label class="block text-sm font-medium">正文<textarea v-model="emailMarkdown" class="form-control mt-2 min-h-64 font-mono text-sm" maxlength="50000" required></textarea></label>
              <button class="btn-secondary gap-2 text-sm" type="button" :disabled="emailPreviewing || !emailMarkdown.trim()" @click="previewEmail"><EyeIcon class="h-4 w-4" aria-hidden="true" />{{ emailPreviewing ? '生成中…' : '预览' }}</button>
            </section>

            <section class="border-b border-slate-200 pb-6 dark:border-neutral-800"><div class="flex items-center justify-between gap-4"><h2 class="text-sm font-semibold">附件</h2><button class="btn-secondary gap-2 text-sm" type="button" :disabled="uploading || emailAttachments.length >= 5" @click="fileInput?.click()"><PaperClipIcon class="h-4 w-4" aria-hidden="true" />{{ uploading ? '上传中…' : '选择文件' }}</button></div><div v-if="emailAttachments.length" class="mt-3 divide-y divide-slate-100 dark:divide-neutral-800"><div v-for="attachment in emailAttachments" :key="attachment.id" class="flex min-w-0 items-center gap-3 py-2"><span class="min-w-0 flex-1 truncate text-sm" :title="attachment.original_name">{{ attachment.original_name }}</span><span class="shrink-0 text-xs text-slate-500">{{ formatBytes(attachment.size) }}</span><button class="p-1 text-slate-400 hover:text-red-600" type="button" aria-label="移除附件" title="移除附件" @click="removeAttachment(attachment.id, true)"><XMarkIcon class="h-4 w-4" /></button></div></div></section>
            <div class="flex flex-wrap gap-3"><button class="btn-secondary" type="submit" :disabled="savingEmail || uploading || !subject.trim() || !emailMarkdown.trim() || (emailRecipientMode === 'selected' && !emailSelectedUids.length)">{{ savingEmail ? '保存中…' : '保存草稿' }}</button><button class="btn-primary gap-2" type="button" :disabled="savingEmail || uploading || !subject.trim() || !emailMarkdown.trim() || (emailRecipientMode === 'selected' && !emailSelectedUids.length)" @click="createEmailCampaign(true)"><PaperAirplaneIcon class="h-4 w-4" aria-hidden="true" />保存并入队</button></div>
          </form>
          <aside class="min-w-0 border-slate-200 dark:border-neutral-800 lg:border-l lg:pl-6"><h2 class="text-sm font-semibold">预览</h2><div v-if="safeEmailPreview" class="broadcast-preview mt-4 break-words" v-html="safeEmailPreview"></div><p v-else class="mt-4 text-sm text-slate-500">暂无预览</p></aside>
        </div>

        <section class="border-t border-slate-200 pt-6 dark:border-neutral-800"><div class="flex items-center justify-between gap-4"><h2 class="text-sm font-semibold">邮件活动</h2><button class="btn-secondary shrink-0 text-sm" type="button" :disabled="loadingCampaigns" @click="loadCampaigns">刷新</button></div><p v-if="loadingCampaigns" class="mt-4 text-sm text-slate-500">正在加载…</p><p v-else-if="!campaigns.length" class="mt-4 text-sm text-slate-500">暂无邮件活动</p><div v-else class="mt-4 divide-y divide-slate-200 border-y border-slate-200 dark:divide-neutral-800 dark:border-neutral-800"><div v-for="campaign in campaigns" :key="campaign.id" class="flex flex-wrap items-center gap-4 py-4"><div class="min-w-0 flex-1"><strong class="block truncate text-sm" :title="campaign.subject">{{ campaign.subject }}</strong><span class="mt-1 block break-words text-xs text-slate-500">{{ campaign.category === 'notice' ? '通知' : '推广' }} · {{ statusLabel(campaign.status) }} · {{ formatDate(campaign.created_at) }}</span><span class="mt-1 block break-words text-xs text-slate-500">已选择 {{ campaign.selected_count }} · 符合条件 {{ campaign.eligible_count }} · 已过滤 {{ campaign.filtered_count }} · 已送达 {{ campaign.delivered_count }} · 失败 {{ campaign.failed_count }}</span></div><button v-if="campaign.status === 'draft'" class="btn-primary shrink-0 text-sm" type="button" :disabled="actingCampaignId === campaign.id" @click="queueCampaign(campaign.id)">{{ actingCampaignId === campaign.id ? '处理中…' : '加入队列' }}</button><button v-else-if="campaign.status === 'queued' || campaign.status === 'sending'" class="btn-secondary shrink-0 text-sm" type="button" :disabled="actingCampaignId === campaign.id" @click="cancelCampaign(campaign.id)">{{ actingCampaignId === campaign.id ? '处理中…' : '取消' }}</button></div></div></section>
      </div>
    </div>
  </main>
</template>

<style scoped>
.broadcast-preview :deep(h1),
.broadcast-preview :deep(h2),
.broadcast-preview :deep(h3),
.broadcast-preview :deep(h4) { margin: 1rem 0 0.5rem; font-weight: 700; }
.broadcast-preview :deep(p),
.broadcast-preview :deep(ul),
.broadcast-preview :deep(ol),
.broadcast-preview :deep(blockquote),
.broadcast-preview :deep(pre) { margin: 0.75rem 0; }
.broadcast-preview :deep(ul),
.broadcast-preview :deep(ol) { padding-left: 1.25rem; }
.broadcast-preview :deep(ul) { list-style: disc; }
.broadcast-preview :deep(ol) { list-style: decimal; }
.broadcast-preview :deep(a) { color: #2563eb; text-decoration: underline; }
.broadcast-preview :deep(pre) { overflow-x: auto; background: #111111; padding: 0.75rem; color: #f8fafc; }
</style>
