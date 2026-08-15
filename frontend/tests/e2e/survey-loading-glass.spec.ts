import { expect, test, type Page } from '@playwright/test'


async function mockAnnouncements(page: Page) {
  await page.route('http://127.0.0.1:10000/api/announcements**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
  }))
  await page.route('http://127.0.0.1:10000/api/version', route => route.fulfill({
    json: { version: '1.5.0' },
  }))
}


test('survey list shows skeletons before rendering glass cards', async ({ page }) => {
  await mockAnnouncements(page)
  let releaseResponse!: () => void
  const responseGate = new Promise<void>((resolve) => { releaseResponse = resolve })
  await page.route('http://127.0.0.1:10000/api/surveys**', async (route) => {
    if (new URL(route.request().url()).pathname !== '/api/surveys') return route.continue()
    await responseGate
    await route.fulfill({
      json: {
        items: [{
          id: 7,
          title: '社区体验调查',
          description: '告诉我们你的体验',
          status: 'active',
          starts_at: null,
          expires_at: null,
          notification_sent: true,
          author_uid: 1,
          created_at: '2026-08-15T00:00:00Z',
          updated_at: '2026-08-15T00:00:00Z',
          question_count: 3,
          response_count: 8,
        }],
        total: 1,
        page: 1,
        page_size: 20,
        total_pages: 1,
      },
    })
  })

  await page.goto('/surveys', { waitUntil: 'domcontentloaded' })
  await expect(page.locator('.skeleton-block').first()).toBeVisible()
  releaseResponse()

  const card = page.locator('.glass-card-interactive')
  await expect(card).toContainText('社区体验调查')
  await expect(card).toHaveCSS('border-radius', '12px')
  await expect(page.locator('.skeleton-block')).toHaveCount(0)
})


test('survey detail uses has_submitted without requesting statistics', async ({ page }) => {
  await mockAnnouncements(page)
  const requestedPaths: string[] = []
  page.on('request', request => requestedPaths.push(new URL(request.url()).pathname))
  await page.route('http://127.0.0.1:10000/api/surveys/7', route => route.fulfill({
    json: {
      id: 7,
      title: '社区体验调查',
      description: '已提交状态来自详情接口',
      status: 'active',
      starts_at: null,
      expires_at: null,
      notification_sent: true,
      author_uid: 1,
      created_at: '2026-08-15T00:00:00Z',
      updated_at: '2026-08-15T00:00:00Z',
      has_submitted: true,
      questions: [],
    },
  }))

  await page.goto('/surveys/7')

  await expect(page.getByText('您已完成此问卷')).toBeVisible()
  await expect(page.getByRole('button', { name: '提交问卷' })).toBeDisabled()
  expect(requestedPaths.some(path => path.endsWith('/statistics'))).toBe(false)
})


test('dark profile overlay is black and blurred', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('theme_preference', 'dark'))
  await mockAnnouncements(page)
  await page.route('http://127.0.0.1:10000/api/users/42/profile**', route => route.fulfill({
    json: {
      user: {
        uid: 42,
        username: 'night-user',
        nickname: '暗色用户',
        avatar_url: null,
        profile_background_url: 'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="32" height="32"%3E%3Crect width="32" height="32" fill="%231d4ed8"/%3E%3C/svg%3E',
        bio: null,
        role: 'user',
        permission_groups: [],
        level: 1,
        level_band: '新手',
        experience_points: 0,
        level_start: 0,
        next_level_start: 100,
        registration_date: '2026-08-15',
        created_at: '2026-08-15T00:00:00Z',
      },
      stats: { post_count: 0, soup_count: 0, follower_count: 0, following_count: 0, like_received: 0 },
      relation: { is_self: false, is_following: false, is_friend: false, is_blocked: false },
      featured_soups: [],
      soups: { items: [], total: 0, page: 1, page_size: 20, total_pages: 0 },
    },
  }))
  await page.route('http://127.0.0.1:10000/api/collections**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 10, total_pages: 0 },
  }))

  await page.goto('/profile/42')
  const overlay = page.locator('.profile-hero-overlay')
  await expect(overlay).toBeVisible()
  const styles = await overlay.evaluate((element) => {
    const style = getComputedStyle(element)
    return { backgroundImage: style.backgroundImage, backdropFilter: style.backdropFilter }
  })

  expect(styles.backgroundImage).toContain('rgba(0, 0, 0')
  expect(styles.backdropFilter).toContain('blur(10px)')
})
