# Brand Logo Integration Design

## Goal

Use the repository-root `icon.ico` as the shared CTG brand mark in the browser chrome and the application navigation.

## Scope

- Copy the existing `icon.ico` into `frontend/public/icon.ico` so Vite serves it without bundling or transforming the file.
- Add a favicon link in `frontend/index.html`.
- Update the desktop `NavBar` brand link to show the icon followed by `汤吧社区`.
- Update the mobile navigation drawer header to use the same icon and label.
- Keep routes, API contracts, authentication, database schema, and theme behavior unchanged.

## Visual And Accessibility Rules

- Use a fixed square image box with `object-contain`; the source image must not be cropped.
- Keep the brand link keyboard accessible and retain the existing home link target.
- Provide descriptive `alt` text for the navigation image and an empty alt for the favicon.
- Use existing dark-mode text classes; do not apply color filters or text shadows to the logo.

## Verification

- Confirm the asset exists in `frontend/public` and is referenced by `index.html`.
- Run `git diff --check`.
- Run the frontend production build with `npm run build`.
