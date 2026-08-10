# Local Draft Persistence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve unfinished turtle-soup and forum-post forms across page reloads in the same browser, isolated by authenticated UID and cleared after successful publication.

**Architecture:** Add a small typed `localStorage` utility that owns versioned envelope parsing and storage failures. Each form owns its schema validator, meaningful-content rule, restoration, and deep Vue watcher so form-specific behavior remains local.

**Tech Stack:** Vue 3 Composition API, TypeScript, Pinia authentication state, browser `localStorage`, Vite.

## Global Constraints

- Do not add cookies, backend endpoints, or database tables.
- Use UID-scoped keys `ctg:draft:v1:soup:<uid>` and `ctg:draft:v1:post:<uid>`.
- Do not persist drafts when no authenticated or stored UID is available.
- Invalid or unavailable storage must never block typing or publishing.
- Clear a draft only after successful publication or when the form returns to defaults.
- Do not add TDD test files; verify through the production build and browser behavior.

---

### Task 1: Versioned Draft Storage Utility

**Files:**
- Create: `frontend/src/utils/draftStorage.ts`

**Interfaces:**
- Produces: `DraftKind = 'soup' | 'post'`.
- Produces: `draftStorageKey(kind: DraftKind, uid: number | string | null | undefined): string | null`.
- Produces: `readDraft<T>(key: string | null, validate: (value: unknown) => value is T): T | null`.
- Produces: `writeDraft<T>(key: string | null, data: T): void`.
- Produces: `removeDraft(key: string | null): void`.

- [ ] **Step 1: Create the storage utility**

Implement a `DRAFT_VERSION = 1` envelope with `{ version, saved_at, data }`. `draftStorageKey` must reject empty, non-numeric, zero, and negative UIDs. `readDraft` must parse JSON, require version 1, validate `data`, remove malformed records, and return `null` on every storage exception. `writeDraft` and `removeDraft` must be no-ops for a null key and catch storage exceptions.

- [ ] **Step 2: Check the utility for unsafe payloads**

Confirm the utility stores only caller-provided form data and never imports or serializes access tokens, refresh tokens, passwords, or the complete auth user object.

### Task 2: Turtle-Soup Draft Restoration

**Files:**
- Modify: `frontend/src/views/SoupCreateView.vue`

**Interfaces:**
- Consumes: all four functions from `frontend/src/utils/draftStorage.ts`.
- Produces: a local `SoupDraft` matching every existing `formData` property.

- [ ] **Step 1: Define and validate the soup draft shape**

Add `SoupDraft`, `snapshotSoupDraft()`, `isSoupDraft(value)`, and `hasSoupDraft(value)`. Validate all strings and booleans, require `tag_ids` to contain only finite numbers, require `custom_tags` to contain only strings, and restrict genre/soup-color strings to the options already accepted by the form.

- [ ] **Step 2: Restore before registering the watcher**

Build the key from `authStore.user?.uid ?? localStorage.getItem('user_uid')`. Read the record and use `Object.assign(formData, restored)` before registering the watcher, ensuring arrays are copied rather than shared with the parsed object.

- [ ] **Step 3: Persist meaningful soup changes**

Import Vue `watch`. Deep-watch `formData`; write `snapshotSoupDraft()` when `hasSoupDraft` is true and remove the record when all fields match defaults.

- [ ] **Step 4: Clear only after successful publication**

Immediately after `createSoup` resolves, call `removeDraft(soupDraftKey)` before showing the success toast and navigating. Leave the draft untouched for validation errors and request failures.

### Task 3: Forum-Post Draft Restoration

**Files:**
- Modify: `frontend/src/views/PostListView.vue`

**Interfaces:**
- Consumes: all four functions from `frontend/src/utils/draftStorage.ts`.
- Consumes: `useAuthStore()` for the current UID, with stored `user_uid` as initialization fallback.
- Produces: local `PostDraft = { title: string; content: string; section: string }`.

- [ ] **Step 1: Define and validate the post draft shape**

Add `isPostDraft(value)` and `hasPostDraft(value)`. Require exactly usable string fields; consider title/content text or a section other than `general` meaningful.

- [ ] **Step 2: Restore and reopen the composer**

Read the UID-scoped post record during setup. Assign a copied object to `draft.value`, and set `composerOpen.value = true` when the restored draft is meaningful.

- [ ] **Step 3: Persist post changes**

Import Vue `watch` and deep-watch `draft`. Write meaningful data and remove the record when the form is at defaults. Closing the composer must not mutate the draft or remove storage.

- [ ] **Step 4: Clear after successful publication**

After the POST request resolves, reset `draft.value` to defaults and call `removeDraft(postDraftKey)` before closing the composer. Failed requests retain the stored record.

### Task 4: Verification

**Files:**
- Verify: `frontend/src/utils/draftStorage.ts`
- Verify: `frontend/src/views/SoupCreateView.vue`
- Verify: `frontend/src/views/PostListView.vue`

**Interfaces:**
- Consumes: the completed browser-facing implementation from Tasks 1-3.
- Produces: build and browser evidence for the handoff.

- [ ] **Step 1: Run whitespace and production checks**

Run `git diff --check -- project/CTG` from `/root`, then run `npm run build` from `frontend`. Require both commands to exit 0.

- [ ] **Step 2: Verify storage utility behavior in a browser context**

Open the running frontend, authenticate, enter every soup field, reload, and confirm all values return. Replace the soup storage value with malformed JSON and confirm the page loads with defaults rather than throwing.

- [ ] **Step 3: Verify post restoration and cleanup**

Enter post title, section, and content, reload, and confirm the composer opens with all values. Close and reopen the composer to confirm the draft remains. Publish successfully, reload, and confirm the composer no longer restores that draft.

- [ ] **Step 4: Recheck running services**

Require HTTP 200 from `http://127.0.0.1:10000/posts`, `http://127.0.0.1:10000/soups/create`, and `http://127.0.0.1:10001/health`. Report Elasticsearch degradation separately if the backend health payload remains degraded.
