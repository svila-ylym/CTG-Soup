<script setup lang="ts">
import { onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import http from '@/api/http'
import { authApi } from '@/api/auth'
import { uploadApi } from '@/api/upload'
import { useAuthStore } from '@/stores/auth'
import { extractApiError } from '@/utils/auth'
import { applyTheme } from '@/utils/theme'
import type { ThemePreference, UploadedAsset, User } from '@/types'

type SettingsTab = 'profile' | 'security' | 'notifications' | 'appearance'

const router = useRouter()
const auth = useAuthStore()
const activeTab = ref<SettingsTab>('profile')
const tabs: Array<{ id: SettingsTab; label: string }> = [
  { id: 'profile', label: '个人资料' },
  { id: 'security', label: '账户安全' },
  { id: 'notifications', label: '通知' },
  { id: 'appearance', label: '外观' },
]
const themeOptions: Array<{ value: ThemePreference; label: string }> = [
  { value: 'light', label: '浅色' },
  { value: 'dark', label: '深色' },
  { value: 'system', label: '跟随系统' },
]

const profile = reactive({ nickname: '', email: '', bio: '' })
const password = reactive({ old: '', next: '', confirm: '' })
const selectedAvatarId = ref<number | null>(null)
const avatarChanged = ref(false)
const assets = ref<UploadedAsset[]>([])
const allowBulkEmail = ref(false)
const themePreference = ref<ThemePreference>('system')
const busy = ref(false)
const uploading = ref(false)
const message = ref('')
const error = ref('')

function populate(user: User | null) {
  if (!user) return
  profile.nickname = user.nickname
  profile.email = user.email
  profile.bio = user.bio || ''
  selectedAvatarId.value = user.avatar_asset_id ?? null
  allowBulkEmail.value = user.allow_bulk_email ?? false
  themePreference.value = user.theme_preference || 'system'
}

watch(() => auth.user, populate, { immediate: true })

function clearFeedback() {
  message.value = ''
  error.value = ''
}

async function loadAssets() {
  assets.value = (await uploadApi.images()).data
}

async function saveProfile() {
  busy.value = true
  clearFeedback()
  try {
    const payload: Record<string, unknown> = {
      nickname: profile.nickname,
      email: profile.email,
      bio: profile.bio,
    }
    if (avatarChanged.value) payload.avatar_asset_id = selectedAvatarId.value
    const response = await http.put<User>('/users/me', payload)
    auth.setUser(response.data)
    avatarChanged.value = false
    message.value = '资料已保存'
  } catch (reason) {
    error.value = extractApiError(reason, '保存失败')
  } finally {
    busy.value = false
  }
}

async function uploadAvatar(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  uploading.value = true
  clearFeedback()
  try {
    const result = (await uploadApi.image(file)).data
    await loadAssets()
    selectedAvatarId.value = result.asset_id
    avatarChanged.value = true
    message.value = '头像已上传，保存资料后生效'
  } catch (reason) {
    error.value = extractApiError(reason, '头像上传失败')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

function selectAvatar(assetId: number | null) {
  selectedAvatarId.value = assetId
  avatarChanged.value = true
}

async function changePassword() {
  clearFeedback()
  if (password.next !== password.confirm) {
    error.value = '两次输入的新密码不一致'
    return
  }
  busy.value = true
  try {
    await authApi.changePassword(password.old, password.next)
    auth.logout()
    await router.replace({ name: 'Login', query: { notice: 'password-changed' } })
  } catch (reason) {
    error.value = extractApiError(reason, '密码修改失败')
  } finally {
    busy.value = false
  }
}

async function savePreferences(values: {
  allow_bulk_email?: boolean
  theme_preference?: ThemePreference
}) {
  busy.value = true
  clearFeedback()
  try {
    const response = await http.put<User>('/users/me/preferences', values)
    auth.setUser(response.data)
    message.value = '设置已保存'
  } catch (reason) {
    error.value = extractApiError(reason, '设置保存失败')
  } finally {
    busy.value = false
  }
}

function chooseTheme(value: ThemePreference) {
  themePreference.value = value
  applyTheme(value)
}

onMounted(async () => {
  try {
    if (!auth.user) await auth.fetchCurrentUser()
    populate(auth.user)
    await loadAssets()
  } catch (reason) {
    error.value = extractApiError(reason, '设置加载失败')
  }
})
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-4xl">
      <h1 class="section-title text-2xl">设置</h1>

      <div class="mt-6 lg:grid lg:grid-cols-[11rem_minmax(0,1fr)] lg:gap-8">
        <div class="flex gap-1 overflow-x-auto border-b border-slate-200 dark:border-neutral-800 lg:flex-col lg:overflow-visible lg:border-b-0 lg:border-r lg:pr-4">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            class="shrink-0 border-b-2 px-4 py-3 text-sm font-medium lg:w-full lg:border-b-0 lg:border-l-2 lg:px-3 lg:py-2 lg:text-left"
            :class="activeTab === tab.id ? 'border-blue-600 text-blue-600' : 'border-transparent text-slate-500'"
            type="button"
            @click="activeTab = tab.id; clearFeedback()"
          >
            {{ tab.label }}
          </button>
        </div>

        <div class="min-w-0">

      <section v-if="activeTab === 'profile'" class="py-7">
        <h2 class="section-title">个人资料</h2>
        <form class="mt-5 max-w-2xl space-y-5" @submit.prevent="saveProfile">
          <div>
            <span class="mb-2 block text-sm font-medium">头像</span>
            <div class="flex flex-wrap gap-3">
              <button
                v-for="asset in assets"
                :key="asset.id"
                class="h-20 w-20 overflow-hidden border-2"
                :class="selectedAvatarId === asset.id ? 'border-blue-600' : 'border-transparent'"
                type="button"
                :aria-label="`选择头像 ${asset.id}`"
                @click="selectAvatar(asset.id)"
              >
                <img :src="asset.public_url" alt="" class="h-full w-full object-cover">
              </button>
              <button
                v-if="selectedAvatarId !== null"
                class="h-20 w-20 border border-dashed border-slate-300 text-sm text-slate-500 dark:border-neutral-700"
                type="button"
                @click="selectAvatar(null)"
              >移除头像</button>
            </div>
            <label class="btn-secondary mt-3 inline-flex cursor-pointer">
              {{ uploading ? '上传中…' : '上传头像' }}
              <input class="sr-only" type="file" accept="image/jpeg,image/png,image/gif,image/webp" :disabled="uploading" @change="uploadAvatar">
            </label>
          </div>

          <label class="block">
            <span class="mb-2 block text-sm font-medium">昵称</span>
            <input v-model.trim="profile.nickname" class="form-control" required maxlength="50">
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium">邮箱</span>
            <input v-model.trim="profile.email" class="form-control" type="email" required>
          </label>
          <label class="block">
            <span class="mb-2 block text-sm font-medium">个人简介</span>
            <textarea v-model="profile.bio" class="form-control min-h-32" maxlength="500"></textarea>
          </label>
          <button class="btn-primary" :disabled="busy">{{ busy ? '保存中…' : '保存资料' }}</button>
        </form>
      </section>

      <section v-if="activeTab === 'security'" class="py-7">
        <h2 class="section-title">修改密码</h2>
        <form class="mt-5 max-w-md space-y-5" @submit.prevent="changePassword">
          <label class="block"><span class="mb-2 block text-sm font-medium">原密码</span><input v-model="password.old" class="form-control" type="password" required autocomplete="current-password"></label>
          <label class="block"><span class="mb-2 block text-sm font-medium">新密码</span><input v-model="password.next" class="form-control" type="password" required minlength="8" autocomplete="new-password"></label>
          <label class="block"><span class="mb-2 block text-sm font-medium">确认新密码</span><input v-model="password.confirm" class="form-control" type="password" required minlength="8" autocomplete="new-password"></label>
          <button class="btn-primary" :disabled="busy">{{ busy ? '提交中…' : '修改密码' }}</button>
        </form>
      </section>

      <section v-if="activeTab === 'notifications'" class="py-7">
        <h2 class="section-title">邮件通知</h2>
        <label class="mt-5 flex max-w-xl items-start gap-3">
          <input v-model="allowBulkEmail" class="mt-1 h-4 w-4" type="checkbox">
          <span>
            <strong class="block text-sm">接收社区批量邮件</strong>
            <span class="mt-1 block text-sm text-slate-500">仅在主动开启后接收管理员发布的活动和社区邮件。</span>
          </span>
        </label>
        <button class="btn-primary mt-5" :disabled="busy" @click="savePreferences({ allow_bulk_email: allowBulkEmail })">保存通知设置</button>
      </section>

      <section v-if="activeTab === 'appearance'" class="py-7">
        <h2 class="section-title">主题</h2>
        <div class="mt-5 inline-flex border border-slate-300 dark:border-neutral-700" role="group" aria-label="主题偏好">
          <button
            v-for="option in themeOptions"
            :key="option.value"
            class="px-4 py-2 text-sm"
            :class="themePreference === option.value ? 'bg-blue-600 text-white' : 'text-slate-600 dark:text-slate-300'"
            type="button"
            @click="chooseTheme(option.value)"
          >{{ option.label }}</button>
        </div>
        <div class="mt-5">
          <button class="btn-primary" :disabled="busy" @click="savePreferences({ theme_preference: themePreference })">保存外观设置</button>
        </div>
      </section>

          <p v-if="message" class="break-words pb-6 text-sm text-green-700 dark:text-green-400">{{ message }}</p>
          <p v-if="error" class="break-words pb-6 text-sm text-red-700 dark:text-red-400">{{ error }}</p>
        </div>
      </div>
    </div>
  </main>
</template>
