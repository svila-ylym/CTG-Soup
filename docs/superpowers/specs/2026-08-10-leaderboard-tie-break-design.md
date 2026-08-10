# Leaderboard Tie-Break Design

## Goal

When published/revealed soups have the same average score, rank the soup with more ratings first.

## Design

The existing leaderboard uses `GET /turtle-soups?sort_by=score`, which is backed by the shared soup list endpoint. Extend only the score ordering there:

1. `avg_rating` descending;
2. `rating_count` descending;
3. `created_at` descending;
4. `id` descending for deterministic ordering when all previous values match.

The ordering remains server-side so pagination, the homepage preview, and the full leaderboard use the same result. No database schema, API response, frontend component, or visible copy changes are needed.

## Constraints

- Do not add a scoring explanation to any page.
- Do not change how scores or rating counts are calculated.
- Do not add a migration or database column.
