import { expect, test, type Page } from '@playwright/test'

const baseSoup = {
  id: 42,
  title: '可以更改的评分',
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

test('rating slider supports a first score and later replacement', async ({ page }) => {
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
  await expect(page.getByRole('dialog')).toContainText('保存后仍可')
  await page.getByRole('button', { name: '确认并提交' }).click()

  await expect(slider).toBeEnabled()
  await expect(page.getByText('当前评分 8.5 分，可随时调整')).toBeVisible()
  await expect(page.getByRole('button', { name: '修改评分' })).toBeDisabled()

  await slider.fill('7')
  await page.getByRole('button', { name: '修改评分' }).click()
  await expect(page.getByRole('dialog')).toContainText('从 8.5 分 修改为 7.0 分')
  await page.getByRole('button', { name: '确认修改' }).click()

  await expect(slider).toBeEnabled()
  await expect(slider).toHaveValue('7')
  await expect(page.getByText('当前评分 7.0 分，可随时调整')).toBeVisible()
  expect(ratingRequests).toEqual([8.5, 7])
})

test('historical rating is editable on first render', async ({ page }) => {
  const ratingRequests: number[] = []
  let myRating = 7.5
  await mockSharedRoutes(page)
  await page.route('**/api/turtle-soups/42**', route => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname
    if (pathname.endsWith('/comments')) {
      return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 50, total_pages: 0 } })
    }
    if (pathname.endsWith('/rating') && request.method() === 'PUT') {
      myRating = (request.postDataJSON() as { score: number }).score
      ratingRequests.push(myRating)
      return route.fulfill({ json: { average_score: myRating, rating_count: 1, my_rating: myRating } })
    }
    return route.fulfill({ json: { ...baseSoup, average_score: myRating, rating_count: 1, my_rating: myRating } })
  })

  await page.goto('/soups/42')

  const slider = page.getByRole('slider', { name: '评分' })
  await expect(slider).toHaveValue('7.5')
  await expect(slider).toBeEnabled()
  await expect(page.getByText('当前评分 7.5 分，可随时调整')).toBeVisible()
  await expect(page.getByRole('button', { name: '修改评分' })).toBeDisabled()

  await slider.fill('9')
  await page.getByRole('button', { name: '修改评分' }).click()
  await page.getByRole('button', { name: '确认修改' }).click()
  await expect(page.getByText('当前评分 9.0 分，可随时调整')).toBeVisible()
  expect(ratingRequests).toEqual([9])
})

test('failed rating update keeps the selected score available for retry', async ({ page }) => {
  await mockSharedRoutes(page)
  await page.route('**/api/turtle-soups/42**', route => {
    const request = route.request()
    const pathname = new URL(request.url()).pathname
    if (pathname.endsWith('/comments')) {
      return route.fulfill({ json: { items: [], total: 0, page: 1, page_size: 50, total_pages: 0 } })
    }
    if (pathname.endsWith('/rating') && request.method() === 'PUT') {
      return route.fulfill({
        status: 503,
        json: { detail: { code: 'TEMPORARY_FAILURE', message: '评分暂时保存失败' } },
      })
    }
    return route.fulfill({ json: { ...baseSoup, average_score: 6.5, rating_count: 1, my_rating: 6.5 } })
  })

  await page.goto('/soups/42')
  const slider = page.getByRole('slider', { name: '评分' })
  await slider.fill('9')
  await page.getByRole('button', { name: '修改评分' }).click()
  await page.getByRole('button', { name: '确认修改' }).click()

  await expect(page.getByRole('dialog')).toContainText('评分暂时保存失败')
  await page.getByRole('button', { name: '取消' }).click()
  await expect(slider).toHaveValue('9')
})
