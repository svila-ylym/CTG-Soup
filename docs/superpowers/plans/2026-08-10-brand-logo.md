# Brand Logo Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose the repository `icon.ico` as the browser favicon and the shared desktop/mobile navigation brand mark.

**Architecture:** Keep the icon as an unmodified Vite public asset at `frontend/public/icon.ico`. Reference it from `frontend/index.html` and reuse the same `/icon.ico` URL in both `NavBar.vue` brand locations, with existing responsive and dark-mode classes preserved.

**Tech Stack:** Vue 3, Vite, Tailwind CSS, existing `NavBar.vue` component.

## Global Constraints

- Do not change API contracts, authentication, database schema, or migrations.
- Do not crop or filter the source icon; render it with `object-contain`.
- Keep the brand link keyboard accessible and linked to `/`.
- Do not run browser tests; verify with `git diff --check` and `npm run build`.

---

### Task 1: Add The Public Icon Asset

**Files:**
- Create: `frontend/public/icon.ico`
- Source: repository-root `icon.ico`

**Interfaces:**
- Produces: `/icon.ico` for Vite static serving and all consumers in later tasks.

- [ ] **Step 1: Confirm the source asset**

Run:

```bash
test -f icon.ico
```

Expected: exit code `0`. If the repository-root file is absent, obtain the exact existing file from the deployment source; do not generate a replacement.

- [ ] **Step 2: Copy the asset without conversion**

Run:

```bash
mkdir -p frontend/public
cp icon.ico frontend/public/icon.ico
```

Expected: `frontend/public/icon.ico` exists and retains the source file type.

- [ ] **Step 3: Check the asset is not empty**

Run:

```bash
file frontend/public/icon.ico
```

Expected: output identifies an ICO image.

### Task 2: Wire The Browser Favicon

**Files:**
- Modify: `frontend/index.html:4-9`

**Interfaces:**
- Consumes: `/icon.ico` from Task 1.
- Produces: browser favicon metadata with no runtime code changes.

- [ ] **Step 1: Add the favicon link**

Add this inside `<head>`:

```html
<link rel="icon" href="/icon.ico" type="image/x-icon" />
```

- [ ] **Step 2: Check the HTML reference**

Run:

```bash
rg -n 'icon\.ico' frontend/index.html
```

Expected: exactly one favicon reference.

### Task 3: Update Desktop And Mobile Branding

**Files:**
- Modify: `frontend/src/components/NavBar.vue:1-10`
- Modify: `frontend/src/components/NavBar.vue:88-100`

**Interfaces:**
- Consumes: `/icon.ico` from Task 1.
- Produces: desktop and mobile brand links that both navigate to `/`.

- [ ] **Step 1: Replace the desktop text-only brand**

Use an accessible link with a fixed icon box:

```vue
<router-link to="/" class="flex shrink-0 items-center gap-2 text-lg font-bold text-gray-800 dark:text-white sm:text-xl">
  <img src="/icon.ico" alt="汤吧社区图标" class="h-8 w-8 object-contain" />
  <span>汤吧社区</span>
</router-link>
```

- [ ] **Step 2: Reuse the brand in the mobile drawer header**

Replace the current title-only block with the same icon and label, keeping the existing subtitle and close button layout:

```vue
<div class="flex min-w-0 items-center gap-2">
  <img src="/icon.ico" alt="汤吧社区图标" class="h-8 w-8 shrink-0 object-contain" />
  <div class="min-w-0">
    <p class="truncate text-lg font-bold text-slate-900 dark:text-white">汤吧社区</p>
    <p class="mt-0.5 text-xs text-slate-500">完整导航</p>
  </div>
</div>
```

- [ ] **Step 3: Confirm no duplicate navigation behavior changed**

Run:

```bash
rg -n 'router-link to="/"|icon\.ico|汤吧社区' frontend/src/components/NavBar.vue
```

Expected: both brand locations contain `/icon.ico`, and existing route links remain unchanged.

### Task 4: Verify And Commit

**Files:**
- Verify: `frontend/public/icon.ico`, `frontend/index.html`, `frontend/src/components/NavBar.vue`

- [ ] **Step 1: Run whitespace validation**

Run: `git diff --check`

Expected: no output and exit code `0`.

- [ ] **Step 2: Run the frontend production build**

Run: `cd frontend && npm run build`

Expected: `vue-tsc` and Vite finish with exit code `0`.

- [ ] **Step 3: Commit the implementation**

Run:

```bash
git add frontend/public/icon.ico frontend/index.html frontend/src/components/NavBar.vue
git commit -m "feat: add shared brand logo"
```

Expected: one implementation commit containing only the logo asset and frontend wiring.
