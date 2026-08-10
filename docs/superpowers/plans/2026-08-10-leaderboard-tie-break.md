# Leaderboard Tie-Break Implementation Plan

> **For agentic workers:** Implement inline in this session; do not add a TDD workflow because the project owner explicitly requested the smallest direct change.

**Goal:** Make higher-rated-count soups rank first when average scores are equal.

**Architecture:** Keep ranking in the existing SQLAlchemy/SQLModel query used by `GET /turtle-soups?sort_by=score`. Add `rating_count` and deterministic timestamp/id tie-breakers after average score; leave all response and frontend code unchanged.

**Tech Stack:** FastAPI, SQLModel/SQLAlchemy, PostgreSQL-compatible query expressions.

## Global Constraints

- No database schema or migration changes.
- No visible scoring-rule text in the frontend.
- Preserve the existing published/revealed soup filter and pagination.

### Task 1: Update score ordering

**Files:**
- Modify: `backend/app/api/turtle_soups.py:379-387`

**Interfaces:**
- Consumes: the existing `sort_by` query parameter and `Soup` model fields `avg_rating`, `rating_count`, `created_at`, and `id`.
- Produces: a stable SQL ordering for score-sorted soup pages.

- [ ] **Step 1: Add the ordering keys**

Change the score branch from a single expression to:

```python
select(
    Soup.avg_rating.desc(),
    Soup.rating_count.desc(),
    Soup.created_at.desc(),
    Soup.id.desc(),
)
```

Keep the other sort branches unchanged.

- [ ] **Step 2: Run verification**

Run:

```bash
PYTHONPATH=backend /tmp/ctg-verify-venv/bin/python -m pytest -q
python3 -m compileall -q backend/app
git diff --check
```

Expected: the existing test suite passes, Python compilation succeeds, and no whitespace errors are reported.

- [ ] **Step 3: Commit**

```bash
git add backend/app/api/turtle_soups.py docs/superpowers/specs/2026-08-10-leaderboard-tie-break-design.md docs/superpowers/plans/2026-08-10-leaderboard-tie-break.md
git commit -m "fix: prioritize rating count for tied soups"
```
