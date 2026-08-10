# Comment Mention Suggestions Design

## Goal

Let users mention another account from any position inside a comment or reply, with an autocomplete menu that inserts a valid `@username ` token. Manually typed tokens must produce the same mention notification and email without requiring a reply relationship.

## Mention Syntax

- A mention token is `@username` followed by whitespace.
- The `@` may appear at the start of text or immediately after any character, including Chinese text and punctuation.
- The trailing whitespace is required; it can be a normal space, newline, or other whitespace.
- Only an exact existing username creates a mention. Mentioning oneself is ignored by the existing synchronization service.
- The parser rule applies everywhere `sync_mentions` is already used, including post bodies and comments.

## Candidate Input

- Create one reusable `MentionTextarea` Vue component.
- Use it for root comments and replies in both post details and turtle-soup details.
- Detect the unfinished `@query` immediately before the current caret, regardless of where it appears in the sentence.
- Search through the existing user search API after at least one query character.
- Show username, nickname, and avatar when available, with at most eight candidates.
- Support mouse selection, Up/Down navigation, Enter or Tab selection, and Escape dismissal.
- Selecting a candidate replaces only the active `@query`, inserts `@username `, and restores the caret after the trailing space.
- Plain typing remains authoritative; submitting never depends on a selected candidate or a reply parent.

## Backend And Notifications

- Update the shared mention parser instead of adding special comment-only parsing.
- Keep existing `sync_mentions`, notification delivery, email delivery, mention offset storage, and reply-notification deduplication unchanged.
- No database or API response schema changes are required.

## Failure Handling And Verification

- A failed suggestion search closes the candidate menu and never blocks comment submission.
- Empty or unmatched manual tokens remain ordinary text.
- Run focused parser checks for start, middle, punctuation-adjacent, multiple, missing-space, and end-of-text cases without adding a TDD cycle.
- Run backend compile, `git diff --check`, and the frontend production build.
- Do not run browser tests.
