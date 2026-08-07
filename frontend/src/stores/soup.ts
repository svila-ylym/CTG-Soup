import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { soupApi } from '@/api/soup'
import type { TurtleSoup, SoupCreate, SoupScore } from '@/types'

export const useSoupStore = defineStore('soup', () => {
  const soups = ref<TurtleSoup[]>([])
  const currentSoup = ref<TurtleSoup | null>(null)
  const leaderboard = ref<TurtleSoup[]>([])
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  // 获取海龟汤列表
  async function fetchList(page = 1, pageSize = 20, tag?: string, sort?: string) {
    isLoading.value = true
    error.value = null
    try {
      const res = await soupApi.getList({ page, page_size: pageSize, tag, sort })
      soups.value = res.data.items
      return res.data
    } catch (e: any) {
      error.value = e.response?.data?.message || '获取列表失败'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // 获取海龟汤详情
  async function fetchById(id: number) {
    isLoading.value = true
    error.value = null
    try {
      const res = await soupApi.getById(id)
      currentSoup.value = res.data
      return res.data
    } catch (e: any) {
      error.value = e.response?.data?.message || '获取详情失败'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // 创建海龟汤
  async function createSoup(data: SoupCreate) {
    isLoading.value = true
    error.value = null
    try {
      const res = await soupApi.create(data)
      return { success: true, id: res.data.id }
    } catch (e: any) {
      error.value = e.response?.data?.message || '创建失败'
      return { success: false, message: error.value }
    } finally {
      isLoading.value = false
    }
  }

  // 评分
  async function submitScore(soupId: number, score: number) {
    error.value = null
    try {
      await soupApi.score({ soup_id: soupId, score })
      // 更新本地缓存
      if (currentSoup.value?.id === soupId) {
        await fetchById(soupId)
      }
      return { success: true }
    } catch (e: any) {
      error.value = e.response?.data?.message || '评分失败'
      return { success: false, message: error.value }
    }
  }

  // 点赞
  async function toggleLike(id: number) {
    error.value = null
    try {
      const soup = soups.value.find(s => s.id === id) || currentSoup.value
      if (!soup) return
      
      if (soup.like_count > 0) {
        await soupApi.unlike(id)
        soup.like_count--
      } else {
        await soupApi.like(id)
        soup.like_count++
      }
      return { success: true }
    } catch (e: any) {
      error.value = e.response?.data?.message || '操作失败'
      return { success: false, message: error.value }
    }
  }

  // 收藏
  async function toggleFavorite(id: number) {
    error.value = null
    try {
      const soup = soups.value.find(s => s.id === id) || currentSoup.value
      if (!soup) return
      
      if (soup.favorite_count > 0) {
        await soupApi.unfavorite(id)
        soup.favorite_count--
      } else {
        await soupApi.favorite(id)
        soup.favorite_count++
      }
      return { success: true }
    } catch (e: any) {
      error.value = e.response?.data?.message || '操作失败'
      return { success: false, message: error.value }
    }
  }

  // 获取排行榜
  async function fetchLeaderboard(limit = 10, type: 'average' | 'bayesian' = 'bayesian') {
    isLoading.value = true
    error.value = null
    try {
      const res = await soupApi.getLeaderboard({ limit, type })
      leaderboard.value = res.data
      return res.data
    } catch (e: any) {
      error.value = e.response?.data?.message || '获取排行榜失败'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // 搜索
  async function search(keyword: string, page = 1, pageSize = 20) {
    isLoading.value = true
    error.value = null
    try {
      const res = await soupApi.search(keyword, { page, page_size: pageSize })
      soups.value = res.data.items
      return res.data
    } catch (e: any) {
      error.value = e.response?.data?.message || '搜索失败'
      throw e
    } finally {
      isLoading.value = false
    }
  }

  // 清空当前海龟汤
  function clearCurrent() {
    currentSoup.value = null
  }

  return {
    soups,
    currentSoup,
    leaderboard,
    isLoading,
    error,
    fetchList,
    fetchById,
    createSoup,
    submitScore,
    toggleLike,
    toggleFavorite,
    fetchLeaderboard,
    search,
    clearCurrent,
  }
})
