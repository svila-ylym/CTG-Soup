# Content Editing, Soup UX, Account Lifecycle, and Moderation Design

## Goal

Add author-only editing for turtle soups and forum posts, preserve turtle-soup
text exactly as entered, and let each soup attach public puzzle images and
spoiler-protected solution images. Correct soup-list navigation and metadata,
make private-message identities navigable, expire abandoned registrations with
deterministic UID reuse, and expose safe punishment revocation from user
management.

## Confirmed Behavior

- Soup titles remain required.
- Puzzle and solution are validated independently. Each must contain either
  non-whitespace text or at least one attached image.
- Puzzle and solution text is stored byte-for-byte as submitted, including
  leading and trailing spaces, indentation, and blank lines. Validation may
  inspect `value.strip()` but must never store the stripped result.
- Puzzle and solution each allow at most five images.
- Puzzle images are public. Solution images are omitted from API responses
  until the caller explicitly requests the revealed solution, matching the
  existing solution-text behavior.
- Only the original author may update a soup or post. This rule also applies
  to admin and root users. Existing moderation and delete permissions remain
  unchanged.
- Soup comment counts are independent from rating counts. The count matches
  the existing comment-list `total`: published top-level comments only.
- Implementation will not use a test-first TDD cycle. Verification and focused
  regression coverage are added after implementation.
- The soup list requests 30 rows per page and shows a next-page control only
  when the API reports a later page. A full final page must not expose a broken
  next-page action.
- The soup tag filter loads every active tag from the existing tags API instead
  of using hard-coded placeholder labels. Selections are submitted by `tag_id`.
- Clicking the other participant's avatar in either the conversation list or
  active private-message header opens `/profile/:uid`.
- Accounts still in `pending_email` 30 minutes after `users.created_at` are
  deleted. Cleanup runs at startup and then every minute in the API process.
- Deleted pending-account UIDs enter a persistent reuse pool. Registration
  advances the next normal allocation on every registration but prefers the
  smallest released UID, producing `3,4,5,6,15,16` in the confirmed example.
- Admin and root users may review reports, create competitions, and revoke
  status punishments within their existing role hierarchy. An admin may revoke
  a regular user's ban or silence, but may not operate on self, another admin,
  or root.

## Data Model

Add a `SoupImage` SQLModel table rather than storing asset identifiers in a
JSON column. Each row contains:

- `id`: primary key.
- `soup_id`: indexed foreign key to `soups.id`.
- `asset_id`: indexed foreign key to `uploaded_assets.id`.
- `placement`: `puzzle` or `solution`.
- `sort_order`: zero-based display order within the placement.
- `created_at`: creation timestamp.

The table has unique constraints for `(soup_id, asset_id)` and
`(soup_id, placement, sort_order)`. An uploaded image can therefore appear at
most once in a soup, and display order cannot collide within one section.

The existing authenticated `POST /api/uploads/images` endpoint remains the
only binary upload entry point. Removing an image from a soup removes only the
`SoupImage` relation. It does not delete the `UploadedAsset` row or public
object because that asset may be reused as an avatar or in another soup.
Images uploaded before a cancelled form submission remain in the owner's
image library.

The new table is created by the existing `SQLModel.metadata.create_all()`
startup path. No existing soup rows need backfilling.

Add two small account-allocation tables:

- `UserUidAllocator` is a singleton row containing the next normal UID. It is
  initialized from the current maximum user UID and advanced for every
  registration, including registrations that receive a released UID.
- `ReusableUserUid` contains only UIDs released by deletion of expired pending
  accounts. It never infers reusable values by scanning arbitrary holes in the
  users table.

The distinction is required because normal values skipped while a released UID
is assigned are consumed allocations, not newly reusable holes. Allocator
advance and pool removal occur in the same registration transaction.
PostgreSQL uses a transaction-scoped advisory lock to serialize allocation and
cleanup; SQLite uses the same table contract for local verification.

## API Contract

`SoupCreate` accepts:

- `puzzle: str = ""`
- `solution: str = ""`
- `puzzle_image_ids: list[int] = []`
- `solution_image_ids: list[int] = []`

`SoupUpdate` accepts optional versions of the same fields. Update validation
uses the effective stored text and image relations after applying the patch,
so a request cannot remove the last remaining content from puzzle or solution.

For both create and update, the backend:

1. Rejects duplicate image identifiers and more than five images per section.
2. Requires every referenced asset to exist, have `kind="image"`, and belong
   to the authenticated author.
3. Validates the text-or-image requirement without normalizing stored text.
4. Synchronizes `SoupImage` rows in the requested order in the same database
   transaction as the soup and tag changes.

`SoupResponse` adds:

- `puzzle_images: list[UploadedAssetResponse]`
- `solution_images: list[UploadedAssetResponse]`
- `comment_count: int`
- `can_edit: bool`

Puzzle images are returned in `sort_order`. Solution images are returned only
when the existing reveal decision allows the solution; otherwise the field is
an empty list. This prevents spoiler URLs from leaking through JSON while the
frontend is still hiding the solution.

Soup update authorization becomes strictly `soup.author_uid == current_user.uid`.
`can_edit` follows the same rule. Existing `can_manage` semantics remain for
delete and moderation controls.

Comment counts are computed from published top-level `Comment` rows targeting
the soup. List responses load counts for the page in one grouped query, while
single-soup responses query only that soup. The value is not stored on `Soup`,
so historical comments are correct without a data migration and ratings can
never affect it. The soup-list comment icon binds to `comment_count`; rating
surfaces continue binding to `rating_count`.

`PostResponse` also adds `can_edit`. Post list and detail routes calculate it
from the optional authenticated user. Post update authorization becomes
strictly `post.author_uid == current_user.uid`; delete authorization is not
changed.

The existing tag list endpoint remains the source of active filter options.
The frontend follows all pages at `page_size=100`, keeps the API's usage-count
ordering, and submits `tag_id` to the soup list endpoint. A tag-loading failure
leaves the all-tags option available and does not block soup loading.

## Frontend Structure

Extract the current soup fields into a reusable `SoupEditorForm` component.
It owns field validation, selected image state, image previews, upload progress,
placement limits, removal, and ordering. It emits a complete `SoupCreate`
payload but does not call create or update APIs itself.

`SoupCreateView` keeps draft persistence and calls the create API.
`SoupEditView` loads the revealed soup, initializes the same editor, and calls
the update API. Routes add `/soups/:id/edit`, protected by authentication.
The view redirects or displays an authorization error when `can_edit` is
false, while the backend remains the security boundary.

Each puzzle and solution image control uses the existing image upload API,
shows uncropped previews, supports removal and left/right ordering, and
disables further selection at five images. Failed uploads leave the rest of
the form intact. Removing a preview before submission only removes its
association from the pending payload.

Soup draft storage includes the selected puzzle and solution asset IDs. On
restore, the view resolves those IDs against the user's uploaded image list
and drops IDs that no longer exist or no longer belong to the user.

The soup submit path continues using trimmed values only for emptiness checks.
It sends `puzzle` and `solution` directly without `.trim()`. Detail rendering
keeps `whitespace-pre-wrap`; puzzle images render below puzzle text, and
solution images render below solution text only after reveal. Images link to
their original public URL and use responsive, non-cropping dimensions.

Add `PostEditView` at `/posts/:id/edit`. It loads the post, edits title,
section, and content, and calls a new `postsApi.update` wrapper. Soup and post
detail pages show an edit icon button only when `can_edit` is true. Long edit
forms use full pages rather than modals so they remain usable on mobile.

`SoupListView` stores returned page metadata, requests 30 rows, and renders the
next button only while `currentPage < totalPages`. The document remains the
scroll container, so 30 cards do not introduce a nested scrolling region.

`MessageView` makes both visible representations of the other user's avatar
navigate to the existing profile route without also selecting or closing the
conversation unexpectedly.

## Pending Account Lifecycle

At startup the application creates the allocation tables, immediately removes
expired pending accounts, then starts one asynchronous loop that repeats every
60 seconds. Shutdown cancels and awaits that loop. Multiple Uvicorn processes
may each start a loop; the shared PostgreSQL advisory lock makes cleanup
idempotent and prevents overlap with UID allocation.

Cleanup uses `User.created_at <= now - 30 minutes`, not the most recent resend
timestamp, so resending a verification message does not extend account life.
It locks verification records before the user row, rechecks status and cutoff,
deletes all `EmailVerification` rows, records the UID in `ReusableUserUid`, and
then deletes the user in one transaction. This ordering prevents a successful
verification racing with deletion. Legacy pending users already past the
cutoff are handled by the first startup pass.

Registration acquires the same allocation lock, advances the singleton normal
UID, removes the smallest released UID when one exists, and explicitly assigns
the chosen UID to the new `User`. Failed registration transactions restore a
removed pool row, while the durable allocator continues to provide unique
normal values.

## Moderation Permissions

The existing report decision and competition creation routes already use the
admin-or-root dependency and retain that behavior. Regression checks make this
contract explicit.

Punishment revocation changes from root-only to admin-or-root. Before revoking,
the backend reloads the actor and target under the existing moderation locks,
rejects self-management, and applies `can_manage_role`: ordinary admins can
revoke punishments affecting regular users, while only root can manage admin
targets. Revocation continues to update the punishment record, derive the user
status from remaining active punishments, increment token version when status
changes, write an operation log, and notify the affected user.

The user-management row locates the active punishment corresponding to the
displayed `banned` or `silenced` status. It requires a two-character revocation
reason and invokes the same endpoint used by the punishment-history tab. When
both ban and silence are active, revoking the ban correctly reveals the
remaining silenced status and then offers `解除禁言`.

## Error Handling

- Empty text plus no images for either soup section returns a structured 422
  validation error.
- Missing, non-image, or foreign-owned assets return 422 without changing the
  soup.
- Updates by anyone except the author return 403, including admin and root.
- Upload errors are shown beside the relevant image section and do not clear
  text or successful image selections.
- A failed create or update keeps the editor populated for correction.
- Failure to load dynamic tag options does not block soup-list results.
- Cleanup logs an error and retries on the next interval rather than stopping
  the API process.
- Revocation returns 403 when an ordinary admin targets self, an admin, or root.

## Verification

After implementation, run focused backend checks covering exact whitespace
persistence, image-only puzzle/solution validation, asset ownership, hidden
solution image responses, ordered associations, and author-only soup/post
updates. Run the complete frontend type-check/build and exercise create, edit,
reveal, unauthorized edit, and responsive image layouts in the browser.

Also verify exact 30-item pagination boundaries, dynamic tag selection by ID,
both private-message avatar links, startup plus periodic pending-account
cleanup, the confirmed UID allocation sequence, concurrent allocation safety,
and ordinary-admin report review, competition creation, and regular-user
punishment revocation.

## Out of Scope

- Image attachments for forum posts.
- Rich text or Markdown editing for soup text.
- Automatic deletion of uploaded image objects.
- Changing delete authorization or moderation permissions beyond the confirmed
  ordinary-admin revocation capability.
- Reusing arbitrary historical UID holes that were not released by pending
  account cleanup.
- Moving cleanup into an external cron job or standalone worker.
- Allowing ordinary administrators to manage peer administrators or root.
