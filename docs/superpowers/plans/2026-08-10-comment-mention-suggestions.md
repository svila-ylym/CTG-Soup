# Comment Mention Suggestions Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add autocomplete mention input to comment/reply forms and recognize manually typed `@username ` tokens at any text position.

**Architecture:** Keep mention synchronization server-side and change only its shared token boundary regex. Add a reusable Vue textarea wrapper that searches existing users around the active caret token and inserts a username plus trailing space; wire that component into the four comment/reply inputs.

**Tech Stack:** Python `re`, existing FastAPI mention service, Vue 3 Composition API, existing `searchApi.users`, Tailwind CSS.

## Global Constraints

- The mention token is `@username` followed by whitespace.
- The `@` may follow any character; the trailing whitespace is required.
- Manual text and selected candidates use the same backend parser and notification/email path.
- No database, API response schema, or migration changes.
- Do not run browser tests or add a TDD cycle; verify with focused parser checks, backend compile, `git diff --check`, and frontend build.

---

### Task 1: Fix Shared Mention Parsing

**Files:**
- Modify: `backend/app/services/mentions.py:19`

**Interfaces:**
- Produces: `parse_mentions(text)` matches `@username ` at the start or after any character, while not matching missing trailing whitespace.

- [ ] **Step 1: Change the token regex**

Replace the leading-boundary expression with a pattern equivalent to:

```python
MENTION_RE = re.compile(r"@([^\s@]+)(?=\s)")
```

Keep the existing parsed offsets and synchronization behavior unchanged.

- [ ] **Step 2: Run focused parser checks**

Use the project Python environment when available and assert these cases: `@alice `, `你好@alice `, `你好，@alice 再见`, two mentions in one sentence, `@alice` without a trailing space, and `@unknown `.

Expected: only syntactically valid tokens are parsed; unknown users remain filtered by `sync_mentions`.

### Task 2: Build The Reusable Mention Textarea

**Files:**
- Create: `frontend/src/components/MentionTextarea.vue`

**Interfaces:**
- Consumes: `v-model`, `maxlength`, `placeholder`, `aria-label`, and optional compact sizing.
- Produces: native textarea value/input events plus candidate selection that inserts `@username ` at the active caret.

- [ ] **Step 1: Track the active token**

On input, inspect text before `selectionStart` with `/@([^\s@]*)$/u`; hide the menu when no unfinished token exists or the query is empty.

- [ ] **Step 2: Query users**

Debounce `searchApi.users(query, 1, 8)` by about 160ms, ignore stale responses with a request sequence, and close the menu on failure.

- [ ] **Step 3: Support selection**

Render a positioned candidate list with avatar, nickname, and `@username`; support click, Up/Down, Enter, Tab, and Escape. Replace only the active token and restore the caret after the inserted trailing space.

- [ ] **Step 4: Keep the control accessible and mobile-safe**

Use a real `<textarea>`, keep the list keyboard reachable, give candidate buttons descriptive labels, and make the dropdown width fit narrow screens.

### Task 3: Wire Comment And Reply Forms

**Files:**
- Modify: `frontend/src/views/PostDetailView.vue`
- Modify: `frontend/src/views/SoupDetailView.vue`

**Interfaces:**
- Consumes: `MentionTextarea` from Task 2.
- Produces: candidate support for root comments and replies in both detail pages; submit handlers continue sending plain text and existing `parent_id` values.

- [ ] **Step 1: Replace the four native textareas**

Use `MentionTextarea` for `commentText` and `replyText`, preserving each existing `v-model`, maxlength, placeholder, aria-label, and compact height.

- [ ] **Step 2: Preserve reply behavior**

Keep `startReply` prefill behavior and ensure selecting another candidate does not clear or change `replyParentId`.

- [ ] **Step 3: Confirm submit paths**

Verify both pages still call their existing `createComment` methods with the final text and optional parent id.

### Task 4: Verify, Commit, And Push

**Files:**
- Verify: `backend/app/services/mentions.py`, `frontend/src/components/MentionTextarea.vue`, both detail views.

- [ ] **Step 1: Run checks**

Run:

```bash
git diff --check
python3 -m compileall -q backend/app
cd frontend && npm run build
```

Expected: all exit with code `0`; do not run browser tests.

- [ ] **Step 2: Commit**

Run:

```bash
git add backend/app/services/mentions.py frontend/src/components/MentionTextarea.vue frontend/src/views/PostDetailView.vue frontend/src/views/SoupDetailView.vue
git commit -m "feat: add comment mention suggestions"
```

- [ ] **Step 3: Push the existing PR branch**

Push the branch using the repository PAT without creating a new PR.
