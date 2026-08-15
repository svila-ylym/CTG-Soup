# Notification Read-All, Community Leaderboards, and Environment Template Design

## Goal

Extend the version `1.5.0` branch with three focused improvements: authenticated users can mark all notifications read in one action, the community ranking separates ordinary turtle soups from 鳖汤, and a copied `backend/.env.example` is complete and starts with safe local defaults after its secret is configured.

The implementation follows the user's instruction not to use TDD. Focused regression coverage is added after implementation, with no new dependencies or database migration.

## Notification Read-All

Add `PUT /api/notifications/read-all`. The endpoint updates only unread notifications whose `recipient_uid` matches the authenticated user, commits once, and returns `{ "updated_count": number }`. It is idempotent: calling it when nothing is unread returns zero.

The notification page shows “全部已读” beside refresh whenever unread items exist. While the request is running the action is disabled. Success marks the loaded notification objects read immediately and clears the shared navigation red dot without another list fetch; failure leaves the local items unchanged and shows the existing page-level operation error.

## Separate Community Rankings

The existing public soup list remains the source of ranking payloads. It gains an optional `ranking_scope` query with two explicit values:

- `regular`: include public/revealed soups whose genre is not `鳖汤`.
- `bie`: include only public/revealed soups whose genre is `鳖汤`.

Without `ranking_scope`, list and filtering behavior remains unchanged. The existing score ordering and tie breakers continue to apply. The frontend ranking store passes this scope and ignores stale responses when users switch quickly.

The ranking page presents a two-option segmented switch: “海龟汤榜” and “鳖汤榜”. The header title, description, empty-state copy, statistics, podium, and full list all describe the active scope. Switching preserves the layout, shows its loading skeleton, and fetches the selected independent dataset. This is the community ranking only and does not alter competition rankings.

## Environment Template

Compare every `Settings` field used by the application with `backend/.env.example`. Add the missing password-reset expiry setting and keep operationally optional values visibly empty. Replace active fake R2 endpoint/bucket/public URL values with empty defaults so switching to the R2 backend cannot silently use example hosts. Keep the repository name and local service defaults that are genuine project defaults.

Because `Settings` intentionally rejects placeholder `SECRET_KEY` values, initialization scripts must replace the template placeholder with a generated random secret when creating a new `.env`. Existing `.env` files are never overwritten. Document that the template itself is not a deployable secret and that production operators must rotate it.

## Errors, Compatibility, and Verification

- Read-all is scoped by recipient in SQL and cannot affect another user.
- Existing clients that do not send `ranking_scope` see the original list.
- Unknown ranking scopes receive FastAPI validation error `422`.
- Empty rankings render a scoped empty state rather than mixing categories.
- Existing local `.env` and credentials are not read, printed, changed, or committed.
- Verification consists of focused notification/ranking API tests, settings/template validation, a frontend production build, and a small browser/layout smoke check.

