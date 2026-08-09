<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import http from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import type { Announcement, PageResult } from '@/types'

type AdminTab = 'reports' | 'users' | 'groups' | 'announcements'
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
  reason: string
  status: 'pending' | 'processed' | 'rejected'
  handler_uid?: number | null
  handle_result?: string | null
  handled_at?: string | null
  created_at: string
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

const auth = useAuthStore()
const activeTab = ref<AdminTab>('reports')
const users = ref<AdminUser[]>([])
const reports = ref<AdminReport[]>([])
const groups = ref<PermissionGroup[]>([])
const announcements = ref<Announcement[]>([])
const reportFilter = ref<'all' | 'pending' | 'processed' | 'rejected'>('pending')
const reportDrafts = ref<Record<number, string>>({})
const loading = ref(true)
const error = ref('')
const message = ref('')
const savingKey = ref('')
const groupForm = ref({ name: '', description: '', permissions: '' })
const tabs: Array<{ key: AdminTab; label: string; count: () => number }> = [
  { key: 'reports', label: '举报', count: () => pendingReportCount.value },
  { key: 'users', label: '用户', count: () => users.value.length },
  { key: 'groups', label: '用户组', count: () => groups.value.length },
  { key: 'announcements', label: '公告', count: () => announcements.value.length },
]

const visibleReports = computed(() => (
  reportFilter.value === 'all'
    ? reports.value
    : reports.value.filter((report) => report.status === reportFilter.value)
))

const pendingReportCount = computed(() => reports.value.filter((report) => report.status === 'pending').length)

function showError(reason: unknown, fallback: string) {
  error.value = extractApiError(reason, fallback)
}

function splitPermissions(value: string) {
  return value.split(',').map((item) => item.trim()).filter(Boolean)
}

function formatDate(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false })
}

function targetLabel(targetType: string) {
  return ({ post: '帖子', comment: '评论', soup: '海龟汤', message: '私信', user: '用户' } as Record<string, string>)[targetType] || targetType
}

async function load() {
  loading.value = true
  error.value = ''
  try {
    const [userRes, reportRes, groupRes, announcementRes] = await Promise.all([
      http.get<PageResult<AdminUser>>('/admin/users', { params: { page: 1, page_size: 100 } }),
      http.get<PageResult<AdminReport>>('/admin/reports', { params: { page: 1, page_size: 100 } }),
      http.get<PermissionGroup[]>('/admin/permission-groups'),
      http.get<PageResult<Announcement>>('/admin/announcements', { params: { page: 1, page_size: 50 } }),
    ])
    users.value = userRes.data.items || []
    reports.value = reportRes.data.items || []
    groups.value = (groupRes.data || []).map((group) => ({
      ...group,
      permission_text: group.permissions.join(', '),
    }))
    announcements.value = announcementRes.data.items || []
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
  message.value = ''
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
    if (checked && !user.group_ids.includes(group.id)) user.group_ids.push(group.id)
    if (!checked) user.group_ids = user.group_ids.filter((id) => id !== group.id)
    group.member_uids = checked
      ? [...new Set([...group.member_uids, user.uid])]
      : group.member_uids.filter((uid) => uid !== user.uid)
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
  error.value = ''
  try {
    const response = await http.post<AdminReport>(`/admin/reports/${report.id}/decision`, {
      accepted,
      result,
    })
    const index = reports.value.findIndex((item) => item.id === report.id)
    if (index >= 0) reports.value[index] = response.data
    message.value = `举报 #${report.id} 已${accepted ? '采纳' : '驳回'}`
  } catch (cause) {
    showError(cause, '举报处理失败')
  } finally {
    savingKey.value = ''
  }
}

async function createGroup() {
  if (!auth.isRoot || !groupForm.value.name.trim()) return
  savingKey.value = 'group:create'
  error.value = ''
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
  error.value = ''
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
  error.value = ''
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

async function createAnnouncement() {
  if (!announcementForm.value.title.trim() || !announcementForm.value.content.trim()) return
  savingKey.value = 'announcement:create'
  error.value = ''
  try {
    await http.post('/admin/announcements', { ...announcementForm.value, status: 'draft' })
    announcementForm.value = { title: '', content: '', priority: 0 }
    message.value = '公告草稿已保存'
    await load()
  } catch (cause) {
    showError(cause, '公告保存失败')
  } finally {
    savingKey.value = ''
  }
}

async function publish(item: Announcement) {
  savingKey.value = `announcement:${item.id}`
  try {
    await http.post(`/admin/announcements/${item.id}/publish`)
    await load()
  } catch (cause) {
    showError(cause, '公告发布失败')
  } finally {
    savingKey.value = ''
  }
}

const announcementForm = ref({ title: '', content: '', priority: 0 })
onMounted(load)
</script>

<template>
  <main class="page-shell">
    <div class="page-container">
      <div class="mb-6 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 class="section-title text-3xl">管理后台</h1>
          <p class="mt-2 text-slate-500">处理举报、维护用户与用户组、发布社区公告。</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <router-link v-if="auth.isRoot" class="btn-secondary" :to="{ path: '/admin/broadcasts', query: { tab: 'system' } }">系统消息</router-link>
          <router-link v-if="auth.isRoot" class="btn-primary" :to="{ path: '/admin/broadcasts', query: { tab: 'email' } }">邮件群发</router-link>
          <button class="btn-secondary" type="button" @click="load">刷新</button>
        </div>
      </div>

      <div v-if="loading" class="surface-card p-12 text-center text-slate-500">正在加载后台数据…</div>
      <div v-else>
        <div class="mb-5 flex flex-wrap gap-2 border-b border-slate-200 pb-3 dark:border-neutral-800" role="tablist" aria-label="管理模块">
          <button v-for="tab in tabs" :key="tab.key" class="rounded-md px-3 py-2 text-sm font-medium" :class="activeTab === tab.key ? 'bg-blue-600 text-white' : 'text-slate-600 hover:bg-slate-100 dark:text-slate-300 dark:hover:bg-neutral-900'" type="button" role="tab" :aria-selected="activeTab === tab.key" @click="activeTab = tab.key">
            {{ tab.label }}<span v-if="tab.count()" class="ml-1.5 text-xs opacity-80">{{ tab.count() }}</span>
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
                  <p class="font-semibold">举报 #{{ report.id }} · {{ targetLabel(report.target_type) }} #{{ report.target_id }}</p>
                  <p class="mt-1 text-xs text-slate-500">举报人 UID {{ report.reporter_uid }} · {{ formatDate(report.created_at) }}</p>
                </div>
                <span class="shrink-0 text-xs text-slate-500">{{ report.status }}</span>
              </div>
              <p class="mt-3 whitespace-pre-wrap break-words text-sm text-slate-700 dark:text-slate-200">{{ report.reason }}</p>
              <p v-if="report.handle_result" class="mt-2 whitespace-pre-wrap break-words text-sm text-slate-500">处理结果：{{ report.handle_result }}</p>
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
            <table class="min-w-[960px] w-full text-left text-sm">
              <thead><tr class="border-b border-slate-200 text-slate-500 dark:border-neutral-800"><th class="px-2 py-2">用户</th><th class="px-2 py-2">邮箱</th><th class="px-2 py-2">角色</th><th class="px-2 py-2">状态</th><th class="px-2 py-2">用户组</th><th class="px-2 py-2">操作</th></tr></thead>
              <tbody>
                <tr v-for="user in users" :key="user.uid" class="border-b border-slate-100 align-top dark:border-neutral-800">
                  <td class="px-2 py-3"><strong class="block">{{ user.nickname }}</strong><small class="text-slate-400">@{{ user.username }} · UID {{ user.uid }}</small></td>
                  <td class="max-w-56 break-all px-2 py-3 text-slate-600 dark:text-slate-300">{{ user.email }}</td>
                  <td class="px-2 py-3"><select v-model="user.role" class="form-control w-28" :disabled="!auth.isRoot || user.uid === auth.user?.uid"><option value="user">user</option><option value="admin">admin</option><option value="root">root</option></select></td>
                  <td class="px-2 py-3"><select v-model="user.status" class="form-control w-36" :disabled="!auth.isRoot || user.uid === auth.user?.uid"><option value="active">active</option><option value="pending_email">pending_email</option><option value="silenced">silenced</option><option value="banned">banned</option></select></td>
                  <td class="min-w-52 px-2 py-3"><div class="space-y-1"><label v-for="group in groups" :key="group.id" class="flex items-center gap-2 text-xs"><input type="checkbox" :checked="groupContains(group, user)" :disabled="!auth.isRoot || savingKey === `group:${group.id}:${user.uid}`" @change="toggleGroupFromEvent(user, group, $event)"><span>{{ group.name }}</span></label><span v-if="!groups.length" class="text-xs text-slate-400">暂无用户组</span></div></td>
                  <td class="px-2 py-3"><button v-if="auth.isRoot && user.uid !== auth.user?.uid" class="btn-secondary whitespace-nowrap text-xs" type="button" :disabled="savingKey === `user:${user.uid}`" @click="saveUser(user)">{{ savingKey === `user:${user.uid}` ? '保存中…' : '保存用户' }}</button><span v-else class="text-xs text-slate-400">当前根用户</span></td>
                </tr>
              </tbody>
            </table>
          </div>
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
              <div class="flex items-center gap-2"><span class="mr-2 text-xs text-slate-500">{{ group.member_count }} 名成员</span><button v-if="auth.isRoot" class="btn-secondary text-xs" type="button" :disabled="savingKey === `group:${group.id}`" @click="saveGroup(group)">保存</button><button v-if="auth.isRoot" class="text-xs text-red-600" type="button" :disabled="savingKey === `group:${group.id}`" @click="deleteGroup(group)">删除</button></div>
            </div>
          </div>
        </section>

        <section v-else class="grid gap-6 lg:grid-cols-2">
          <div class="surface-card p-5">
            <h2 class="section-title">发布公告</h2>
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
            <div v-else class="mt-4 divide-y divide-slate-200 border-y border-slate-200 dark:divide-neutral-800 dark:border-neutral-800"><div v-for="item in announcements" :key="item.id" class="py-3"><div class="flex min-w-0 justify-between gap-3"><strong class="min-w-0 break-words">{{ item.title }}</strong><span class="shrink-0 text-xs text-slate-500">{{ item.status }}</span></div><p class="mt-1 line-clamp-2 break-words text-sm text-slate-600 dark:text-slate-300">{{ item.content }}</p><button v-if="item.status === 'draft'" class="mt-2 text-sm text-blue-600" type="button" @click="publish(item)">发布</button></div></div>
          </div>
        </section>
      </div>
    </div>
  </main>
</template>
