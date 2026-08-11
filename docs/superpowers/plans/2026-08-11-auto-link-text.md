# Precise HTTP/HTTPS Auto-Linking Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Render complete, valid HTTP/HTTPS URLs in user-authored plain text as safe external links throughout the frontend.

**Architecture:** A pure TypeScript parser produces text/link segments without HTML generation. A small Vue component renders those segments, while `MentionText` applies stored mention offsets first and delegates only ordinary text segments to the link renderer. Existing sanitized rich-HTML pipelines and link-wrapped list cards stay unchanged.

**Tech Stack:** Vue 3, TypeScript, native `URL`, Vite, Node assertions.

## Global Constraints

- Only complete `http://` and `https://` URLs with valid non-empty hostnames become links.
- Protocol-only fragments, malformed authorities, and candidates embedded in ASCII words remain text.
- Sentence punctuation and unmatched closing brackets are excluded from href values.
- Rendering must not use `v-html`.
- Links use `target="_blank"` and `rel="noopener noreferrer nofollow ugc"`.
- Existing rich HTML and already linked card surfaces are not reprocessed.
- Update PR #13 only; do not connect to or modify the deployment server.

---

### Task 1: Parser And Shared Renderer

**Files:**
- Create: `frontend/src/utils/linkifyText.ts`
- Create: `frontend/src/components/LinkifiedText.vue`
- Create: `frontend/scripts/check-linkify.mjs`

**Interfaces:**
- Produces `TextLinkSegment = { type: 'text' | 'link'; text: string; href?: string }`.
- Produces `linkifyText(text: string): TextLinkSegment[]`.
- Produces `<LinkifiedText :text="value" />`.

- [ ] Implement scanning, URL validation, boundary validation, punctuation trimming, and unmatched bracket trimming in the pure parser.
- [ ] Render parser segments with interpolation and safe `<a>` attributes in `LinkifiedText.vue`.
- [ ] Add a focused Node assertion script covering domains, ports, paths, query/fragment, Chinese adjacency, punctuation, brackets, protocol fragments, malformed hosts, non-HTTP schemes, and embedded candidates.
- [ ] Run `node --experimental-strip-types scripts/check-linkify.mjs` from `frontend` and confirm every assertion passes.

### Task 2: Mentions And Plain-Text Surfaces

**Files:**
- Modify: `frontend/src/components/MentionText.vue`
- Modify: plain-text views under `frontend/src/views/`
- Modify: `frontend/src/App.vue`

**Interfaces:**
- Consumes `<LinkifiedText>` from Task 1.
- Keeps `MentionText` props unchanged: `{ text: string; mentions?: MentionRef[] }`.

- [ ] Make `MentionText` render mention segments as router links and non-mention segments through `LinkifiedText`.
- [ ] Replace direct interpolation on non-linked detail surfaces for soup fields, profile bio, collection description, messages, announcements, notifications, and moderation previews.
- [ ] Leave rich-HTML views, inputs, errors, diagnostic `<pre>` output, titles/usernames, and already link-wrapped cards unchanged.
- [ ] Run `npm run build` from `frontend` and fix all Vue/TypeScript errors.

### Task 3: Verification And Pull Request Update

**Files:**
- Modify: existing PR branch only.

**Interfaces:**
- Produces a clean commit pushed to `codex/soup-collections-1-4-0`.
- Updates GitHub PR #13.

- [ ] Run the focused parser assertion script, frontend production build, and `git diff --check`.
- [ ] Review the complete diff for nested anchors, unsafe href construction, and missed primary detail surfaces.
- [ ] Commit with `feat: auto-link valid web URLs`.
- [ ] Push without force and verify PR #13 head SHA matches local HEAD.
