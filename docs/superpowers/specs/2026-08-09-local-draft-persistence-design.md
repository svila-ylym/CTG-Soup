# Local Draft Persistence Design

## Scope

Preserve unfinished turtle-soup and forum-post forms when the page reloads in the same browser. Drafts remain frontend-only; no backend API, database table, or cookie is added.

## Storage And Isolation

Use `localStorage` because form bodies can exceed cookie limits and must not be attached to HTTP requests. Store separate versioned records for each content type and authenticated UID:

- `ctg:draft:v1:soup:<uid>`
- `ctg:draft:v1:post:<uid>`

The UID comes from the authenticated user or the existing `user_uid` local-storage entry while authentication is initializing. When no UID is available, the form continues to work but is not persisted, preventing an anonymous draft from leaking to the next account on a shared browser.

Each record contains a schema version, save time, and form data. Soup drafts include the title, puzzle, solution, genre, soup color, player counts, selected tag IDs, custom tags, and reveal setting. Post drafts include the title, section, and content.

## Save, Restore, And Clear Rules

Register a deep Vue watcher after attempting restoration. A meaningful change writes the complete current form record synchronously, so an immediate refresh cannot lose the last input. Returning a form to all defaults removes its record.

On component creation, parse and validate the stored record before assigning it to reactive form state. Invalid JSON, an unsupported schema version, or fields with invalid types are discarded without breaking the page. A restored post automatically opens the post composer.

Publishing successfully removes the matching draft. Validation errors, request failures, page navigation, refreshes, and closing the post composer preserve it. Soup and post drafts never share a storage key.

## Components

Add a small `draftStorage` utility for safe JSON parsing, version checks, writes, and removals. `SoupCreateView.vue` and `PostListView.vue` define their own field validators and meaningful-content checks, then use the shared utility from their existing form lifecycle. This keeps storage mechanics centralized while leaving form-specific rules beside each form.

## Failure Handling And Privacy

Storage access is wrapped in `try/catch`; unavailable or full browser storage must not block typing or publishing. Drafts contain user-authored content, never access tokens or passwords. UID-scoped keys prevent normal account switching from restoring another user's draft on the same browser.

## Verification

Verify production TypeScript/Vite compilation, then exercise both forms in a browser: enter all supported fields, reload, confirm restoration, publish, reload again, and confirm the draft was cleared. Also verify malformed storage data is ignored and a post draft reopens the composer.
