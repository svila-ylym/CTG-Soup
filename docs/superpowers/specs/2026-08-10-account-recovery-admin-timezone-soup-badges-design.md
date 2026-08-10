# Account Recovery, Pending User Administration, Message Timezone, and Soup Badges Design

## Scope

- Let root users delete accounts whose status is `pending_email` from the existing user-management table.
- Add a complete forgot-password flow that verifies mailbox ownership through an emailed reset link.
- Render private-message timestamps in UTC+8 regardless of the browser's local timezone.
- Show turtle-soup genre and color badges in the soup list, soup detail, and homepage popular-soup cards.

## Backend Design

Password reset reuses the existing SMTP service and JWT secret. `POST /auth/reset-password-request` accepts an email address and always returns a generic response so account existence is not disclosed. For an existing non-pending user, it sends a signed `password_reset` JWT containing the UID and current `token_version`; the token expires after 30 minutes. `POST /auth/reset-password` validates the token purpose, expiry, user, and token version before hashing the new password and incrementing `token_version`. This invalidates existing sessions and all previously issued reset links without adding a database table or migration.

`DELETE /admin/users/{uid}/pending` requires `get_current_root_user`. It locks UID allocation, locks the selected user, verifies that the current status is still `pending_email`, deletes email-verification records, inserts the UID into `reusable_user_uids`, records an operation log, and commits atomically. A non-pending target returns a conflict response.

## Frontend Design

The login page links to `/forgot-password`. That page submits an email address and displays the backend's generic response. The reset email links to `/reset-password?token=...`; the page validates password confirmation and calls the reset endpoint. Both routes are guest-only.

The user-management table shows a destructive delete button only when the signed-in user is root and the row is `pending_email`. It requires a browser confirmation and reloads management data after success.

Private messages parse timezone-less API timestamps as UTC and format both the conversation list and message bubbles using `Asia/Shanghai`. Soup metadata uses shared compact badge-style helpers so list, detail, and homepage colors stay consistent.

## Error Handling And Verification

- Password-reset request responses remain generic; rate limits and SMTP failures use the existing API error format.
- Invalid, expired, already-consumed, or stale reset tokens return a single invalid-or-expired message.
- Pending-user deletion rechecks the target under a database lock to avoid deleting an account that was verified concurrently.
- Per user instruction, no TDD or browser automation is added. Verification consists of backend compilation/import checks, the frontend production build, `git diff --check`, and a final diff review.
