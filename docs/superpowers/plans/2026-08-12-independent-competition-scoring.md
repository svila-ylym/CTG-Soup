# Independent Competition Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add private organizer scoring for competitions, opened at one configured date and published only when every entry is scored and the competition is settled.

**Architecture:** Store the scoring schedule on `Competition` and private judge metadata on `CompetitionEntry`, while retaining `final_score` and `result_snapshot` as the public frozen result. Public ranking code returns no live independent rankings; protected organizer endpoints expose and update judge scores. Settlement copies complete private scores into the existing ranking snapshot flow.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, PostgreSQL/SQLite migration tests, Pydantic v2, Vue 3 Composition API, TypeScript, Vue Router, Tailwind CSS.

## Global Constraints

- Do not use TDD; implement first, then add and run focused regression coverage.
- Independent scores are 1 through 10 inclusive in 0.5 increments.
- `scoring_at` is a single opening timestamp and must be no earlier than `end_time`.
- Only the competition creator or an administrator may inspect or modify private judge scores.
- Every entry must be scored before settlement; an absent score is never treated as zero.
- Public clients see no independent score or ranking before settlement.
- Ties remain ordered by soup creation time ascending, then soup ID ascending.
- Existing competitions remain average-scored without data rewriting.

---

## File Map

- `backend/app/models/models.py`: independent score enum and persisted schedule/judge fields.
- `backend/app/migrations/competition_judging.py`: idempotent schema additions.
- `backend/app/migrations/social_platform.py`: invokes the new migration during `--phase all`.
- `backend/app/schemas/competitions.py`: create/update validation and protected judging payloads.
- `backend/app/services/competition_entries.py`: private ranking source selection and settlement guards.
- `backend/app/api/competitions.py`: public privacy boundary and organizer judging endpoints.
- `backend/tests/test_competition_judging_migration.py`: migration execution/idempotency.
- `backend/tests/test_competition_contract.py`: permissions, privacy, validation and settlement behavior.
- `frontend/src/types/index.ts`: independent scoring types and judging workbench contracts.
- `frontend/src/views/CompetitionCreateView.vue`: scoring mode and scoring date input.
- `frontend/src/views/CompetitionEditView.vue`: loads and edits scoring configuration.
- `frontend/src/views/CompetitionDetailView.vue`: public waiting state and authorized judging entry point.
- `frontend/src/views/CompetitionJudgingView.vue`: protected score-entry workbench.
- `frontend/src/router/index.ts`: judging route.

---

### Task 1: Persist Independent Scoring Configuration

**Files:**
- Modify: `backend/app/models/models.py`
- Create: `backend/app/migrations/competition_judging.py`
- Modify: `backend/app/migrations/social_platform.py`
- Create: `backend/tests/test_competition_judging_migration.py`

**Interfaces:**
- Produces: `CompetitionScoreType.INDEPENDENT`, `Competition.scoring_at`, `CompetitionEntry.judge_score`, `CompetitionEntry.judged_by_uid`, and `CompetitionEntry.judged_at`.
- Produces: `ensure_competition_judging_schema(engine: Engine = default_engine, dry_run: bool = False) -> CompetitionJudgingMigrationReport`.

- [ ] **Step 1: Extend the SQLModel entities**

Add the enum value and nullable fields. Use a nullable foreign key column with `ondelete="SET NULL"` for `judged_by_uid`; do not change the default score type.

- [ ] **Step 2: Add the idempotent migration**

Inspect `competitions` and `competition_entries`, report exact pending actions, and execute PostgreSQL/SQLite-compatible `ALTER TABLE` statements. Add the foreign key where supported without rebuilding existing SQLite tables; tests only require columns under SQLite and production PostgreSQL receives the constraint.

- [ ] **Step 3: Register the migration**

Call `ensure_competition_judging_schema()` from foundation before application code relies on the new columns, and concatenate its actions into the existing report.

- [ ] **Step 4: Add post-implementation migration tests**

Cover dry-run without mutation, first execution creating all four columns, and a second execution returning no actions.

- [ ] **Step 5: Run focused migration verification**

Run: `PYTHONPATH=backend python -m pytest -q backend/tests/test_competition_judging_migration.py`

Expected: all tests pass.

- [ ] **Step 6: Commit**

```bash
git add backend/app/models/models.py backend/app/migrations/competition_judging.py backend/app/migrations/social_platform.py backend/tests/test_competition_judging_migration.py
git commit -m "feat: persist independent competition scores"
```

### Task 2: Enforce Judging Rules and Privacy in the Backend

**Files:**
- Modify: `backend/app/schemas/competitions.py`
- Modify: `backend/app/services/competition_entries.py`
- Modify: `backend/app/api/competitions.py`
- Modify: `backend/tests/test_competition_contract.py`

**Interfaces:**
- Consumes: persisted fields from Task 1.
- Produces: `CompetitionJudgeScoreUpdate(score: float)`, `CompetitionJudgingEntryResponse`, and `CompetitionJudgingResponse`.
- Produces endpoints `GET /api/competitions/{competition_id}/judging` and `PUT /api/competitions/{competition_id}/entries/{entry_id}/judge-score`.
- Produces stable error codes `INDEPENDENT_SCORING_NOT_OPEN`, `INDEPENDENT_SCORING_INCOMPLETE`, `INDEPENDENT_SCORING_LOCKED`, `NOT_INDEPENDENT_COMPETITION`, and `COMPETITION_ENTRY_NOT_FOUND`.

- [ ] **Step 1: Expand competition schemas and validation**

Accept `average | independent`, normalize `scoring_at` to naive UTC using the existing UTC+8 behavior for naive inputs, require it for independent mode, reject it for average mode, and require `scoring_at >= end_time`. Add the protected judging response types and validate score with the existing half-step rule.

- [ ] **Step 2: Make ranking score sources explicit**

Update `_competition_ranking_rows()` to use public soup averages for average competitions and `judge_score` only while settling independent competitions. Make `competition_rankings()` return an empty total/groups payload for unsettled independent competitions. Keep snapshots unchanged after settlement.

- [ ] **Step 3: Enforce independent settlement completeness**

Under the existing collection lock, verify `scoring_at` has arrived and every entry has `judge_score`. Raise a typed exception containing the missing count. Copy all judge scores to `final_score` before building rankings and committing the snapshot.

- [ ] **Step 4: Add protected judging endpoints**

Authorize the creator or any admin role using the authenticated admin-capable dependency plus explicit owner handling. Return private score metadata only from `/judging`. On PUT, enforce mode, opening date, unsettled state, entry ownership and score validation, then update `judge_score`, `judged_by_uid`, and `judged_at` in one transaction.

- [ ] **Step 5: Protect edits after judging begins**

When any entry has a judge score, reject changes to mode, dates or required/optional tags with `INDEPENDENT_SCORING_LOCKED`. Permit name, description, color and `top_n` edits without deleting/recollecting entries. Preserve legacy clients that omit new optional fields during average competition edits.

- [ ] **Step 6: Add post-implementation contract coverage**

Add focused cases for create/update date validation, creator/admin/non-owner permissions, early scoring rejection, score range and half-step validation, overwriting metadata, public privacy, ignoring soup averages, incomplete settlement, completed independent rankings, optional group rankings, stable tie order, and edit locking.

- [ ] **Step 7: Run focused backend verification**

Run: `PYTHONPATH=backend python -m pytest -q backend/tests/test_competition_contract.py backend/tests/test_competition_judging_migration.py`

Expected: all tests pass.

- [ ] **Step 8: Commit**

```bash
git add backend/app/schemas/competitions.py backend/app/services/competition_entries.py backend/app/api/competitions.py backend/tests/test_competition_contract.py
git commit -m "feat: add organizer-only competition judging"
```

### Task 3: Add Independent Scoring Controls and Workbench

**Files:**
- Modify: `frontend/src/types/index.ts`
- Modify: `frontend/src/views/CompetitionCreateView.vue`
- Modify: `frontend/src/views/CompetitionEditView.vue`
- Modify: `frontend/src/views/CompetitionDetailView.vue`
- Create: `frontend/src/views/CompetitionJudgingView.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: backend response properties `score_type`, `scoring_at`, `settled_at`, and protected judging endpoints from Task 2.
- Produces: route `/competitions/:id/judging` and typed `CompetitionJudging` payloads.

- [ ] **Step 1: Expand frontend types**

Use `CompetitionScoreType = 'average' | 'independent'`, add nullable `scoring_at` to competition/create/update contracts, and define judging entry/progress types without adding judge data to public `CompetitionEntry`.

- [ ] **Step 2: Add create controls**

Replace the read-only average label with a compact segmented radio control. Show the UTC+8 `datetime-local` scoring input only for independent mode, validate it is at or after the ending timestamp, and send its UTC ISO value or `null`.

- [ ] **Step 3: Add edit controls**

Load mode and scoring date, reuse create validation/copy, and surface backend locking errors. Do not reset the saved mode to average when loading an independent competition.

- [ ] **Step 4: Add the judging workbench**

Create a utilitarian table listing soup title, author UID, 1–10 half-step numeric input, save status and last update metadata. Fetch only the protected judging endpoint, save rows individually, display `scored_count / total_count`, and disable editing after settlement or before opening time.

- [ ] **Step 5: Update public competition detail**

Display “平均分” or “独评” and the scoring date. For unsettled independent competitions show entries without score/rank columns and a waiting message. Show the judging link only to the creator/admin; settled output continues using public rankings.

- [ ] **Step 6: Register the route**

Lazy-load `CompetitionJudgingView.vue`, require authentication, and let the backend remain the authority for owner/admin permission.

- [ ] **Step 7: Run frontend verification**

Run: `cd frontend && npm run build`

Expected: Vue type-check and Vite production build succeed.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types/index.ts frontend/src/views/CompetitionCreateView.vue frontend/src/views/CompetitionEditView.vue frontend/src/views/CompetitionDetailView.vue frontend/src/views/CompetitionJudgingView.vue frontend/src/router/index.ts
git commit -m "feat: add independent judging workbench"
```

### Task 4: Final Verification and Delivery

**Files:**
- Verify only; fix scoped defects in files from Tasks 1–3 if found.

**Interfaces:**
- Consumes: complete independent-scoring feature.
- Produces: a reviewable branch and deployable migration/build evidence.

- [ ] **Step 1: Run backend focused tests**

Run: `PYTHONPATH=backend python -m pytest -q backend/tests/test_competition_contract.py backend/tests/test_competition_judging_migration.py backend/tests/test_database_backup.py`

Expected: all tests pass.

- [ ] **Step 2: Run frontend and static checks**

Run: `cd frontend && npm run build`

Run: `python -m py_compile backend/app/models/models.py backend/app/migrations/competition_judging.py backend/app/schemas/competitions.py backend/app/services/competition_entries.py backend/app/api/competitions.py`

Run: `bash -n Update.sh && git diff --check`

Expected: every command exits zero.

- [ ] **Step 3: Inspect the final diff and migration path**

Confirm no private judge fields appear in public competition response schemas, migration is registered once, legacy average competitions have no required new input, and the branch version remains `1.4.1` unless separately requested.

- [ ] **Step 4: Commit any verification fixes**

```bash
git add <scoped-files>
git commit -m "fix: harden independent competition scoring"
```

- [ ] **Step 5: Push and update the existing pull request**

Push `codex/soup-collections-1-4-0` and confirm the open PR head matches local HEAD. Do not deploy production unless the user explicitly requests it after reviewing this feature.
