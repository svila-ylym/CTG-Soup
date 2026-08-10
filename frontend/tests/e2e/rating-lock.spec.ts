import { expect, test, type Page } from '@playwright/test'

const baseSoup = {
  id: 42,
  title: '不可更改的评分',
  puzzle: '谜面',
  solution: null,
  solution_available: true,
  is_solution_public: true,
  genre: '本格',
  soup_color: '清汤',
  main_player_count: '一人',
  secondary_player_count: '无人',
  tags: [],
  author_uid: 7,
  author: { uid: 7, username: 'author', nickname: '作者' },
  average_score: 0,
  rating_count: 0,
  like_count: 0,
  favorite_count: 0,
  view_count: 1,
  status: 'published',
  is_liked: false,
  is_favorited: false,
  my_rating: null as number | null,
  can_manage: false,
  created_at: '2026-08-08T00:00:00Z',
  updated_at: '2026-08-08T00:00:00Z',
}

async function mockSharedRoutes(page: Page) {
  await page.route('http://127.0.0.1:10000/api/announcements**', route => route.fulfill({
    json: { items: [], total: 0, page: 1, page_size: 5, total_pages: 0 },
  }))
}

test('rating slider submits only after irreversible confirmation and then locks', async ({ page }) => {
  const ratingRequests: number[] = []
  let soup = { ...baseSoup }
  await mockSharedRoutes(page)
  await page.route('**/api/turtle-soups/42**', async route => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname
    if (pathname.endsWith('/comments')) {
      return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 50, total_pages: 0 } })
    }
    if (pathname.endsWith('/rating') && request.method() === 'PUT') {
      const body = request.postDataJSON() as { score: number }
      ratingRequests.push(body.score)
      soup = { ...soup, average_score: body.score, rating_count: 1, my_rating: body.score }
      return route.fulfill({
        json: { average_score: body.score, rating_count: 1, my_rating: body.score },
      })
    }
    return route.fulfill({ json: soup })
  })

  await page.goto('/soups/42')

  const slider = page.getByRole('slider', { name: '评分' })
  await expect(slider).toHaveAttribute('min', '1')
  await expect(slider).toHaveAttribute('max', '10')
  await expect(slider).toHaveAttribute('step', '0.5')
  await expect(slider).toHaveValue('5')
  await slider.fill('8.5')
  expect(ratingRequests).toEqual([])

  await page.getByRole('button', { name: '确认评分' }).click()
  await expect(page.getByRole('dialog')).toContainText('8.5')
  await expect(page.getByRole('dialog')).toContainText('提交后不可修改')
  await page.getByRole('button', { name: '取消' }).click()
  expect(ratingRequests).toEqual([])

  await page.getByRole('button', { name: '确认评分' }).click()
  await page.getByRole('button', { name: '确认并提交' }).click()
  await expect(slider).toBeDisabled()
  await expect(page.getByText('已评分 8.5 分，评分已锁定')).toBeVisible()
  expect(ratingRequests).toEqual([8.5])
})

test('historical rating is locked on first render', async ({ page }) => {
  await mockSharedRoutes(page)
  await page.route('**/api/turtle-soups/42**', route => {
    const pathname = new URL(route.request().url()).pathname
    if (pathname.endsWith('/comments')) {
      return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 50, total_pages: 0 } })
    }
    return route.fulfill({ json: { ...baseSoup, my_rating: 7.5 } })
  })

  await page.goto('/soups/42')

  const slider = page.getByRole('slider', { name: '评分' })
  await expect(slider).toHaveValue('7.5')
  await expect(slider).toBeDisabled()
  await expect(page.getByText('已评分 7.5 分，评分已锁定')).toBeVisible()
  await expect(page.getByRole('button', { name: '确认评分' })).toHaveCount(0)
})

test('rating conflict reloads and locks the server value', async ({ page }) => {
  let serverRating: number | null = null
  await mockSharedRoutes(page)
  await page.route('**/api/turtle-soups/42**', route => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname
    if (pathname.endsWith('/comments')) {
      return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 50, total_pages: 0 } })
    }
    if (pathname.endsWith('/rating') && request.method() === 'PUT') {
      serverRating = 6.5
      return route.fulfill({
        status: 409,
        json: {
          detail: {
            code: 'RATING_ALREADY_SUBMITTED',
            message: '评分确认后不可修改',
          },
        },
      })
    }
    return route.fulfill({ json: { ...baseSoup, my_rating: serverRating } })
  })

  await page.goto('/soups/42')
  const slider = page.getByRole('slider', { name: '评分' })
  await slider.fill('9')
  await page.getByRole('button', { name: '确认评分' }).click()
  await page.getByRole('button', { name: '确认并提交' }).click()

  await expect(slider).toHaveValue('6.5')
  await expect(slider).toBeDisabled()
  await expect(page.getByText('已评分 6.5 分，评分已锁定')).toBeVisible()
})
