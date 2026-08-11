# Precise HTTP/HTTPS Auto-Linking Design

## Goal

Recognize complete HTTP and HTTPS URLs in user-authored text throughout the
application and render them as safe, clickable external links. A protocol
fragment such as `http://`, malformed host text, or `http://` embedded in an
ASCII word must remain ordinary text.

## Scope

The feature applies to plain-text content rendered by the frontend, including
posts and comments, soup puzzle/solution and people notes, profile biographies,
collection descriptions, direct messages, announcements, notifications, and
moderation text previews. Shared list/detail renderers should use the same
implementation.

Existing rich HTML is not passed through the plain-text parser. Competition
descriptions, system messages, and broadcast previews already use sanitized
Markdown/HTML with linkification and keep that pipeline. Form inputs, editable
textareas, code/preformatted diagnostic JSON, error messages, and text already
inside an anchor are not transformed.

## Parsing Rules

A reusable pure TypeScript parser returns ordered text and link segments. It
scans case-insensitively for `http://` or `https://` candidates and then accepts
a candidate only when all of these conditions hold:

- the protocol is exactly HTTP or HTTPS;
- the candidate is not immediately preceded by an ASCII letter, number,
  underscore, or `@`;
- the candidate contains no whitespace, control characters, angle brackets,
  quotes, or backticks;
- `new URL(candidate)` succeeds and produces a non-empty hostname;
- a candidate consisting only of a protocol or otherwise malformed authority
  is rejected;
- trailing Chinese or ASCII sentence punctuation is returned to the text;
- unmatched closing `)`, `]`, or `}` is returned to the text, while balanced
  brackets within URL paths remain part of the link.

The visible label preserves the original spelling. The href uses the accepted
original candidate. URL fragments and query strings are supported.

## Rendering And Safety

`LinkifiedText.vue` renders parser output with Vue text interpolation and real
`<a>` nodes; it never uses `v-html`. External links open in a new tab and carry
`rel="noopener noreferrer nofollow ugc"`. A shared link class provides the
same blue/underline interaction style used elsewhere.

`MentionText.vue` composes mention and URL segmentation: stored mention offsets
are applied first, and only non-mention text is passed through the URL parser.
This prevents an `@mention` and a URL from overlapping or corrupting offsets.

## Rollout

Replace direct interpolation at plain-text content surfaces with
`LinkifiedText`, and let all post/comment surfaces inherit the behavior through
`MentionText`. Do not create nested anchors inside cards that are already
entirely links; the card remains the navigation target and its full detail view
provides the external URL. This preserves valid HTML and keyboard behavior.

## Verification

Focused parser checks cover valid domains, ports, paths, query strings,
fragments, Chinese adjacency, trailing punctuation, balanced brackets,
protocol-only fragments, invalid hosts, non-HTTP schemes, and ASCII-word
embedding. The frontend production build validates Vue and TypeScript usage.
The backend is unchanged and does not require a schema migration.
