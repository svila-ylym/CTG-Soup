# Unread Indicators And Email Default Design

## Scope

Show a boolean red dot for unread notifications, unread system messages, and unread private messages in the corresponding navigation controls. Never show an unread number. New registrations opt into bulk email by default, while existing users keep their current preference.

## Unread State Sources

Notifications use the existing `GET /api/notifications` endpoint with `unread_only=true`, page 1, and page size 1; the response total determines whether a dot is visible.

Extend `GET /api/system-messages` with an optional `unread_only` query parameter. When enabled, filter recipients whose `read_at` is null before both the count and page query. The frontend requests one item and uses the response total as a boolean.

Private messages reuse the existing Pinia chat store. Add a computed unread total derived from conversation `unread_count` values. The navigation initializes conversations and the existing WebSocket connection after authentication, so incoming messages update the dot immediately. Marking a conversation read already sets its unread count to zero.

## Shared Frontend State

Add an unread-indicator Pinia store with `hasNotifications` and `hasSystemMessages` booleans. It exposes refresh methods, starts one 30-second polling interval while authenticated, and stops and resets on logout. Failed refreshes preserve the last known state rather than hiding an existing dot.

`NavBar.vue` owns the authenticated lifecycle: start the unread store, load chat conversations, and connect chat realtime when authenticated; stop polling, disconnect chat, and clear user-specific state when unauthenticated. Component unmount performs the same cleanup.

Notification and system-message views call the appropriate refresh method after loading or successfully marking an item read. This removes dots immediately without waiting for the polling interval.

## Presentation

Replace the notification numeric badge with a fixed-size red dot and add identical dots to system-message and private-message icon buttons. Dots are positioned absolutely without changing button dimensions and include accessible unread labels. Mobile navigation links display the same boolean dot beside their text.

## Email Default

Set the `User.allow_bulk_email` Python model default and registration value to `true`, and align the response-schema fallback. Do not run a data migration and do not change the legacy migration default, because that would opt existing accounts into email without their action. Users can still disable email delivery in settings.

## Failure Handling And Verification

Unread refresh failures remain non-blocking and do not log users out. Chat connection failures continue using the store's existing polling fallback. Verification consists of focused backend tests for affected API/auth contracts, the existing backend regression suite, and the frontend TypeScript/Vite production build. Browser automation is explicitly excluded.
