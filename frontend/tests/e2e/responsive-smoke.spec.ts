import { expect, test } from '@playwright/test'

const routes = [
  '/',
  '/login',
  '/register',
  '/verify-email',
  '/soups',
  '/leaderboard',
  '/posts',
  '/competitions',
  '/search',
]

const viewports = [
  { width: 375, height: 812 },
  { width: 768, height: 1024 },
  { width: 1440, height: 900 },
]

for (const viewport of viewports) {
  test.describe(`${viewport.width}px viewport`, () => {
    test.use({ viewport })

    for (const route of routes) {
      test(`${route} loads without page errors or horizontal overflow`, async ({ page }) => {
        const pageErrors: string[] = []
        page.on('pageerror', error => pageErrors.push(error.message))
        if (route === '/soups') {
          await page.route('http://127.0.0.1:10000/api/announcements**', request => request.fulfill({
            json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
          }))
          await page.route('http://127.0.0.1:10000/api/turtle-soups**', request => request.fulfill({
            json: { items: [], total: 0, page: 1, page_size: 30, total_pages: 0 },
          }))
          await page.route('http://127.0.0.1:10000/api/tags**', request => request.fulfill({
            json: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
          }))
        }

        const response = await page.goto(route, { waitUntil: 'networkidle' })

        expect(response?.ok()).toBe(true)
        await expect(page.locator('#app')).toBeVisible()
        expect(await page.title()).toContain('Turtle Soup')
        expect(pageErrors).toEqual([])
        const dimensions = await page.evaluate(() => ({
          clientWidth: document.documentElement.clientWidth,
          scrollWidth: document.documentElement.scrollWidth,
        }))
        expect(dimensions.scrollWidth).toBeLessThanOrEqual(dimensions.clientWidth)
      })
    }
  })
}

test('soup people fields are text and the solution reveals only after a click', async ({ page }) => {
  const pageErrors: string[] = []
  page.on('pageerror', error => pageErrors.push(error.message))
  await page.addInitScript(() => localStorage.setItem('access_token', 'test-token'))
  await page.route('**/api/auth/me', route => route.fulfill({
    json: {
      uid: 1,
      username: 'author',
      nickname: '作者',
      email: 'author@example.com',
      role: 'user',
      status: 'active',
      points: 0,
      consecutive_signin_days: 0,
      created_at: '2026-08-08T00:00:00Z',
    },
  }))
  await page.route('http://127.0.0.1:10000/api/tags**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
  }))
  await page.route('http://127.0.0.1:10000/api/announcements**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
  }))

  await page.goto('/soups/create', { waitUntil: 'networkidle' })

  const mainPeople = page.getByLabel(/主要人数/)
  const secondaryPeople = page.getByLabel(/次要人数/)
  await expect(mainPeople).toHaveAttribute('type', 'text')
  await expect(secondaryPeople).toHaveAttribute('type', 'text')
  await mainPeople.fill('一群人')
  await secondaryPeople.fill('影子和一只猫')
  await expect(mainPeople).toHaveValue('一群人')
  await expect(secondaryPeople).toHaveValue('影子和一只猫')

  const soupPayload = {
    id: 7,
    title: '密室',
    puzzle: '门从里面锁着。',
    puzzle_images: [],
    solution_images: [],
    solution_available: true,
    is_solution_public: true,
    genre: '本格',
    soup_color: '清汤',
    main_player_count: '一人',
    secondary_player_count: '无人',
    tags: [],
    author_uid: 1,
    author: { uid: 1, username: 'author', nickname: '作者' },
    average_score: 0,
    rating_count: 0,
    comment_count: 0,
    like_count: 0,
    favorite_count: 0,
    view_count: 1,
    status: 'published',
    is_liked: false,
    is_favorited: false,
    my_rating: null,
    can_manage: false,
    can_edit: true,
    created_at: '2026-08-08T00:00:00Z',
    updated_at: '2026-08-08T00:00:00Z',
  }
  await page.route('**/api/turtle-soups/7**', route => {
    const url = new URL(route.request().url())
    if (url.pathname.endsWith('/comments')) {
      return route.fulfill({
        json: { items: [], total: 0, page: 1, page_size: 50, total_pages: 0 },
      })
    }
    const revealed = url.searchParams.get('reveal') === 'true'
    return route.fulfill({
      json: { ...soupPayload, solution: revealed ? '凶手从窗户离开。' : null },
    })
  })

  await page.goto('/soups/7')
  await expect(page.getByText('汤底已隐藏，确认后才会显示。')).toBeVisible()
  await page.getByRole('button', { name: '揭示汤底' }).click()
  await expect(page.getByText('凶手从窗户离开。')).toBeVisible()
  await expect(page.getByText('汤底已隐藏，确认后才会显示。')).toHaveCount(0)
  expect(pageErrors).toEqual([])
})

test('a verified email token is not submitted twice', async ({ page }) => {
  const token = 'verification-token-value-at-least-32-characters'
  let verificationRequests = 0
  await page.route('http://127.0.0.1:10000/api/announcements**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
  }))
  await page.route('http://127.0.0.1:10000/api/auth/verify-email', route => {
    verificationRequests += 1
    return route.fulfill({
      status: verificationRequests === 1 ? 200 : 400,
      json: verificationRequests === 1
        ? { message: '邮箱验证成功，请登录' }
        : { detail: { code: 'VERIFICATION_EXPIRED', message: '验证链接已过期' } },
    })
  })

  await page.goto(`/verify-email?token=${token}`)
  await expect(page.getByText('邮箱验证成功，请登录')).toBeVisible()
  await page.getByRole('button', { name: '验证邮箱' }).click()
  await page.waitForTimeout(200)

  expect(verificationRequests).toBe(1)
  await expect(page.getByText('验证链接已过期')).toHaveCount(0)
})
