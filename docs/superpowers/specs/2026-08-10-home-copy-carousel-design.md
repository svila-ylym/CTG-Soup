# Home Copy Carousel Design

## Goal

Replace the fixed homepage introduction with a rotating set of lines read from the repository-root `home.txt` file.

## Content Source

- `home.txt` remains at the repository root and contains one sentence per line.
- The backend reads the file on every request so server-side edits become visible after a page refresh without rebuilding the frontend.
- Empty lines are ignored and surrounding whitespace is removed.
- A missing, unreadable, or empty file falls back to the current homepage sentence instead of breaking the page.

## API And Frontend

- Add a public `GET /api/home/lines` endpoint returning `{ "lines": string[] }`.
- The homepage requests the lines during mount and starts from the first sentence.
- When multiple lines exist, the homepage advances in source order every six seconds and loops back to the first line.
- The text uses a short opacity and vertical-translation transition. Reduced-motion users receive an immediate text change without animation.
- Clear the interval when the homepage unmounts.

## Scope And Verification

- No database models, migrations, authentication, or admin controls change.
- Verify backend syntax with `python3 -m compileall -q backend/app`.
- Verify whitespace with `git diff --check`.
- Verify the frontend with `npm run build`; do not run browser tests.
