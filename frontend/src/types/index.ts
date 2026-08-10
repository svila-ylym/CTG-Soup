// API 响应接口
export interface ApiResponse<T = any> {
  code: number
  message: string
  data: T
}

// 用户相关
export interface User {
  uid: number
  username: string
  nickname: string
  email: string
  avatar_url?: string
  avatar_asset_id?: number | null
  profile_background_url?: string | null
  profile_background_asset_id?: number | null
  bio?: string
  role: 'user' | 'admin' | 'root'
  status: 'pending_email' | 'active' | 'banned' | 'silenced'
  points: number
  level?: number
  level_band?: string
  consecutive_signin_days: number
  allow_bulk_email: boolean
  theme_preference: ThemePreference
  created_at: string
}

export type ThemePreference = 'light' | 'dark' | 'system'

export interface UploadedAsset {
  id: number
  owner_uid: number
  kind: 'image'
  storage_key: string
  public_url: string
  mime_type: string
  size: number
  created_at: string
}

export interface UploadImageResult {
  asset_id: number
  url: string
  storage: 'local'
  key: string
  mime_type: string
  size: number
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  nickname: string
  password: string
  email: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in?: number
}

// 海龟汤相关
export type SoupGenre = '本格' | '变格' | '鳖汤' | '未分类'
export type SoupColor = '清汤' | '红汤' | '黑汤' | '未分类'
export type CreateSoupGenre = Exclude<SoupGenre, '未分类'>
export type CreateSoupColor = Exclude<SoupColor, '未分类'>

export interface Tag {
  id: number
  slug: string
  name: string
  kind: 'system' | 'custom'
  status: 'active' | 'disabled'
  description?: string | null
  sort_order: number
  view_count: number
  usage_count: number
  created_at: string
  updated_at: string
}

export interface SoupAuthor {
  uid: number
  username: string
  nickname: string
  avatar_url?: string | null
  level?: number
  level_band?: string
}

export interface SoupImageRef {
  id: number
  public_url: string
  mime_type: string
  size: number
}

export interface TurtleSoup {
  id: number
  title: string
  puzzle: string
  solution?: string | null
  puzzle_images: SoupImageRef[]
  solution_images: SoupImageRef[]
  solution_available: boolean
  is_solution_public: boolean
  genre: SoupGenre
  soup_color: SoupColor
  main_player_count: string
  secondary_player_count: string
  author: SoupAuthor
  author_uid: number
  tags: Tag[]
  average_score: number
  rating_count: number
  comment_count: number
  like_count: number
  favorite_count: number
  view_count: number
  status: string
  my_rating: number | null
  is_liked: boolean
  is_favorited: boolean
  can_manage: boolean
  can_edit: boolean
  created_at: string
  updated_at: string
}

export interface SoupCreate {
  title: string
  puzzle: string
  solution: string
  genre: CreateSoupGenre
  soup_color: CreateSoupColor
  main_player_count: string
  secondary_player_count: string
  tag_ids: number[]
  custom_tags: string[]
  puzzle_image_ids: number[]
  solution_image_ids: number[]
  is_revealed?: boolean
}

export type SoupEditorState = Omit<
  SoupCreate,
  'puzzle_image_ids' | 'solution_image_ids'
> & {
  puzzle_images: SoupImageRef[]
  solution_images: SoupImageRef[]
}

export interface SoupScore {
  soup_id: number
  score: number // 1-10, 支持 0.5 步进
}

export interface SoupInteractionState {
  liked?: boolean
  favorited?: boolean
  like_count: number
  favorite_count: number
}

// 帖子相关
export interface Post {
  id: number
  title: string
  content: string
  author_uid: number
  author?: SoupAuthor
  author_username?: string
  author_nickname?: string
  section: string
  tags: string[]
  post_type: 'normal' | 'poll' | 'turtle_soup'
  like_count: number
  comment_count: number
  favorite_count: number
  view_count: number
  status: 'published' | 'hidden' | 'deleted'
  created_at: string
  updated_at: string
  mentions: MentionRef[]
  can_edit: boolean
}

export interface MentionRef {
  uid: number
  username: string
  start_offset: number
  end_offset: number
}

export interface Comment {
  id: number
  content: string
  author_uid: number
  author?: SoupAuthor
  parent_id?: number | null
  created_at: string
  mentions: MentionRef[]
  replies?: Comment[]
}

// 比赛相关
export interface Competition {
  id: number
  name: string
  description: string
  start_time: string
  end_time: string
  creator_uid: number
  required_tag_ids: number[]
  score_type: 'average'
  top_n: number
  custom_page_config: Record<string, unknown>
  status: 'pending' | 'ongoing' | 'completed'
  result_snapshot?: Record<string, unknown> | null
  settled_at?: string | null
  created_at: string
  updated_at: string
  entries?: CompetitionEntry[]
}

export interface CompetitionCreate {
  name: string
  description: string
  start_time: string
  end_time: string
  required_tag_ids: number[]
  custom_tags: string[]
  score_type: 'average'
  top_n: number
  custom_page_config: Record<string, unknown>
}

export type CompetitionUpdate = CompetitionCreate

export interface CompetitionEntry {
  competition_id: number
  soup_id: number
  final_score: number
  author_uid: number
  rank: number | null
}

// 社交相关
export interface FollowRelation {
  follower_uid: number
  following_uid: number
  is_friend: boolean
  created_at: string
}

export interface BlacklistEntry {
  blocker_uid: number
  blocked_uid: number
  created_at: string
}

// 消息相关
export interface Message {
  id: number
  sender_uid: number
  receiver_uid: number
  sender: SoupAuthor
  receiver: SoupAuthor
  sender_username?: string
  receiver_username?: string
  content: string
  is_read: boolean
  sender_deleted: boolean
  receiver_deleted: boolean
  created_at: string
}

export interface ChatMessage {
  id: number
  conversation_id: number
  sender_uid: number
  receiver_uid: number
  content: string
  is_read: boolean
  created_at: string
}

export interface DirectConversation {
  id: number
  other_user: SoupAuthor & { avatar_url?: string | null }
  last_message: ChatMessage | null
  unread_count: number
  last_message_at: string | null
  created_at: string
}

export interface ConversationPage {
  items: DirectConversation[]
  total: number
}

export interface MessageCursorPage {
  items: ChatMessage[]
  next_cursor: number | null
}

export interface SystemMessageAttachment {
  id: number
  original_name: string
  mime_type: string
  size: number
  sha256: string
  created_at: string
}

export interface SystemMessageSummary {
  id: number
  title: string
  sender_uid: number
  is_read: boolean
  attachment_count: number
  created_at: string
}

export interface SystemMessageDetail extends SystemMessageSummary {
  markdown: string
  rendered_html: string
  read_at: string | null
  attachments: SystemMessageAttachment[]
}

export interface SystemMessagePage extends PageResult<SystemMessageSummary> {}

export interface SystemMessageSendResult {
  id: number
  title: string
  recipient_mode: 'selected' | 'all'
  recipient_count: number
  attachment_count: number
  created_at: string
}

export interface BroadcastUser {
  uid: number
  username: string
  nickname: string
  email: string
  role: User['role']
  status: User['status']
  allow_bulk_email?: boolean
}

export type EmailCampaignCategory = 'notice' | 'promotion'
export type EmailCampaignStatus = 'draft' | 'queued' | 'sending' | 'completed' | 'cancelled'

export interface EmailCampaignSummary {
  id: number
  subject: string
  category: EmailCampaignCategory
  recipient_mode: 'selected' | 'all'
  status: EmailCampaignStatus
  selected_count: number
  eligible_count: number
  filtered_count: number
  queued_count: number
  delivered_count: number
  failed_count: number
  attachment_count: number
  created_at: string
  queued_at: string | null
  completed_at: string | null
}

export interface Notification {
  id: number
  recipient_uid: number
  notification_type: string
  title: string
  content: string
  related_entity_id?: number
  related_entity_type?: string
  is_read: boolean
  created_at: string
}

export interface Announcement {
  id: number
  title: string
  content: string
  priority: number
  status: 'draft' | 'published' | 'expired'
  author_uid: number
  published_at?: string | null
  expires_at?: string | null
  created_at: string
  updated_at: string
}

// 成就相关
export interface Achievement {
  code: string
  name: string
  description: string
  icon: string
  title_id: string
  condition_type: string
  condition_params: Record<string, any>
  repeatable: boolean
}

export interface UserAchievement {
  achievement_code: string
  current_value: number
  achieved_at?: string
}

// 举报相关
export interface Report {
  id: number
  reporter_uid: number
  target_type: 'post' | 'comment' | 'soup' | 'message' | 'user'
  target_id: number
  reason: string
  status: 'pending' | 'processed' | 'rejected'
  handler_uid?: number
  processed_at?: string
  created_at: string
}

// 处罚相关
export interface Punishment {
  id: number
  target_uid: number
  operator_uid: number
  type: 'mute' | 'ban' | 'delete_content' | 'disable_comment' | 'limit_flow'
  start_time: string
  end_time?: string
  reason: string
  revoked: boolean
  revoked_by?: number
  revoked_at?: string
  content_id?: number
}

// 分页参数
export interface PageParams {
  page: number
  page_size: number
}

export interface PageResult<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  total_pages?: number
}

// 搜索参数
export interface SearchParams {
  keyword: string
  type?: 'user' | 'post' | 'soup'
  sort?: 'relevance' | 'time' | 'likes'
  page?: number
  page_size?: number
}

export interface SearchUser {
  uid: number
  username: string
  nickname: string
  avatar_url?: string | null
}

export interface SearchPost {
  id: number
  author_uid: number
  title: string
  excerpt: string
  section: string
  created_at: string
}

export interface SearchSoup {
  id: number
  author_uid: number
  title: string
  puzzle_excerpt: string
  average_score: number
  rating_count: number
  favorite_count: number
  created_at: string
}

export interface SearchSectionState<T> {
  items: T[]
  loading: boolean
  error: string
}

export interface PublicProfileUser {
  uid: number
  username: string
  nickname: string
  avatar_url?: string | null
  profile_background_url?: string | null
  bio?: string | null
  role: 'user' | 'admin' | 'root'
  level: number
  level_band: string
  experience_points: number
  level_start: number
  next_level_start: number | null
  created_at: string
}

export interface ProfileStats {
  post_count: number
  soup_count: number
  follower_count: number
  following_count: number
  like_received: number
}

export interface ProfileRelation {
  is_self: boolean
  is_following: boolean
  is_friend: boolean
  is_blocked: boolean
}

export interface ProfileSoupSummary {
  id: number
  title: string
  puzzle_excerpt: string
  genre: string
  soup_color: string
  average_score: number
  rating_count: number
  like_count: number
  favorite_count: number
  created_at: string
}

export interface PublicProfile {
  user: PublicProfileUser
  stats: ProfileStats
  relation: ProfileRelation
  featured_soups: ProfileSoupSummary[]
  soups: PageResult<ProfileSoupSummary>
}

export interface SigninStatus {
  signed_in: boolean
  signin_day: string
  consecutive_days: number
  experience_points: number
  experience_gained: number
  level: number
  level_start: number
  next_level_start: number | null
}
