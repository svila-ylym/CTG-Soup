import { expect, test, type Page } from '@playwright/test'

async function mockCompetitionPage(page: Page, onCreate?: (payload: Record<string, unknown>) => void) {
  await page.addInitScript(() => {
    localStorage.setItem('access_token', 'admin-token')
    localStorage.setItem('user_role', 'admin')
  })
  await page.route('http://127.0.0.1:10000/api/announcements**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
  }))
  await page.route('http://127.0.0.1:10000/api/auth/me', route => route.fulfill({
    json: {
      uid: 1,
      username: 'admin',
      nickname: '管理员',
      email: 'admin@example.com',
      role: 'admin',
      status: 'active',
      points: 0,
      consecutive_signin_days: 0,
      created_at: '2026-08-08T00:00:00Z',
    },
  }))
  await page.route('http://127.0.0.1:10000/api/users/me/signin', route => route.fulfill({
    json: {
      signed_in: false,
      signin_day: '2026-08-09',
      consecutive_days: 0,
      experience_points: 0,
      experience_gained: 0,
      level: 1,
      level_start: 0,
      next_level_start: 100,
    },
  }))
  await page.route('http://127.0.0.1:10000/api/tags**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 100, total_pages: 0 },
  }))
  await page.route('http://127.0.0.1:10000/api/competitions', async route => {
    if (route.request().method() !== 'POST') return route.continue()
    const payload = route.request().postDataJSON() as Record<string, unknown>
    onCreate?.(payload)
    return route.fulfill({
      status: 201,
      json: {
        id: 77,
        creator_uid: 1,
        ...payload,
        required_tag_ids: [9],
        status: 'pending',
        result_snapshot: null,
        created_at: '2026-08-09T00:00:00Z',
        updated_at: '2026-08-09T00:00:00Z',
        settled_at: null,
        entries: [],
      },
    })
  })
  await page.route('http://127.0.0.1:10000/api/competitions/77', route => route.fulfill({
    json: {
      id: 77,
      creator_uid: 1,
      name: '夏夜赛',
      description: '说明',
      start_time: '2026-08-10T10:00:00Z',
      end_time: '2026-08-11T10:00:00Z',
      required_tag_ids: [9],
      score_type: 'average',
      top_n: 10,
      custom_page_config: {},
      status: 'pending',
      result_snapshot: null,
      created_at: '2026-08-09T00:00:00Z',
      updated_at: '2026-08-09T00:00:00Z',
      settled_at: null,
      entries: [],
    },
  }))
}

async function fillCompetitionDetails(page: Page) {
  await page.getByLabel('比赛名称').fill('夏夜赛')
  await page.getByLabel('比赛说明').fill('说明')
  await page.getByLabel('开始时间').fill('2026-08-10T10:00')
  await page.getByLabel('结束时间').fill('2026-08-11T10:00')
}

test('custom competition keyword can be removed, deduplicated, and submitted', async ({ page }) => {
  let createPayload: Record<string, any> | null = null
  await mockCompetitionPage(page, payload => { createPayload = payload })
  await page.goto('/competitions/create')
  await fillCompetitionDetails(page)

  const input = page.getByRole('textbox', { name: '新增比赛关键词' })
  await input.fill('夏夜推理')
  await page.getByRole('button', { name: '添加关键词' }).click()
  await expect(page.getByText('#夏夜推理', { exact: true })).toHaveCount(1)
  await page.getByRole('button', { name: '移除关键词 夏夜推理' }).click()
  await expect(page.getByText('#夏夜推理', { exact: true })).toHaveCount(0)

  await input.fill('夏夜推理')
  await input.press('Enter')
  await input.fill('夏夜推理')
  await input.press('Enter')
  await expect(page.getByText('#夏夜推理', { exact: true })).toHaveCount(1)

  await page.getByRole('button', { name: '发布比赛' }).click()
  await expect.poll(() => createPayload).not.toBeNull()
  expect(createPayload?.required_tag_ids).toEqual([])
  expect(createPayload?.custom_tags).toEqual(['夏夜推理'])
  expect(createPayload?.start_time).toBe('2026-08-10T02:00:00.000Z')
  expect(createPayload?.end_time).toBe('2026-08-11T02:00:00.000Z')
})

test('competition requires an existing or custom keyword', async ({ page }) => {
  await mockCompetitionPage(page)
  await page.goto('/competitions/create')
  await fillCompetitionDetails(page)

  await page.getByRole('button', { name: '发布比赛' }).click()

  await expect(page.getByText('请至少选择或新增一个比赛关键词')).toBeVisible()
})
