<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import {
  ArrowLeftIcon,
  ArrowPathIcon,
  CheckIcon,
  FaceSmileIcon,
  FlagIcon,
  PaperAirplaneIcon,
  SignalIcon,
  SignalSlashIcon,
} from '@heroicons/vue/24/outline'
import EmojiPicker from '@/components/EmojiPicker.vue'
import UserBadges from '@/components/UserBadges.vue'
import { useAuthStore } from '@/stores/auth'
import { useChatStore, type ChatItem } from '@/stores/chat'
import ReportDialog from '@/components/ReportDialog.vue'
import { formatChinaMessageTime } from '@/utils/datetime'

const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const chat = useChatStore()
const composer = ref('')
const composerInput = ref<HTMLTextAreaElement | null>(null)
const messageEnd = ref<HTMLElement | null>(null)
const showEmoji = ref(false)
const sending = ref(false)
const reportMessageId = ref<number | null>(null)
const mobileDetail = computed(() => chat.activeConversationId !== null)
let typingTimer: number | undefined

const currentUid = computed(() => auth.user?.uid ?? Number(localStorage.getItem('user_uid')))
const statusLabel = computed(() => {
  if (chat.socketStatus === 'connected') return '实时连接'
  if (chat.socketStatus === 'connecting') return '连接中'
  return '轮询模式'
})

function avatarInitial(conversation: { other_user: { nickname: string } }) {
  return conversation.other_user.nickname.slice(0, 1).toUpperCase() || '?'
}

function isMine(message: ChatItem) {
  return message.sender_uid === currentUid.value
}

function messageLevel(message: ChatItem) {
  return isMine(message)
    ? auth.user?.level || Math.max(0, Math.floor((auth.user?.points || 0) / 100))
    : chat.activeConversation?.other_user.level || 0
}

function messageUser(message: ChatItem) {
  return isMine(message) ? auth.user : chat.activeConversation?.other_user
}

function scrollToBottom() {
  void nextTick(() => messageEnd.value?.scrollIntoView({ behavior: 'smooth', block: 'end' }))
}

async function selectConversation(id: number) {
  showEmoji.value = false
  composer.value = ''
  stopTyping()
  await chat.openConversation(id)
  await router.replace({ path: '/messages', query: { conversation: String(id) } })
  scrollToBottom()
}

async function openRequestedConversation() {
  const uid = Number(route.query.uid)
  if (Number.isInteger(uid) && uid > 0 && uid !== currentUid.value) {
    const conversation = await chat.openConversationForUser(uid)
    if (conversation) {
      await router.replace({ path: '/messages', query: { conversation: String(conversation.id) } })
      scrollToBottom()
    }
    return
  }
  const conversationId = Number(route.query.conversation)
  if (Number.isInteger(conversationId) && conversationId > 0) {
    await chat.openConversation(conversationId)
    return
  }
  if (chat.conversations.length && chat.activeConversationId === null) {
    await chat.openConversation(chat.conversations[0].id)
  }
}

async function initialize() {
  await chat.loadConversations()
  chat.connect()
  await openRequestedConversation()
}

function backToList() {
  showEmoji.value = false
  composer.value = ''
  chat.closeConversation()
  void router.replace({ path: '/messages' })
}

function insertEmoji(emoji: string) {
  const input = composerInput.value
  if (!input) {
    composer.value += emoji
    return
  }
  const start = input.selectionStart ?? composer.value.length
  const end = input.selectionEnd ?? start
  composer.value = `${composer.value.slice(0, start)}${emoji}${composer.value.slice(end)}`
  showEmoji.value = false
  void nextTick(() => {
    input.focus()
    const cursor = start + emoji.length
    input.setSelectionRange(cursor, cursor)
  })
}

function onComposerInput() {
  chat.setTyping(true)
  if (typingTimer !== undefined) window.clearTimeout(typingTimer)
  typingTimer = window.setTimeout(() => {
    chat.setTyping(false)
    typingTimer = undefined
  }, 2500)
}

function stopTyping() {
  if (typingTimer !== undefined) window.clearTimeout(typingTimer)
  typingTimer = undefined
  chat.setTyping(false)
}

async function send() {
  if (sending.value || !composer.value.trim() || !chat.activeConversation) return
  sending.value = true
  stopTyping()
  const success = await chat.sendMessage(composer.value)
  if (success) {
    composer.value = ''
    showEmoji.value = false
    scrollToBottom()
  }
  sending.value = false
}

async function retry(message: ChatItem) {
  await chat.retryMessage(message)
  scrollToBottom()
}

async function loadOlder() {
  const id = chat.activeConversationId
  const cursor = id === null ? null : chat.messagesByConversation[id]?.[0]?.id
  if (id !== null && chat.hasMoreMessages && cursor) {
    await chat.loadMessages(id, cursor)
  }
}

watch(
  () => route.query.uid,
  (value) => {
    if (value) void openRequestedConversation()
  },
)
watch(
  () => chat.activeMessages.length,
  () => scrollToBottom(),
)

onMounted(() => {
  void initialize()
})

onUnmounted(() => {
  stopTyping()
  chat.closeConversation()
})
</script>

<template>
  <main class="page-shell">
    <div class="page-container max-w-6xl">
      <header class="flex items-center justify-between gap-4 border-b border-slate-200 pb-5 dark:border-neutral-800">
        <div class="min-w-0">
          <h1 class="section-title text-2xl">私信</h1>
          <p class="mt-1 text-sm text-slate-500">一对一会话</p>
        </div>
        <div class="flex shrink-0 items-center gap-2 text-xs text-slate-500" :title="chat.socketError || statusLabel">
          <SignalIcon v-if="chat.socketStatus === 'connected'" class="h-4 w-4 text-emerald-600" aria-hidden="true" />
          <SignalSlashIcon v-else class="h-4 w-4 text-amber-600" aria-hidden="true" />
          <span class="hidden sm:inline">{{ statusLabel }}</span>
          <button v-if="chat.socketStatus === 'offline'" class="p-1 text-slate-500 hover:text-blue-600" type="button" aria-label="重新连接" title="重新连接" @click="chat.connect">
            <ArrowPathIcon class="h-4 w-4" aria-hidden="true" />
          </button>
        </div>
      </header>

      <div class="mt-5 grid h-[calc(100dvh-12rem)] min-h-0 overflow-hidden border border-slate-200 bg-white dark:border-neutral-800 dark:bg-neutral-950 lg:h-[clamp(32rem,calc(100dvh-12rem),45rem)] lg:grid-cols-[320px_minmax(0,1fr)]">
        <aside :class="[mobileDetail ? 'hidden lg:flex' : 'flex', 'min-h-0 flex-col border-r border-slate-200 dark:border-neutral-800']">
          <div class="flex items-center justify-between border-b border-slate-200 px-4 py-3 dark:border-neutral-800">
            <h2 class="font-semibold">会话</h2>
            <span class="text-xs text-slate-500">{{ chat.conversations.length }}</span>
          </div>
          <div v-if="chat.loadingConversations" class="p-6 text-center text-sm text-slate-500">正在加载…</div>
          <div v-else-if="chat.error && !chat.conversations.length" class="p-5 text-center text-sm text-red-600">
            <p>{{ chat.error }}</p>
            <button class="btn-secondary mt-3 text-sm" type="button" @click="chat.loadConversations">重试</button>
          </div>
          <div v-else-if="!chat.conversations.length" class="p-6 text-center text-sm text-slate-500">暂无会话</div>
          <div v-else class="min-h-0 flex-1 overflow-y-auto">
            <div
              v-for="conversation in chat.conversations"
              :key="conversation.id"
              class="flex min-h-20 w-full items-center gap-3 border-b border-slate-100 px-4 py-3 text-left transition hover:bg-slate-50 dark:border-neutral-800 dark:hover:bg-neutral-800"
              :class="chat.activeConversationId === conversation.id ? 'bg-blue-50 dark:bg-blue-950/30' : ''"
            >
              <router-link :to="`/profile/${conversation.other_user.uid}`" class="shrink-0" :aria-label="`查看 ${conversation.other_user.nickname} 的个人主页`" :title="`查看 ${conversation.other_user.nickname} 的个人主页`" @click.stop>
                <img v-if="conversation.other_user.avatar_url" :src="conversation.other_user.avatar_url" alt="" class="h-10 w-10 rounded-full object-cover">
                <span v-else class="flex h-10 w-10 items-center justify-center rounded-full bg-blue-100 font-semibold text-blue-700 dark:bg-blue-900/50 dark:text-blue-200">{{ avatarInitial(conversation) }}</span>
              </router-link>
              <button class="min-w-0 flex-1 text-left" type="button" @click="selectConversation(conversation.id)">
                <span class="flex items-center justify-between gap-2">
                  <strong class="truncate text-sm">{{ conversation.other_user.nickname }}</strong>
                  <time v-if="conversation.last_message_at" class="shrink-0 text-[11px] text-slate-400">{{ formatChinaMessageTime(conversation.last_message_at) }}</time>
                </span>
                <UserBadges class="mt-1" :level="conversation.other_user.level" :band="conversation.other_user.level_band" :permission-groups="conversation.other_user.permission_groups" :role="conversation.other_user.role" compact />
                <span class="mt-1 flex items-center justify-between gap-2">
                  <span class="truncate text-xs text-slate-500">{{ conversation.last_message?.content || '开始聊天' }}</span>
                  <span v-if="conversation.unread_count" class="h-2.5 w-2.5 shrink-0 rounded-full bg-red-500" aria-label="有未读私信"></span>
                </span>
              </button>
            </div>
          </div>
        </aside>

        <section :class="[mobileDetail ? 'flex' : 'hidden lg:flex', 'min-h-0 min-w-0 flex-1 flex-col']">
          <template v-if="chat.activeConversation">
            <header class="flex min-h-16 items-center gap-3 border-b border-slate-200 px-4 py-3 dark:border-neutral-800">
              <button class="p-1 text-slate-500 hover:text-blue-600 lg:hidden" type="button" aria-label="返回会话列表" title="返回会话列表" @click="backToList">
                <ArrowLeftIcon class="h-5 w-5" aria-hidden="true" />
              </button>
              <router-link :to="`/profile/${chat.activeConversation.other_user.uid}`" class="shrink-0" :aria-label="`查看 ${chat.activeConversation.other_user.nickname} 的个人主页`" :title="`查看 ${chat.activeConversation.other_user.nickname} 的个人主页`">
                <img v-if="chat.activeConversation.other_user.avatar_url" :src="chat.activeConversation.other_user.avatar_url" alt="" class="h-9 w-9 rounded-full object-cover">
                <span v-else class="flex h-9 w-9 items-center justify-center rounded-full bg-blue-100 text-sm font-semibold text-blue-700 dark:bg-blue-900/50 dark:text-blue-200">{{ avatarInitial(chat.activeConversation) }}</span>
              </router-link>
              <div class="min-w-0">
                <h2 class="truncate font-semibold">{{ chat.activeConversation.other_user.nickname }}</h2>
                <UserBadges :level="chat.activeConversation.other_user.level" :band="chat.activeConversation.other_user.level_band" :permission-groups="chat.activeConversation.other_user.permission_groups" :role="chat.activeConversation.other_user.role" compact />
                <p class="truncate text-xs text-slate-500">@{{ chat.activeConversation.other_user.username }}</p>
              </div>
            </header>

            <div class="min-h-0 flex-1 overflow-y-auto px-4 py-5 sm:px-6">
              <div v-if="chat.hasMoreMessages" class="mb-4 text-center">
                <button class="text-xs text-blue-600 hover:underline disabled:opacity-50" type="button" :disabled="chat.loadingOlderMessages" @click="loadOlder">{{ chat.loadingOlderMessages ? '正在加载…' : '加载更早消息' }}</button>
              </div>
              <div v-if="chat.loadingMessages && !chat.activeMessages.length" class="py-12 text-center text-sm text-slate-500">正在加载消息…</div>
              <div v-else-if="!chat.activeMessages.length" class="py-16 text-center text-sm text-slate-500">还没有消息，打个招呼吧。</div>
              <div v-else class="space-y-4">
                <div v-for="message in chat.activeMessages" :key="message.clientId || message.id" class="flex" :class="isMine(message) ? 'justify-end' : 'justify-start'">
                  <div class="max-w-[min(85%,38rem)]">
                    <div class="mb-1 flex items-center gap-2 text-xs" :class="isMine(message) ? 'justify-end' : 'justify-start'"><UserBadges :level="messageLevel(message)" :band="messageUser(message)?.level_band" :permission-groups="messageUser(message)?.permission_groups" :role="messageUser(message)?.role" compact /></div>
                    <div class="break-words whitespace-pre-wrap px-4 py-2.5 text-sm" :class="isMine(message) ? 'bg-blue-600 text-white' : 'bg-slate-100 text-slate-800 dark:bg-neutral-900 dark:text-slate-100'" :data-testid="isMine(message) ? 'outgoing-message' : 'incoming-message'">{{ message.content }}</div>
                    <div class="mt-1 flex items-center gap-2 text-[11px] text-slate-400" :class="isMine(message) ? 'justify-end' : 'justify-start'">
                      <time>{{ formatChinaMessageTime(message.created_at) }}</time>
                      <button v-if="!isMine(message) && message.id > 0" class="inline-flex items-center gap-1 text-red-600 hover:underline" type="button" @click="reportMessageId = message.id"><FlagIcon class="h-3 w-3" aria-hidden="true" />举报</button>
                      <template v-if="isMine(message)">
                        <span v-if="message.deliveryStatus === 'sending'">发送中…</span>
                        <button v-else-if="message.deliveryStatus === 'failed'" class="inline-flex items-center gap-1 text-red-600 hover:underline" type="button" @click="retry(message)">
                          <ArrowPathIcon class="h-3 w-3" aria-hidden="true" />重试
                        </button>
                        <span v-else-if="message.is_read" class="inline-flex items-center gap-1"><CheckIcon class="h-3 w-3" aria-hidden="true" />已读</span>
                      </template>
                    </div>
                    <p v-if="message.deliveryStatus === 'failed' && message.sendError" class="mt-1 text-right text-[11px] text-red-600">{{ message.sendError }}</p>
                  </div>
                </div>
                <p v-if="chat.isTyping" class="text-xs text-slate-500">正在输入…</p>
              </div>
              <div ref="messageEnd" class="h-px"></div>
            </div>

            <div class="border-t border-slate-200 px-3 pt-3 pb-[calc(0.75rem+env(safe-area-inset-bottom))] dark:border-neutral-800 sm:p-4">
              <div v-if="chat.socketError" class="mb-2 text-xs text-amber-700 dark:text-amber-300">{{ chat.socketError }}</div>
              <div class="relative flex items-end gap-2">
                <button class="flex h-10 w-10 shrink-0 items-center justify-center text-slate-500 transition hover:bg-slate-100 hover:text-blue-600 dark:hover:bg-neutral-800" type="button" aria-label="打开表情" title="打开表情" @click="showEmoji = !showEmoji">
                  <FaceSmileIcon class="h-5 w-5" aria-hidden="true" />
                </button>
                <EmojiPicker v-if="showEmoji" @select="insertEmoji" />
                <textarea ref="composerInput" v-model="composer" class="form-control min-h-10 min-w-0 max-h-36 flex-1 resize-y py-2.5" rows="1" maxlength="4000" aria-label="消息内容" placeholder="输入消息…" @input="onComposerInput" @blur="stopTyping" @keydown.enter.exact.prevent="send"></textarea>
                <button class="btn-primary h-10 w-10 shrink-0 p-0" type="button" aria-label="发送" title="发送" :disabled="sending || !composer.trim()" @click="send">
                  <PaperAirplaneIcon class="h-5 w-5" aria-hidden="true" />
                </button>
              </div>
            </div>
          </template>
          <div v-else class="flex flex-1 flex-col items-center justify-center p-10 text-center text-slate-500">
            <div class="mb-4 flex h-14 w-14 items-center justify-center rounded-full bg-slate-100 dark:bg-neutral-900">
              <SignalIcon class="h-7 w-7" aria-hidden="true" />
            </div>
            <p>选择一个会话开始交流</p>
            <p class="mt-1 text-xs">也可以从个人主页发起私信</p>
          </div>
        </section>
      </div>
      <ReportDialog v-if="reportMessageId" :open="true" target-type="message" :target-id="reportMessageId" @close="reportMessageId = null" />
    </div>
  </main>
</template>
