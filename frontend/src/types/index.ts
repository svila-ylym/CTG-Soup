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
  avatar?: string
  role: 'user' | 'admin' | 'root'
  status: 'active' | 'banned' | 'muted'
  score: number
  created_at: string
  titles: string[]
}

export interface LoginRequest {
  username: string
  password: string
}

export interface RegisterRequest {
  username: string
  password: string
  email: string
}

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

// 海龟汤相关
export interface TurtleSoup {
  id: number
  title: string
  puzzle: string
  solution?: string
  author: User
  tags: string[]
  avg_score: number
  score_count: number
  like_count: number
  favorite_count: number
  status: 'visible' | 'hidden' | 'deleted'
  created_at: string
  updated_at: string
}

export interface SoupCreate {
  title: string
  puzzle: string
  solution: string
  tags: string[]
}

export interface SoupScore {
  soup_id: number
  score: number // 1-10, 支持 0.5 步进
}

// 帖子相关
export interface Post {
  id: number
  title: string
  content: string
  author: User
  category: string
  tags: string[]
  type: 'normal' | 'poll' | 'turtle_soup'
  like_count: number
  comment_count: number
  favorite_count: number
  status: 'visible' | 'hidden' | 'deleted'
  created_at: string
  updated_at: string
}

export interface Comment {
  id: number
  content: string
  author: User
  target_type: 'post' | 'soup'
  target_id: number
  like_count: number
  status: 'visible' | 'hidden' | 'deleted'
  created_at: string
  replies?: Comment[]
}

// 比赛相关
export interface Competition {
  id: number
  name: string
  description: string
  start_time: string
  end_time: string
  tags: string[]
  scoring_method: 'average' | 'highest'
  top_n: number
  custom_page: any
  status: 'pending' | 'ongoing' | 'ended'
  creator: User
  created_at: string
}

export interface CompetitionEntry {
  competition_id: number
  soup_id: number
  final_score: number
  author_uid: number
  rank: number
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
  content: string
  is_read: boolean
  sender_deleted: boolean
  receiver_deleted: boolean
  created_at: string
}

export interface Notification {
  id: number
  receiver_uid: number
  type: 'mention' | 'comment' | 'reply' | 'score' | 'report' | 'punishment' | 'role_change' | 'achievement' | 'competition'
  title: string
  content: string
  entity_id?: number
  entity_type?: string
  is_read: boolean
  created_at: string
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
}

// 搜索参数
export interface SearchParams {
  keyword: string
  type?: 'user' | 'post' | 'soup'
  sort?: 'relevance' | 'time' | 'likes'
  page?: number
  page_size?: number
}
