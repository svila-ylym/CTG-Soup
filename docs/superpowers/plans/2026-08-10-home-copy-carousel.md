# Home Copy Carousel Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Serve the root `home.txt` lines through a public endpoint and rotate them in the homepage introduction.

**Architecture:** Add a small read-only FastAPI router that resolves the repository-root `home.txt`, strips blank lines, and returns a fallback line when the file cannot be read. `HomeView.vue` fetches that payload on mount and cycles the current line on a six-second interval with a lightweight transition.

**Tech Stack:** FastAPI, pathlib, Vue 3 Composition API, Vue transitions, Vite.

## Global Constraints

- `home.txt` remains at the repository root and contains one sentence per line.
- No database models, migrations, authentication, or admin controls change.
- Missing or empty content falls back to the existing homepage sentence.
- Do not run browser tests; verify with backend compile, `git diff --check`, and `npm run build`.

---

### Task 1: Bring The Root Copy Into The Branch

**Files:**
- Create: `home.txt`

**Interfaces:**
- Produces: the repository-root content read by the backend endpoint.

- [ ] **Step 1: Download the exact server copy**

Run:

```bash
sshpass -p 'dswbPRFP5666' sftp root@154.40.43.131
get /www/wwwroot/ctg/home.txt home.txt
```

Expected: local `home.txt` matches the already-authored remote file, with one sentence per line.

- [ ] **Step 2: Inspect line format**

Run: `sed -n '1,40p' home.txt`

Expected: each non-empty line is one carousel item; do not rewrite the text.

### Task 2: Add The Home Copy API

**Files:**
- Create: `backend/app/api/home.py`
- Modify: `backend/app/main.py`

**Interfaces:**
- Produces: `GET /api/home/lines` returning `{ "lines": list[str] }`.

- [ ] **Step 1: Implement the read-only router**

Use `Path(__file__).resolve().parents[3] / "home.txt"`, read UTF-8 text, keep `line.strip()` values that are non-empty, and return the fallback list `["一碗汤，一群人，一场从“为什么”开始的推理冒险。读故事、问线索、把藏起来的真相一点点拼完整。"]` when reading fails or yields no lines.

- [ ] **Step 2: Register the router**

Import `home` in `backend/app/main.py` and add:

```python
app.include_router(home.router, prefix="/api/home", tags=["首页"])
```

- [ ] **Step 3: Compile the backend**

Run: `python3 -m compileall -q backend/app`

Expected: exit code `0`.

### Task 3: Rotate Copy In The Homepage

**Files:**
- Modify: `frontend/src/views/HomeView.vue`

**Interfaces:**
- Consumes: `GET /api/home/lines`.
- Produces: first-line display on mount, six-second looping rotation, and cleanup on unmount.

- [ ] **Step 1: Replace the static paragraph text**

Wrap the displayed line in a Vue `<Transition name="hero-copy-carousel" mode="out-in">` and bind a stable key to the current index.

- [ ] **Step 2: Load and rotate lines**

Add a fallback constant, `ref` state for lines/index, a `fetch('/api/home/lines')` loader, and a `window.setInterval` started on mount only when there are at least two lines. Clear the interval in `onBeforeUnmount`.

- [ ] **Step 3: Add a lightweight transition**

Define scoped `.hero-copy-carousel-enter-active` and leave-active transitions using only `opacity` and `transform`, plus a reduced-motion override with no transition.

### Task 4: Verify, Commit, And Deploy

**Files:**
- Verify: `home.txt`, `backend/app/api/home.py`, `backend/app/main.py`, `frontend/src/views/HomeView.vue`

- [ ] **Step 1: Run checks**

Run:

```bash
git diff --check
python3 -m compileall -q backend/app
cd frontend && npm run build
```

Expected: all commands exit `0`.

- [ ] **Step 2: Commit**

Run: `git add home.txt backend/app/api/home.py backend/app/main.py frontend/src/views/HomeView.vue && git commit -m "feat: rotate homepage copy from home.txt"`

- [ ] **Step 3: Push and synchronize the same four source files**

Push the current branch to the existing PR, then upload `home.txt`, the new backend router, `backend/app/main.py`, and `frontend/src/views/HomeView.vue` to `/www/wwwroot/ctg` without restarting or migrating.
