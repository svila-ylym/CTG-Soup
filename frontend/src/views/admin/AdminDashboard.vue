<script setup lang="ts">
import LinkifiedText from '@/components/LinkifiedText.vue'
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { ArrowDownTrayIcon, ArrowPathIcon, ShieldExclamationIcon, TrashIcon } from '@heroicons/vue/24/outline'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { formatChinaDateTime } from '@/utils/datetime'
import type { Announcement, Competition, PageResult, Tag } from '@/types'

type AdminTab = 'reports' | 'users' | 'punishments' | 'competitions' | 'tags' | 'groups' | 'announcements' | 'updates' | 'logs'
type UserRole = 'user' | 'admin' | 'root'
type UserStatus = 'pending_email' | 'active' | 'banned' | 'silenced'

interface AdminUser {
  uid: number
  username: string
  nickname: string
  email: string
  role: UserRole
  status: UserStatus
  allow_bulk_email: boolean
  group_ids: number[]
  created_at: string
}

interface AdminReport {
  id: number
  reporter_uid: number
  target_type: string
  target_id: number
  target_exists?: boolean
  target_url?: string | null
  target_author_uid?: number | null
  target_preview?: string | null
  reason: string
  status: 'pending' | 'processed' | 'rejected'
  handler_uid?: number | null
  handle_result?: string | null
  handled_at?: string | null
  created_at: string
}

interface AdminPunishment {
  id: number
  target_uid: number
  operator_uid: number
  punishment_type: string
  reason: string
  start_time: string
  end_time?: string | null
  is_revoked: boolean
  is_active?: boolean
  revoked_at?: string | null
  revoked_by?: number | null
  revoke_reason?: string | null
}

interface PermissionGroup {
  id: number
  name: string
  description?: string | null
  permissions: string[]
  member_uids: number[]
  member_count: number
  permission_text: string
  created_at: string
  updated_at: string
}

interface OperationLog {
  id: number
  operator_uid: number
  operator_username?: string | null
  operator_roles: string[]
  action_type: string
  target_type: string
  target_id?: number | null
  details?: Record<string, unknown> | null
  created_at: string
}

interface UpdateStatus {
  current_version: string
  latest_version?: string | null
  tag_name?: string | null
  release_name?: string | null
  published_at?: string | null
  html_url?: string | null
  status: 'up_to_date' | 'update_available' | 'ahead' | 'invalid_latest_version' | 'unknown_current_version' | 'no_release' | 'error'
  update_available: boolean
  checked_at: string
  error?: string | null
}

interface UpdateTask {
  task_id: string
  status: 'queued' | 'running' | 'succeeded' | 'failed'
  tag_name: string
  started_at?: string | null
  finished_at?: string | null
  exit_code?: number | null
  log_path?: string | null
  error?: string | null
}

const auth = useAuthStore()
const activeTab = ref<AdminTab>('reports')
const users = ref<AdminUser[]>([])
const reports = ref<AdminReport[]>([])
const punishments = ref<AdminPunishment[]>([])
const competitions = ref<Competition[]>([])
const tags = ref<Tag[]>([])
const groups = ref<PermissionGroup[]>([])
const announcements = ref<Announcement[]>([])
const logs = ref<OperationLog[]>([])
const reportFilter = ref<'all' | 'pending' | 'processed' | 'rejected'>('pending')
const reportDrafts = ref<Record<number, string>>({})
const punishmentReasons = ref<Record<number, string>>({})
const revokeReasons = ref<Record<number, string>>({})
const userRevokeReasons = ref<Record<number, string>>({})
const mergeTargets = ref<Record<number, number | null>>({})
const loading = ref(true)
const error = ref('')
const message = ref('')
const savingKey = ref('')
const groupForm = ref({ name: '', description: '', permissions: '' })
const tagForm = ref({ name: '', description: '', kind: 'custom' as 'custom' | 'system' })
const announcementForm = ref({ title: '', content: '', priority: 0 })
const updateInfo = ref<UpdateStatus | null>(null)
const updateTask = ref<UpdateTask | null>(null)
const updateChecking = ref(false)
let updatePollTimer: number | undefined

const pendingReportCount = computed(() => reports.value.filter((report) => report.status === 'pending').length)
const activePunishmentCount = computed(() => punishments.value.filter((item) => item.is_active ?? !item.is_revoked).length)
const tabs = computed<Array<{ key: AdminTab; label: string; count: number }>>(() => {
  const items: Array<{ key: AdminTab; label: string; count: number }> = [
    { key: 'reports', label: '举报', count: pendingReportCount.value },
    { key: 'users', label: '用户', count: users.value.length },
    { key: 'punishments', label: '处罚', count: activePunishmentCount.value },
    { key: 'competitions', label: '比赛', count: competitions.value.length },
    { key: 'tags', label: '标签', count: tags.value.length },
    { key: 'groups', label: '用户组', count: groups.value.length },
    { key: 'announcements', label: '公告', count: announcements.value.length },
    { key: 'updates', label: '系统更新', count: updateInfo.value?.update_available ? 1 : 0 },
  ]
  if (auth.isRoot) items.push({ key: 'logs', label: '日志', count: logs.value.length })
  return items
})

const visibleReports = computed(() => (
  reportFilter.value === 'all'
    ? reports.value
    : reports.value.filter((report) => report.status === reportFilter.value)
))

function showError(reason: unknown, fallback: string) {
  error.value = extractApiError(reason, fallback)
}

function splitPermissions(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

function formatDate(value: string) {
  return formatChinaDateTime(value)
}

function targetLabel(targetType: string) {
  return ({ post: '帖子', comment: '评论', soup: '海龟汤', message: '私信', user: '用户' } as Record<string, string>)[targetType] || targetType
}

function punishmentLabel(value: string) {
  return ({ ban: '封禁', silence: '禁言', delete_content: '删除内容', disable_comment: '禁用评论', rate_limit: '限流' } as Record<string, string>)[value] || value
}

function formatDetails(value?: Record<string, unknown> | null) {
  return value ? JSON.stringify(value, null, 2) : '—'
}

function updateStatusLabel(value?: UpdateStatus['status']) {
  return ({ up_to_date: '已是最新版', update_available: '发现新版本', ahead: '当前版本高于 Latest', invalid_latest_version: '发行版标签无效', unknown_current_version: '当前版本无效', no_release: '暂无正式发行版', error: '检查失败' } as Record<string, string>)[value || ''] || '尚未检查'
}

async function checkUpdate(force = false) {
  updateChecking.value = true
  try {
    updateInfo.value = (await http.get<UpdateStatus>('/admin/update/status', { params: { force } })).data
  } catch (cause) {
    showError(cause, '版本检查失败')
  } finally {
    updateChecking.value = false
  }
}

function stopUpdatePolling() {
  if (updatePollTimer) window.clearInterval(updatePollTimer)
  updatePollTimer = undefined
}

async function pollUpdateTask() {
  if (!updateTask.value) return
  try {
    updateTask.value = (await http.get<UpdateTask>(`/admin/update/tasks/${updateTask.value.task_id}`)).data
    if (['succeeded', 'failed'].includes(updateTask.value.status)) {
      stopUpdatePolling()
      void checkUpdate(true)
    }
  } catch (cause) {
    stopUpdatePolling()
    showError(cause, '升级状态读取失败')
  }
}

async function runUpdate() {
  if (!auth.isRoot || !updateInfo.value?.update_available || !window.confirm(`确定升级到 ${updateInfo.value.tag_name} 吗？升级期间服务可能短暂中断。`)) return
  savingKey.value = 'update:run'
  try {
    updateTask.value = (await http.post<UpdateTask>('/admin/update/run')).data
    message.value = '升级任务已启动'
    stopUpdatePolling()
    updatePollTimer = window.setInterval(pollUpdateTask, 2000)
  } catch (cause) {
    showError(cause, '升级启动失败')
  } finally {
    savingKey.value = ''
  }
}

function canPunish(user: AdminUser) {
  if (user.uid === auth.user?.uid || user.role === 'root') return false
  return auth.isRoot || user.role === 'user'
}

function canManageUser(user: AdminUser) {
  if (user.uid === auth.user?.uid) return false
  return auth.isRoot || (auth.user?.role === 'admin' && user.role === 'user')
}

function activeStatusPunishment(user: AdminUser) {
  const type = user.status === 'banned' ? 'ban' : user.status === 'silenced' ? 'silence' : null
  if (!type) return null
  return punishments.value.find(item => (
    item.target_uid === user.uid
    && item.punishment_type === type
    && !item.is_revoked
    && (item.is_active ?? true)
  )) || null
}

function canRevokePunishment(item: AdminPunishment) {
  const user = users.value.find(candidate => candidate.uid === item.target_uid)
  return Boolean(auth.isAdmin && user && canManageUser(user) && !item.is_revoked && (item.is_active ?? true))
}

function canSettle(competition: Competition) {
  return !competition.settled_at && new Date(competition.end_time).getTime() <= Date.now()
}

async function fetchAllPages<T>(url: string): Promise<T[]> {
  const first = await http.get<PageResult<T>>(url, { params: { page: 1, page_size: 100 } })
  const items = [...(first.data.items || [])]
  const totalPages = first.data.total_pages || 1
  if (totalPages <= 1) return items
  const remaining = await Promise.all(
    Array.from({ length: totalPages - 1 }, (_, index) => (
      http.get<PageResult<T>>(url, { params: { page: index + 2, page_size: 100 } })
    )),
  )
  for (const response of remaining) items.push(...(response.data.items || []))
  return items
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [userItems, reportItems, punishmentItems, competitionItems, tagRes, groupRes, announcementItems] = await Promise.all([
      fetchAllPages<AdminUser>('/admin/users'),
      fetchAllPages<AdminReport>('/admin/reports'),
      fetchAllPages<AdminPunishment>('/admin/punishments'),
      fetchAllPages<Competition>('/competitions'),
      http.get<Tag[]>('/admin/tags'),
      http.get<PermissionGroup[]>('/admin/permission-groups'),
      fetchAllPages<Announcement>('/admin/announcements'),
    ])
    users.value = userItems
    reports.value = reportItems
    punishments.value = punishmentItems
    competitions.value = competitionItems
    tags.value = tagRes.data || []
    groups.value = (groupRes.data || []).map((group) => ({ ...group, permission_text: group.permissions.join(', ') }))
    announcements.value = announcementItems
    logs.value = auth.isRoot
      ? await fetchAllPages<OperationLog>('/admin/logs')
      : []
    for (const report of reports.value) {
      if (reportDrafts.value[report.id] === undefined) reportDrafts.value[report.id] = report.handle_result || ''
    }
  } catch (cause) {
    showError(cause, '管理数据加载失败')
  } finally {
    loading.value = false
  }
}

async function saveUser(user: AdminUser) {
  savingKey.value = `user:${user.uid}`
  try {
    await http.put(`/admin/users/${user.uid}`, { role: user.role, status: user.status })
    message.value = `用户 @${user.username} 已更新`
    await load()
  } catch (cause) {
    showError(cause, '用户更新失败')
  } finally {
    savingKey.value = ''
  }
}

async function deletePendingUser(user: AdminUser) {
  if (!auth.isRoot || user.status !== 'pending_email' || savingKey.value) return
  if (!window.confirm(`确定删除待验证账号 @${user.username} 吗？删除后 UID ${user.uid} 将被回收。`)) return
  savingKey.value = `delete-user:${user.uid}`
  error.value = ''
  try {
    const response = await http.delete<{ message: string }>(`/admin/users/${user.uid}/pending`)
    message.value = response.data.message
    await load()
  } catch (cause) {
    showError(cause, '待验证账号删除失败')
  } finally {
    savingKey.value = ''
  }
}

async function punishUser(user: AdminUser, punishmentType: 'ban' | 'silence') {
  const reason = (punishmentReasons.value[user.uid] || '').trim()
  if (reason.length < 2) {
    error.value = '请填写至少 2 个字符的处罚原因'
    return
  }
  savingKey.value = `punish:${user.uid}`
  try {
    await http.post('/admin/punish', { target_uid: user.uid, punishment_type: punishmentType, reason })
    punishmentReasons.value[user.uid] = ''
    message.value = `用户 @${user.username} 已${punishmentType === 'ban' ? '封禁' : '禁言'}`
    await load()
  } catch (cause) {
    showError(cause, '处罚执行失败')
  } finally {
    savingKey.value = ''
  }
}

async function revokePunishment(item: AdminPunishment, suppliedReason?: string) {
  if (!canRevokePunishment(item)) return
  const reason = (suppliedReason ?? revokeReasons.value[item.id] ?? '').trim()
  if (reason.length < 2) {
    error.value = '请填写至少 2 个字符的撤销原因'
    return
  }
  savingKey.value = `punishment:${item.id}`
  try {
    await http.post(`/admin/punish/${item.id}/revoke`, { revoke_reason: reason })
    revokeReasons.value[item.id] = ''
    userRevokeReasons.value[item.target_uid] = ''
    message.value = `处罚 #${item.id} 已撤销`
    await load()
  } catch (cause) {
    showError(cause, '处罚撤销失败')
  } finally {
    savingKey.value = ''
  }
}

async function revokeUserStatus(user: AdminUser) {
  const item = activeStatusPunishment(user)
  if (!item) {
    error.value = '没有找到对应的生效处罚，请刷新页面'
    return
  }
  await revokePunishment(item, userRevokeReasons.value[user.uid])
}

function groupContains(group: PermissionGroup, user: AdminUser) {
  return user.group_ids.includes(group.id)
}

async function toggleGroup(user: AdminUser, group: PermissionGroup, checked: boolean) {
  if (!auth.isRoot) return
  const key = `group:${group.id}:${user.uid}`
  savingKey.value = key
  try {
    const path = `/admin/permission-groups/${group.id}/members/${user.uid}`
    if (checked) await http.put(path)
    else await http.delete(path)
    user.group_ids = checked ? [...new Set([...user.group_ids, group.id])] : user.group_ids.filter((id) => id !== group.id)
    group.member_uids = checked ? [...new Set([...group.member_uids, user.uid])] : group.member_uids.filter((uid) => uid !== user.uid)
    group.member_count = group.member_uids.length
  } catch (cause) {
    showError(cause, '用户组成员更新失败')
  } finally {
    savingKey.value = ''
  }
}

function toggleGroupFromEvent(user: AdminUser, group: PermissionGroup, event: Event) {
  void toggleGroup(user, group, (event.target as HTMLInputElement).checked)
}

async function decideReport(report: AdminReport, accepted: boolean) {
  const result = (reportDrafts.value[report.id] || '').trim()
  if (result.length < 2) {
    error.value = '请填写至少 2 个字符的处理结果'
    return
  }
  savingKey.value = `report:${report.id}`
  try {
    await http.post(`/admin/reports/${report.id}/decision`, { accepted, result })
    message.value = `举报 #${report.id} 已${accepted ? '采纳' : '驳回'}`
    await load()
  } catch (cause) {
    showError(cause, '举报处理失败')
  } finally {
    savingKey.value = ''
  }
}

async function createGroup() {
  if (!auth.isRoot || !groupForm.value.name.trim()) return
  savingKey.value = 'group:create'
  try {
    await http.post('/admin/permission-groups', {
      name: groupForm.value.name,
      description: groupForm.value.description,
      permissions: splitPermissions(groupForm.value.permissions),
    })
    groupForm.value = { name: '', description: '', permissions: '' }
    message.value = '用户组已创建'
    await load()
  } catch (cause) {
    showError(cause, '用户组创建失败')
  } finally {
    savingKey.value = ''
  }
}

async function saveGroup(group: PermissionGroup) {
  if (!auth.isRoot) return
  savingKey.value = `group:${group.id}`
  try {
    await http.put(`/admin/permission-groups/${group.id}`, {
      name: group.name,
      description: group.description || '',
      permissions: splitPermissions(group.permission_text),
    })
    message.value = `用户组“${group.name}”已更新`
    await load()
  } catch (cause) {
    showError(cause, '用户组更新失败')
  } finally {
    savingKey.value = ''
  }
}

async function deleteGroup(group: PermissionGroup) {
  if (!auth.isRoot || !window.confirm(`确定删除用户组“${group.name}”吗？`)) return
  savingKey.value = `group:${group.id}`
  try {
    await http.delete(`/admin/permission-groups/${group.id}`)
    message.value = '用户组已删除'
    await load()
  } catch (cause) {
    showError(cause, '用户组删除失败')
  } finally {
    savingKey.value = ''
  }
}

async function createTag() {
  if (!tagForm.value.name.trim()) return
  savingKey.value = 'tag:create'
  try {
    await http.post('/admin/tags', tagForm.value)
    tagForm.value = { name: '', description: '', kind: 'custom' }
    message.value = '标签已创建'
    await load()
  } catch (cause) {
    showError(cause, '标签创建失败')
  } finally {
    savingKey.value = ''
  }
}

async function saveTag(tag: Tag) {
  savingKey.value = `tag:${tag.id}`
  try {
    await http.put(`/admin/tags/${tag.id}`, {
      name: tag.name,
      description: tag.description || '',
      status: tag.status,
      sort_order: tag.sort_order,
    })
    message.value = `标签“${tag.name}”已更新`
    await load()
  } catch (cause) {
    showError(cause, '标签更新失败')
  } finally {
    savingKey.value = ''
  }
}

async function mergeTag(tag: Tag) {
  const targetTagId = mergeTargets.value[tag.id]
  if (!targetTagId) return
  if (!window.confirm(`确定将“${tag.name}”合并到所选标签吗？`)) return
  savingKey.value = `tag:${tag.id}`
  try {
    await http.post(`/admin/tags/${tag.id}/merge`, { target_tag_id: targetTagId })
    message.value = `标签“${tag.name}”已合并`
    await load()
  } catch (cause) {
    showError(cause, '标签合并失败')
  } finally {
    savingKey.value = ''
  }
}

async function settleCompetition(item: Competition) {
  savingKey.value = `competition:${item.id}`
  try {
    await http.post(`/competitions/${item.id}/settle`)
    message.value = `比赛“${item.name}”已结算`
    await load()
  } catch (cause) {
    showError(cause, '比赛结算失败')
  } finally {
    savingKey.value = ''
  }
}

async function deleteCompetition(item: Competition) {
  if (!window.confirm(`确定删除比赛“${item.name}”及其参赛记录吗？`)) return
  savingKey.value = `competition:${item.id}`
  try {
    await http.delete(`/competitions/${item.id}`)
    message.value = '比赛已删除'
    await load()
  } catch (cause) {
    showError(cause, '比赛删除失败')
  } finally {
    savingKey.value = ''
  }
}

async function createAnnouncement() {
  if (!announcementForm.value.title.trim() || !announcementForm.value.content.trim()) return
  savingKey.value = 'announcement:create'
  try {
    await http.post('/admin/announcements', announcementForm.value)
    announcementForm.value = { title: '', content: '', priority: 0 }
    message.value = '公告草稿已保存'
    await load()
  } catch (cause) {
    showError(cause, '公告保存失败')
  } finally {
    savingKey.value = ''
  }
}

async function saveAnnouncement(item: Announcement) {
  savingKey.value = `announcement:${item.id}`
  try {
    await http.put(`/admin/announcements/${item.id}`, { title: item.title, content: item.content, priority: item.priority })
    message.value = `公告“${item.title}”已更新`
    await load()
  } catch (cause) {
    showError(cause, '公告更新失败')
  } finally {
    savingKey.value = ''
  }
}

async function publish(item: Announcement) {
  savingKey.value = `announcement:${item.id}`
  try {
    await http.post(`/admin/announcements/${item.id}/publish`)
    message.value = '公告已发布'
    await load()
  } catch (cause) {
    showError(cause, '公告发布失败')
  } finally {
    savingKey.value = ''
  }
}

async function withdraw(item: Announcement) {
  savingKey.value = `announcement:${item.id}`
  try {
    await http.post(`/admin/announcements/${item.id}/withdraw`)
    message.value = '公告已撤回为草稿'
    await load()
  } catch (cause) {
    showError(cause, '公告撤回失败')
  } finally {
    savingKey.value = ''
  }
}

async function deleteAnnouncement(item: Announcement) {
  if (!window.confirm(`确定删除公告“${item.title}”吗？`)) return
  savingKey.value = `announcement:${item.id}`
  try {
    await http.delete(`/admin/announcements/${item.id}`)
    message.value = '公告已删除'
    await load()
  } catch (cause) {
    showError(cause, '公告删除失败')
  } finally {
    savingKey.value = ''
  }
}

onMounted(() => { void load(); void checkUpdate() })
onUnmounted(stopUpdatePolling)
</script>

<template>
  <main class="page-shell">
    <div class="page-container">
      <div class="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h1 class="section-title text-3xl">管理后台</h1>
        <div class="flex flex-wrap gap-2">
          <router-link v-if="auth.isRoot" class="btn-secondary" :to="{ path: '/admin/broadcasts', query: { tab: 'system' } }">系统消息</router-link>
          <router-link v-if="auth.isRoot" class="btn-primary" :to="{ path: '/admin/broadcasts', query: { tab: 'email' } }">邮件群发</router-link>
          <button class="btn-secondary inline-flex items-center gap-1.5" type="button" title="刷新管理数据" @click="load"><ArrowPathIcon class="h-4 w-4" aria-hidden="true" />刷新</button>
        </div>
      </div>

      <div v-if="loading" class="surface-card p-12 text-center text-slate-500">正在加载后台数据…</div>
      <div v-else>
        <div class="mb-5 flex flex-wrap gap-2 border-b border-slate-200 pb-3 dark:border-neutral-800" role="tablist" aria-label="管理模块">
          <button v-for="tab in tabs" :key="tab.key" class="rounded-md px-3 py-2 text-sm font-medium" :class="activeTab === tab.key ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-neutral-900'" type="button" role="tab" :aria-selected="activeTab === tab.key" @click="activeTab = tab.key">
            {{ tab.label }}<span v-if="tab.count" class="ml-1.5 text-xs opacity-80">{{ tab.count }}</span>
          </button>
        </div>

        <p v-if="error" class="mb-4 break-words text-sm text-red-600">{{ error }}</p>
        <p v-if="message" class="mb-4 break-words text-sm text-emerald-600">{{ message }}</p>

        <section v-if="activeTab === 'reports'" class="surface-card p-5">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <h2 class="section-title">举报处理</h2>
            <select v-model="reportFilter" class="form-control w-auto" aria-label="举报状态">
              <option value="pending">待处理</option>
              <option value="all">全部</option>
              <option value="processed">已采纳</option>
              <option value="rejected">已驳回</option>
            </select>
          </div>
          <div v-if="!visibleReports.length" class="py-10 text-center text-sm text-slate-500">暂无举报记录。</div>
          <div v-else class="mt-4 divide-y divide-slate-200 border-y border-slate-200 dark:divide-neutral-800 dark:border-neutral-800">
            <article v-for="report in visibleReports" :key="report.id" class="py-4">
              <div class="flex flex-wrap items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="font-semibold">
                    举报 #{{ report.id }} ·
                    <router-link v-if="report.target_url && report.target_exists" class="text-blue-600 hover:underline" :to="report.target_url">{{ targetLabel(report.target_type) }} #{{ report.target_id }}</router-link>
                    <span v-else>{{ targetLabel(report.target_type) }} #{{ report.target_id }}（已删除）</span>
                  </p>
                  <p class="mt-1 text-xs text-slate-500">举报人 UID {{ report.reporter_uid }} · {{ formatDate(report.created_at) }}</p>
                </div>
                <span class="shrink-0 text-xs text-slate-500">{{ report.status }}</span>
              </div>
              <p class="mt-3 whitespace-pre-wrap break-words text-sm text-slate-700 dark:text-slate-200"><LinkifiedText :text="report.reason" /></p>
              <p v-if="report.target_preview" class="mt-2 whitespace-pre-wrap break-words border-l-2 border-slate-300 pl-3 text-sm text-slate-500 dark:border-neutral-700">目标内容：<LinkifiedText :text="report.target_preview" /></p>
              <p v-if="report.handle_result" class="mt-2 whitespace-pre-wrap break-words text-sm text-slate-500">处理结果：<LinkifiedText :text="report.handle_result" /></p>
              <div v-if="report.status === 'pending'" class="mt-3 flex flex-col gap-2 sm:flex-row">
                <input v-model="reportDrafts[report.id]" class="form-control min-w-0 flex-1" maxlength="2000" placeholder="填写处理结果">
                <button class="btn-primary" type="button" :disabled="savingKey === `report:${report.id}`" @click="decideReport(report, true)">采纳</button>
                <button class="btn-secondary" type="button" :disabled="savingKey === `report:${report.id}`" @click="decideReport(report, false)">驳回</button>
              </div>
            </article>
          </div>
        </section>

        <section v-else-if="activeTab === 'users'" class="surface-card p-5">
          <div class="flex flex-wrap items-center justify-between gap-3">
            <h2 class="section-title">用户管理</h2>
            <span class="text-sm text-slate-500">共 {{ users.length }} 个用户</span>
          </div>
          <div v-if="!users.length" class="py-10 text-center text-sm text-slate-500">暂无用户。</div>
          <div v-else class="mt-4 overflow-x-auto">
            <table class="w-full min-w-[1280px] text-left text-sm">
              <thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-2 py-2">用户</th><th class="px-2 py-2">邮箱</th><th class="px-2 py-2">角色</th><th class="px-2 py-2">状态</th><th class="px-2 py-2">用户组</th><th class="px-2 py-2">账号设置</th><th class="px-2 py-2">处罚</th></tr></thead>
              <tbody>
                <tr v-for="user in users" :key="user.uid" class="border-b border-slate-100 align-top dark:border-neutral-800">
                  <td class="px-2 py-3"><strong class="block">{{ user.nickname }}</strong><small class="text-slate-400">@{{ user.username }} · UID {{ user.uid }}</small></td>
                  <td class="max-w-56 break-all px-2 py-3 text-slate-600 dark:text-slate-300">{{ user.email }}</td>
                  <td class="px-2 py-3"><select v-model="user.role" class="form-control w-28" :disabled="!auth.isRoot || user.uid === auth.user?.uid"><option value="user">user</option><option value="admin">admin</option><option value="root">root</option></select></td>
                  <td class="px-2 py-3"><select v-model="user.status" class="form-control w-36" :disabled="!auth.isRoot || user.uid === auth.user?.uid || user.status === 'banned' || user.status === 'silenced'"><option v-if="user.status === 'banned'" value="banned">banned</option><option v-if="user.status === 'silenced'" value="silenced">silenced</option><option value="active">active</option><option value="pending_email">pending_email</option></select></td>
                  <td class="min-w-52 px-2 py-3"><div class="space-y-1"><label v-for="group in groups" :key="group.id" class="flex items-center gap-2 text-xs"><input type="checkbox" :checked="groupContains(group, user)" :disabled="!auth.isRoot || savingKey === `group:${group.id}:${user.uid}`" @change="toggleGroupFromEvent(user, group, $event)"><span>{{ group.name }}</span></label><span v-if="!groups.length" class="text-xs text-slate-400">暂无用户组</span></div></td>
                  <td class="px-2 py-3">
                    <div v-if="auth.isRoot && user.uid !== auth.user?.uid" class="flex flex-wrap gap-2">
                      <button class="btn-secondary whitespace-nowrap text-xs" type="button" :disabled="savingKey === `user:${user.uid}`" @click="saveUser(user)">保存用户</button>
                      <button v-if="user.status === 'pending_email'" class="inline-flex min-h-9 items-center gap-1 whitespace-nowrap rounded-md bg-red-600 px-3 py-2 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50" type="button" :disabled="savingKey === `delete-user:${user.uid}`" @click="deletePendingUser(user)"><TrashIcon class="h-4 w-4" aria-hidden="true" />{{ savingKey === `delete-user:${user.uid}` ? '删除中…' : '删除待验证账号' }}</button>
                    </div>
                    <span v-else-if="user.uid === auth.user?.uid" class="text-xs text-slate-400">当前账号</span><span v-else class="text-xs text-slate-400">ROOT 管理</span>
                  </td>
                  <td class="min-w-72 px-2 py-3">
                    <div v-if="activeStatusPunishment(user) && canManageUser(user)" class="flex items-center gap-2">
                      <input v-model="userRevokeReasons[user.uid]" class="form-control min-w-36" maxlength="2000" placeholder="解除原因">
                      <button class="btn-secondary whitespace-nowrap text-xs" type="button" :disabled="savingKey === `punishment:${activeStatusPunishment(user)?.id}`" @click="revokeUserStatus(user)">{{ user.status === 'banned' ? '解除封禁' : '解除禁言' }}</button>
                    </div>
                    <div v-else-if="canPunish(user)" class="flex items-center gap-2">
                      <input v-model="punishmentReasons[user.uid]" class="form-control min-w-36" maxlength="2000" placeholder="处罚原因">
                      <button class="btn-secondary inline-flex items-center gap-1 whitespace-nowrap text-xs" type="button" :disabled="savingKey === `punish:${user.uid}`" @click="punishUser(user, 'silence')"><ShieldExclamationIcon class="h-4 w-4" aria-hidden="true" />禁言</button>
                      <button class="inline-flex min-h-9 items-center gap-1 whitespace-nowrap rounded-md bg-red-600 px-3 py-2 text-xs font-medium text-white hover:bg-red-700 disabled:opacity-50" type="button" :disabled="savingKey === `punish:${user.uid}`" @click="punishUser(user, 'ban')"><ShieldExclamationIcon class="h-4 w-4" aria-hidden="true" />封禁</button>
                    </div>
                    <span v-else class="text-xs text-slate-400">不可处罚</span>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section v-else-if="activeTab === 'punishments'" class="surface-card p-5">
          <h2 class="section-title">处罚记录</h2>
          <div v-if="!punishments.length" class="py-10 text-center text-sm text-slate-500">暂无处罚记录。</div>
          <div v-else class="mt-4 overflow-x-auto">
            <table class="w-full min-w-[960px] text-left text-sm">
              <thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-2 py-2">记录</th><th class="px-2 py-2">目标</th><th class="px-2 py-2">类型</th><th class="px-2 py-2">原因</th><th class="px-2 py-2">时间</th><th class="px-2 py-2">状态 / 操作</th></tr></thead>
              <tbody><tr v-for="item in punishments" :key="item.id" class="border-b border-slate-100 align-top dark:border-neutral-800"><td class="px-2 py-3">#{{ item.id }}<small class="mt-1 block text-slate-400">操作人 UID {{ item.operator_uid }}</small></td><td class="px-2 py-3"><router-link class="text-blue-600 hover:underline" :to="`/profile/${item.target_uid}`">UID {{ item.target_uid }}</router-link></td><td class="px-2 py-3 font-medium">{{ punishmentLabel(item.punishment_type) }}</td><td class="max-w-80 break-words px-2 py-3"><LinkifiedText :text="item.reason" /></td><td class="px-2 py-3 text-xs text-slate-500">{{ formatDate(item.start_time) }}<span v-if="item.end_time" class="block">至 {{ formatDate(item.end_time) }}</span></td><td class="min-w-72 px-2 py-3"><span v-if="item.is_revoked" class="text-emerald-600">已撤销<span v-if="item.revoke_reason" class="block text-xs text-slate-500"><LinkifiedText :text="item.revoke_reason" /></span></span><span v-else-if="item.is_active === false" class="text-slate-500">已到期</span><div v-else-if="canRevokePunishment(item)" class="flex gap-2"><input v-model="revokeReasons[item.id]" class="form-control min-w-40" maxlength="2000" placeholder="撤销原因"><button class="btn-secondary whitespace-nowrap text-xs" type="button" :disabled="savingKey === `punishment:${item.id}`" @click="revokePunishment(item)">撤销</button></div><span v-else class="text-red-600">生效中</span></td></tr></tbody>
            </table>
          </div>
        </section>

        <section v-else-if="activeTab === 'competitions'" class="surface-card p-5">
          <div class="flex flex-wrap items-center justify-between gap-3"><h2 class="section-title">比赛管理</h2><router-link class="btn-primary" to="/competitions/create">发布比赛</router-link></div>
          <div v-if="!competitions.length" class="py-10 text-center text-sm text-slate-500">暂无比赛。</div>
          <div v-else class="mt-4 overflow-x-auto"><table class="w-full min-w-[840px] text-left text-sm"><thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-2 py-2">比赛</th><th class="px-2 py-2">周期</th><th class="px-2 py-2">状态</th><th class="px-2 py-2">标签</th><th class="px-2 py-2">操作</th></tr></thead><tbody><tr v-for="item in competitions" :key="item.id" class="border-b border-slate-100 dark:border-neutral-800"><td class="px-2 py-3"><router-link class="font-semibold text-blue-600 hover:underline" :to="`/competitions/${item.id}`">{{ item.name }}</router-link><small class="mt-1 block text-slate-400">#{{ item.id }} · 创建人 UID {{ item.creator_uid }}</small></td><td class="px-2 py-3 text-xs text-slate-500">{{ formatDate(item.start_time) }}<span class="block">{{ formatDate(item.end_time) }}</span></td><td class="px-2 py-3">{{ item.settled_at ? '已结算' : item.status }}</td><td class="px-2 py-3">{{ item.required_tag_ids.length }} 个</td><td class="px-2 py-3"><div class="flex items-center gap-3"><button v-if="canSettle(item)" class="btn-secondary text-xs" type="button" :disabled="savingKey === `competition:${item.id}`" @click="settleCompetition(item)">结算</button><button class="inline-flex items-center gap-1 text-xs font-medium text-red-600 hover:text-red-700" type="button" :disabled="savingKey === `competition:${item.id}`" @click="deleteCompetition(item)"><TrashIcon class="h-4 w-4" aria-hidden="true" />删除</button></div></td></tr></tbody></table></div>
        </section>

        <section v-else-if="activeTab === 'tags'" class="surface-card p-5">
          <h2 class="section-title">标签管理</h2>
          <form class="mt-4 grid gap-3 border-b border-slate-200 pb-5 dark:border-neutral-800 sm:grid-cols-[minmax(10rem,16rem)_minmax(12rem,1fr)_8rem_auto]" @submit.prevent="createTag"><input v-model="tagForm.name" class="form-control" required maxlength="30" placeholder="标签名称"><input v-model="tagForm.description" class="form-control" maxlength="500" placeholder="标签描述"><select v-model="tagForm.kind" class="form-control"><option value="custom">自定义</option><option value="system">系统</option></select><button class="btn-primary" type="submit" :disabled="savingKey === 'tag:create'">创建标签</button></form>
          <div v-if="!tags.length" class="py-10 text-center text-sm text-slate-500">暂无标签。</div>
          <div v-else class="mt-4 overflow-x-auto"><table class="w-full min-w-[1120px] text-left text-sm"><thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-2 py-2">名称</th><th class="px-2 py-2">描述</th><th class="px-2 py-2">状态</th><th class="px-2 py-2">排序</th><th class="px-2 py-2">使用</th><th class="px-2 py-2">合并到</th><th class="px-2 py-2">操作</th></tr></thead><tbody><tr v-for="tag in tags" :key="tag.id" class="border-b border-slate-100 align-top dark:border-neutral-800"><td class="px-2 py-3"><input v-model="tag.name" class="form-control min-w-32"><small class="mt-1 block text-slate-400">{{ tag.slug }} · {{ tag.kind }}</small></td><td class="px-2 py-3"><input v-model="tag.description" class="form-control min-w-52" maxlength="500"></td><td class="px-2 py-3"><select v-model="tag.status" class="form-control w-28"><option value="active">启用</option><option value="disabled">停用</option></select></td><td class="px-2 py-3"><input v-model.number="tag.sort_order" class="form-control w-24" type="number"></td><td class="px-2 py-3">{{ tag.usage_count }}</td><td class="px-2 py-3"><select v-model="mergeTargets[tag.id]" class="form-control min-w-40"><option :value="null">选择目标</option><option v-for="target in tags.filter((item) => item.id !== tag.id && item.status === 'active')" :key="target.id" :value="target.id">{{ target.name }}</option></select></td><td class="px-2 py-3"><div class="flex gap-3"><button class="btn-secondary text-xs" type="button" :disabled="savingKey === `tag:${tag.id}`" @click="saveTag(tag)">保存</button><button class="text-xs font-medium text-red-600" type="button" :disabled="!mergeTargets[tag.id] || savingKey === `tag:${tag.id}`" @click="mergeTag(tag)">合并</button></div></td></tr></tbody></table></div>
        </section>

        <section v-else-if="activeTab === 'groups'" class="surface-card p-5">
          <h2 class="section-title">用户组管理</h2>
          <form v-if="auth.isRoot" class="mt-4 grid gap-3 border-b border-slate-200 pb-5 dark:border-neutral-800 sm:grid-cols-2" @submit.prevent="createGroup">
            <input v-model="groupForm.name" class="form-control" required maxlength="100" placeholder="用户组名称">
            <input v-model="groupForm.description" class="form-control" maxlength="500" placeholder="描述">
            <input v-model="groupForm.permissions" class="form-control sm:col-span-2" placeholder="权限标识，用逗号分隔">
            <button class="btn-primary w-fit" type="submit" :disabled="savingKey === 'group:create' || !groupForm.name.trim()">创建用户组</button>
          </form>
          <div v-if="!groups.length" class="py-10 text-center text-sm text-slate-500">暂无用户组。</div>
          <div v-else class="divide-y divide-slate-200 dark:divide-neutral-800">
            <div v-for="group in groups" :key="group.id" class="grid gap-3 py-5 lg:grid-cols-[minmax(10rem,16rem)_minmax(12rem,1fr)_auto] lg:items-end">
              <div><label class="mb-1 block text-xs text-slate-500">名称</label><input v-model="group.name" class="form-control" :disabled="!auth.isRoot"></div>
              <div><label class="mb-1 block text-xs text-slate-500">描述 / 权限</label><input v-model="group.description" class="form-control" :disabled="!auth.isRoot" placeholder="描述"><input v-model="group.permission_text" class="form-control mt-2" :disabled="!auth.isRoot" placeholder="权限标识，用逗号分隔"></div>
              <div class="flex items-center gap-2"><span class="mr-2 text-xs text-slate-500">{{ group.member_count }} 名成员</span><button v-if="auth.isRoot" class="btn-secondary text-xs" type="button" :disabled="savingKey === `group:${group.id}`" @click="saveGroup(group)">保存</button><button v-if="auth.isRoot" class="inline-flex items-center gap-1 text-xs text-red-600" type="button" :disabled="savingKey === `group:${group.id}`" @click="deleteGroup(group)"><TrashIcon class="h-4 w-4" aria-hidden="true" />删除</button></div>
            </div>
          </div>
        </section>

        <section v-else-if="activeTab === 'announcements'" class="grid gap-6 lg:grid-cols-[minmax(18rem,24rem)_1fr]">
          <div class="surface-card p-5">
            <h2 class="section-title">新建公告</h2>
            <form class="mt-4 space-y-4" @submit.prevent="createAnnouncement">
              <input v-model="announcementForm.title" class="form-control" required maxlength="200" placeholder="公告标题">
              <textarea v-model="announcementForm.content" class="form-control min-h-32" required maxlength="5000" placeholder="公告内容（纯文本）"></textarea>
              <input v-model.number="announcementForm.priority" class="form-control" type="number" min="0" max="100" placeholder="优先级">
              <button class="btn-primary" :disabled="savingKey === 'announcement:create' || !announcementForm.title.trim() || !announcementForm.content.trim()">保存草稿</button>
            </form>
          </div>
          <div class="surface-card p-5">
            <h2 class="section-title">公告列表</h2>
            <div v-if="!announcements.length" class="py-8 text-center text-sm text-slate-500">暂无公告。</div>
            <div v-else class="mt-4 divide-y divide-slate-200 border-y border-slate-200 dark:divide-neutral-800 dark:border-neutral-800"><div v-for="item in announcements" :key="item.id" class="py-4"><div class="grid gap-3 sm:grid-cols-[1fr_7rem]"><input v-model="item.title" class="form-control font-semibold" maxlength="200"><input v-model.number="item.priority" class="form-control" type="number" min="0" max="100" aria-label="优先级"></div><textarea v-model="item.content" class="form-control mt-3 min-h-24" maxlength="10000"></textarea><div class="mt-3 flex flex-wrap items-center gap-3"><span class="mr-auto text-xs text-slate-500">{{ item.status }} · {{ formatDate(item.updated_at) }}</span><button class="btn-secondary text-xs" type="button" :disabled="savingKey === `announcement:${item.id}`" @click="saveAnnouncement(item)">保存</button><button v-if="item.status === 'draft'" class="text-sm font-medium text-blue-600" type="button" :disabled="savingKey === `announcement:${item.id}`" @click="publish(item)">发布</button><button v-else class="text-sm font-medium text-amber-700" type="button" :disabled="savingKey === `announcement:${item.id}`" @click="withdraw(item)">撤回</button><button class="inline-flex items-center gap-1 text-sm font-medium text-red-600" type="button" :disabled="savingKey === `announcement:${item.id}`" @click="deleteAnnouncement(item)"><TrashIcon class="h-4 w-4" aria-hidden="true" />删除</button></div></div></div>
          </div>
        </section>

        <section v-else-if="activeTab === 'updates'" class="surface-card p-5">
          <div class="flex flex-wrap items-start justify-between gap-3">
            <div><h2 class="section-title">系统更新</h2><p class="mt-1 text-sm text-slate-500">数据源：GitHub Latest Release</p></div>
            <button class="btn-secondary inline-flex items-center gap-1.5" type="button" :disabled="updateChecking" @click="checkUpdate(true)"><ArrowPathIcon class="h-4 w-4" :class="updateChecking ? 'animate-spin' : ''" aria-hidden="true" />{{ updateChecking ? '检查中…' : '重新检查' }}</button>
          </div>
          <div v-if="updateInfo" class="mt-6 grid gap-5 border-y border-slate-200 py-5 dark:border-neutral-800 sm:grid-cols-2 lg:grid-cols-4">
            <div><p class="text-xs text-slate-500">当前版本</p><p class="mt-1 text-lg font-semibold">v{{ updateInfo.current_version }}</p></div>
            <div><p class="text-xs text-slate-500">Latest</p><p class="mt-1 text-lg font-semibold">{{ updateInfo.latest_version ? `v${updateInfo.latest_version}` : updateInfo.status === 'no_release' ? '暂无正式发行版' : '不可用' }}</p></div>
            <div><p class="text-xs text-slate-500">状态</p><p class="mt-1 font-medium" :class="updateInfo.update_available ? 'text-amber-600' : updateInfo.status === 'error' ? 'text-red-600' : 'text-emerald-600'">{{ updateStatusLabel(updateInfo.status) }}</p></div>
            <div><p class="text-xs text-slate-500">检查时间</p><p class="mt-1 text-sm">{{ formatDate(updateInfo.checked_at) }}</p></div>
          </div>
          <p v-if="updateInfo?.error" class="mt-4 text-sm text-red-600">{{ updateInfo.error }}</p>
          <div v-if="updateInfo?.html_url" class="mt-4"><a class="text-sm font-medium text-blue-600 hover:underline" :href="updateInfo.html_url" target="_blank" rel="noopener noreferrer">查看 {{ updateInfo.release_name || updateInfo.tag_name }}</a></div>
          <div class="mt-6 flex flex-wrap items-center gap-3">
            <button v-if="auth.isRoot" class="btn-primary inline-flex items-center gap-1.5" type="button" :disabled="!updateInfo?.update_available || savingKey === 'update:run' || ['queued', 'running'].includes(updateTask?.status || '')" @click="runUpdate"><ArrowDownTrayIcon class="h-4 w-4" aria-hidden="true" />{{ savingKey === 'update:run' ? '启动中…' : '升级到 Latest' }}</button>
            <span v-else class="text-sm text-slate-500">只有 ROOT 可以执行在线升级。</span>
          </div>
          <div v-if="updateTask" class="mt-6 border-t border-slate-200 pt-5 text-sm dark:border-neutral-800">
            <p><strong>任务 {{ updateTask.task_id.slice(0, 8) }}</strong> · {{ updateTask.status }}</p>
            <p class="mt-2 text-slate-500">目标 {{ updateTask.tag_name }}<span v-if="updateTask.log_path"> · 日志 {{ updateTask.log_path }}</span></p>
            <p v-if="updateTask.error" class="mt-2 text-red-600">{{ updateTask.error }}</p>
          </div>
        </section>

        <section v-else-if="activeTab === 'logs' && auth.isRoot" class="surface-card p-5">
          <h2 class="section-title">操作日志</h2>
          <div v-if="!logs.length" class="py-10 text-center text-sm text-slate-500">暂无操作日志。</div>
          <div v-else class="mt-4 overflow-x-auto"><table class="w-full min-w-[900px] text-left text-sm"><thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-2 py-2">时间</th><th class="px-2 py-2">操作人</th><th class="px-2 py-2">动作</th><th class="px-2 py-2">目标</th><th class="px-2 py-2">详情</th></tr></thead><tbody><tr v-for="log in logs" :key="log.id" class="border-b border-slate-100 align-top dark:border-neutral-800"><td class="whitespace-nowrap px-2 py-3 text-xs text-slate-500">{{ formatDate(log.created_at) }}</td><td class="px-2 py-3">{{ log.operator_username || `UID ${log.operator_uid}` }}<small class="block text-slate-400">{{ log.operator_roles.join(', ') }}</small></td><td class="px-2 py-3 font-medium">{{ log.action_type }}</td><td class="px-2 py-3">{{ log.target_type }}<span v-if="log.target_id"> #{{ log.target_id }}</span></td><td class="px-2 py-3"><pre class="max-w-xl whitespace-pre-wrap break-words text-xs text-slate-600 dark:text-slate-300">{{ formatDetails(log.details) }}</pre></td></tr></tbody></table></div>
        </section>
      </div>
    </div>
  </main>
</template>
