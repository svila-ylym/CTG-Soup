import { expect, test, type Page } from '@playwright/test'

const discovery = {
  lines: ['把线索拼成一个完整故事。', '每一次提问都离真相更近。'],
  latest_competition: {
    id: 12,
    name: '夏夜推理赛',
    description_excerpt: '围绕夏夜创作一碗让人意外的海龟汤。',
    cover_asset_id: 9,
    cover_url: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="160" height="70"%3E%3Crect width="160" height="70" fill="%232468ac"/%3E%3C/svg%3E',
    competition_color: '#2468AC',
    status: 'ongoing',
    start_time: '2026-08-15T00:00:00Z',
    end_time: '2026-08-20T00:00:00Z',
    score_type: 'average',
    top_n: 10,
    required_tags: ['夏夜', '原创'],
    entry_count: 7,
  },
  random_soups: [
    { id: 1, title: '雨夜来信', puzzle_excerpt: '他收到一封不可能寄出的信。', genre: '本格', soup_color: '清汤', average_score: 8.5, rating_count: 4, author_name: '青山', competition_colors: ['#2468AC'], created_at: '2026-08-15T00:00:00Z' },
    { id: 2, title: '空房间', puzzle_excerpt: '房间里没有人，却传来脚步声。', genre: '变格', soup_color: '红汤', average_score: 7, rating_count: 2, author_name: '海风', competition_colors: [], created_at: '2026-08-14T00:00:00Z' },
    { id: 3, title: '最后一班车', puzzle_excerpt: '他每天都错过同一班车。', genre: '鳖汤', soup_color: '黑汤', average_score: 9, rating_count: 8, author_name: '白昼', competition_colors: [], created_at: '2026-08-13T00:00:00Z' },
    { id: 4, title: '没有影子的人', puzzle_excerpt: '所有人都看见了他，除了镜子。', genre: '未分类', soup_color: '未分类', average_score: 6.5, rating_count: 1, author_name: '月光', competition_colors: [], created_at: '2026-08-12T00:00:00Z' },
  ],
}

async function mockHome(page: Page) {
  await page.route('http://127.0.0.1:10000/api/announcements**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
  }))
  await page.route('http://127.0.0.1:10000/api/home/discovery', route => route.fulfill({ json: discovery }))
}

test('homepage uses a bounded scenery banner with latest competition and random soups', async ({ page }) => {
  test.setTimeout(20_000)
  await page.setViewportSize({ width: 1440, height: 900 })
  await mockHome(page)
  const requestedUrls: string[] = []
  const pageErrors: string[] = []
  page.on('request', request => requestedUrls.push(request.url()))
  page.on('pageerror', error => pageErrors.push(error.message))

  await page.goto('/')

  const banner = page.getByTestId('home-banner')
  await expect(banner).toBeVisible()
  expect(await banner.evaluate(element => element.getBoundingClientRect().height)).toBeLessThanOrEqual(320)
  await expect(page.getByRole('heading', { name: '夏夜推理赛' })).toBeVisible()
  await expect(page.getByRole('heading', { name: '随机推荐' })).toBeVisible()
  await expect(page.getByText('雨夜来信')).toBeVisible()
  await expect(page.getByText('没有影子的人')).toBeVisible()
  expect(requestedUrls.some(url => url.includes('hitokoto'))).toBe(false)
  expect(requestedUrls.filter(url => url.includes('/api/home/discovery'))).toHaveLength(1)
  expect(pageErrors).toEqual([])
  const dimensions = await page.evaluate(() => ({
    clientWidth: document.documentElement.clientWidth,
    scrollWidth: document.documentElement.scrollWidth,
  }))
  expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth)
})

test('mobile sidebar embeds the animated accessible theme switch', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.addInitScript(() => localStorage.setItem('theme_preference', 'light'))
  await mockHome(page)
  const pageErrors: string[] = []
  page.on('pageerror', error => pageErrors.push(error.message))

  await page.goto('/')
  await page.getByRole('button', { name: '打开导航侧栏' }).click()

  const switchControl = page.locator('#theme-toggle-sidebar')
  await expect(switchControl).toBeVisible()
  await expect(switchControl).toHaveAttribute('aria-checked', 'false')
  await expect(switchControl).toHaveAttribute('aria-label', '切换到深色主题')
  await expect(page.getByText('外观主题')).toBeVisible()
  const toggleBox = await switchControl.boundingBox()
  expect(toggleBox?.width).toBeGreaterThanOrEqual(89)
  expect(toggleBox?.height).toBeGreaterThanOrEqual(39)
  await switchControl.click()

  await expect(page.locator('html')).toHaveClass(/dark/)
  await expect(switchControl).toHaveAttribute('aria-checked', 'true')
  await expect(switchControl).toHaveAttribute('aria-label', '切换到浅色主题')
  await expect.poll(() => page.evaluate(() => localStorage.getItem('app-theme'))).toBe('dark')
  await expect(page.locator('html')).not.toHaveAttribute('data-theme-transition')
  await expect(switchControl.locator('.theme-toggle__container')).toHaveCSS('background-color', 'rgb(29, 31, 44)')
  await expect.poll(async () => {
    const transform = await switchControl.locator('.theme-toggle__sun').evaluate(element => getComputedStyle(element).transform)
    return Number(transform.match(/matrix\([^,]+,[^,]+,[^,]+,[^,]+,\s*([^,]+)/)?.[1] || 0)
  }).toBeGreaterThan(45)
  await expect.poll(() => page.locator('html').evaluate(element => element.classList.contains('is-animating'))).toBe(false)
  const drawer = page.locator('.mobile-drawer-panel')
  await expect(drawer).toHaveCSS('border-radius', '24px')

  await page.keyboard.press('Escape')
  await expect(drawer).toHaveCount(0)
  await expect(page.getByRole('button', { name: '打开导航侧栏' })).toBeFocused()
  expect(pageErrors).toEqual([])
})

test('community leaderboard switches between regular and bie soups', async ({ page }) => {
  await page.setViewportSize({ width: 1280, height: 900 })
  await page.route('http://127.0.0.1:10000/api/announcements**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
  }))
  const requestedScopes: string[] = []
  await page.route('http://127.0.0.1:10000/api/turtle-soups**', route => {
    const scope = new URL(route.request().url()).searchParams.get('ranking_scope') || ''
    requestedScopes.push(scope)
    const isBie = scope === 'bie'
    return route.fulfill({
      json: {
        items: [{
          id: isBie ? 22 : 11,
          title: isBie ? '独立鳖汤冠军' : '本格推理冠军',
          puzzle: isBie ? '这碗汤有一点离谱。' : '门明明锁着，人却消失了。',
          genre: isBie ? '鳖汤' : '本格',
          soup_color: isBie ? '黑汤' : '清汤',
          average_score: isBie ? 9.6 : 9.2,
          rating_count: 12,
          like_count: 8,
          competition_colors: [],
          author_uid: 1,
          author: { uid: 1, username: 'author', nickname: '榜首作者' },
        }],
        total: 1,
        page: 1,
        page_size: 50,
        total_pages: 1,
      },
    })
  })

  await page.goto('/leaderboard')
  await expect(page.getByRole('heading', { name: '海龟汤排行榜' })).toBeVisible()
  await expect(page.getByText('本格推理冠军')).toBeVisible()

  await page.getByRole('tab', { name: '鳖汤榜' }).click()
  await expect(page.getByRole('heading', { name: '鳖汤排行榜' })).toBeVisible()
  await expect(page.getByText('独立鳖汤冠军')).toBeVisible()
  expect(requestedScopes).toEqual(['regular', 'bie'])
})

test('notifications can be marked read in one action', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('access_token', 'test-token'))
  await page.route('http://127.0.0.1:10000/api/announcements**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
  }))
  await page.route('http://127.0.0.1:10000/api/auth/me', route => route.fulfill({
    json: {
      uid: 1,
      username: 'reader',
      nickname: '通知读者',
      email: 'reader@example.com',
      role: 'user',
      status: 'active',
      points: 0,
      consecutive_signin_days: 0,
      theme_preference: 'light',
      created_at: '2026-08-15T00:00:00Z',
    },
  }))
  await page.route('http://127.0.0.1:10000/api/users/me/signin', route => route.fulfill({
    json: {
      signed_in: false,
      signin_day: '2026-08-15',
      consecutive_days: 0,
      experience_points: 0,
      experience_gained: 0,
      level: 1,
      level_start: 0,
      next_level_start: 100,
    },
  }))
  await page.route('http://127.0.0.1:10000/api/messages/conversations', route => route.fulfill({
    json: { items: [], total: 0 },
  }))
  await page.route('http://127.0.0.1:10000/api/system-messages**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 1, total_pages: 0 },
  }))
  let readAllRequests = 0
  let readAll = false
  await page.route('http://127.0.0.1:10000/api/notifications**', route => {
    const request = route.request()
    const url = new URL(request.url())
    if (request.method() === 'PUT' && url.pathname.endsWith('/read-all')) {
      readAllRequests += 1
      readAll = true
      return route.fulfill({ json: { updated_count: 2 } })
    }
    const unreadOnly = url.searchParams.get('unread_only') === 'true'
    return route.fulfill({
      json: {
        items: unreadOnly ? [] : [
          { id: 1, recipient_uid: 1, notification_type: 'system', title: '第一条通知', content: '内容', is_read: readAll, created_at: '2026-08-15T00:00:00Z' },
          { id: 2, recipient_uid: 1, notification_type: 'system', title: '第二条通知', content: '内容', is_read: readAll, created_at: '2026-08-14T00:00:00Z' },
        ],
        total: unreadOnly ? (readAll ? 0 : 2) : 2,
        page: 1,
        page_size: unreadOnly ? 1 : 50,
        total_pages: 1,
      },
    })
  })

  await page.goto('/notifications')
  await expect(page.getByText('第一条通知')).toBeVisible()
  await page.getByRole('button', { name: '全部已读' }).click()

  await expect(page.getByText('全部通知已读')).toBeVisible()
  await expect(page.getByText('未读')).toHaveCount(0)
  await expect(page.getByRole('button', { name: '全部已读' })).toHaveCount(0)
  expect(readAllRequests).toBe(1)
})
