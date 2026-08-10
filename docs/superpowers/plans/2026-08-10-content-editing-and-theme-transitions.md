# Content Editing And Theme Transitions Implementation Plan

> **For agentic workers:** Implement this plan inline in the existing PR worktree. The user explicitly requested no TDD and no browser testing.

**Goal:** Let competition creators edit their competitions, preserve authored whitespace across competitions, soups and posts, and polish the affected comment and homepage transitions.

**Architecture:** Reuse the competition creation form for editing and add an owner-checked update endpoint. Keep whitespace validation separate from persistence so blank-only input is rejected while original values are stored. Use the browser View Transition API with a CSS fallback for theme changes, and CSS interpolation for homepage time scenes.

**Tech Stack:** FastAPI, SQLModel, Pydantic, Vue 3, TypeScript, Tailwind CSS.

## Global Constraints

- No database migration.
- Do not run browser tests.
- Preserve original spaces and line breaks; use trimming only for blank checks.
- Keep changes on the existing PR branch.

---

### Task 1: Competition editing

**Files:** `backend/app/api/competitions.py`, `backend/app/schemas/competitions.py`, `frontend/src/views/CompetitionCreateView.vue`, `frontend/src/views/CompetitionDetailView.vue`, `frontend/src/router/index.ts`, `frontend/src/types/index.ts`

- [x] Add an update schema and `PUT /competitions/{id}` endpoint restricted to the creator.
- [x] Reuse image, HTML, tag and time validation for create and update.
- [x] Add an edit route, populate the existing form, submit updates, and expose an edit button to the creator.

### Task 2: Whitespace preservation

**Files:** `backend/app/services/safe_html.py`, `backend/app/api/posts.py`, `backend/app/schemas/community.py`, `backend/app/api/turtle_soups.py`, post and soup Vue views

- [x] Remove persistence-time trimming while retaining blank-only validation.
- [x] Ensure rich competition content displays authored whitespace.

### Task 3: UI fixes and transitions

**Files:** `frontend/src/views/PostDetailView.vue`, `frontend/src/views/HomeView.vue`, `frontend/src/utils/theme.ts`, `frontend/src/assets/main.css`

- [x] Group comment author and level badge so flex spacing does not separate them.
- [x] Make the secondary hero button scene-aware in dark mode.
- [x] Add directional theme reveal animations and smoother time-scene interpolation with reduced-motion handling.

### Task 4: Verification and delivery

- [x] Run backend compilation, frontend production build and `git diff --check`.
- [ ] Review the diff, commit, push the existing PR branch, and sync changed source files to the server without restarting it.
