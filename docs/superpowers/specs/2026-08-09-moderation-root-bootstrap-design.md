# Moderation And Root Bootstrap Design

## Scope

Complete the existing report, account-ban, and turtle-soup deletion workflows, and assign the ROOT role to the first registered account when its database UID is 1.

## Reporting

Keep the current authenticated report submission endpoint for compatibility. Before inserting a report, normalize the target type, verify that the target exists and is visible to the reporter, reject self-reports, and reject a second pending report for the same reporter and target. Supported targets remain posts, comments, turtle soups, private messages, and users. Private-message reports are valid only when the reporter is the sender or receiver.

Admin report listings include whether the target still exists and a navigable target path when one is available. Accepting or rejecting a report records the handler, result, and time exactly once, writes an operation log, and creates a notification for the reporter.

## Bans

Use the existing `Punishment` table as the source of the audit record. Admins may ban ordinary users; ROOT may ban users and admins, but no one may ban themselves or a ROOT account. A duplicate active ban is rejected. Creating a ban sets the target status to `banned`, increments `token_version`, writes an operation log, and notifies the target. Existing access and refresh flows already reject banned accounts on their next request.

The admin user list exposes a permanent-ban action with a required reason. Existing ROOT-only role/status editing and punishment revocation remain available and are not replaced in this change.

## Turtle Soup Deletion

Add `DELETE /api/turtle-soups/{soup_id}`. The author, an admin, or ROOT may delete a soup. Deletion is idempotent from the storage perspective but deleted content returns 404 to public callers. The endpoint sets `status="deleted"`, updates the timestamp, writes an operation log, and removes entries belonging to competitions that have not been settled. Settled snapshots remain immutable.

The soup detail page shows a trash icon only when `can_manage` is true, requires explicit confirmation, calls the delete endpoint, and returns to the soup list.

## ROOT Bootstrap

Registration initially inserts a normal user so the database assigns the UID. Immediately after flush, UID 1 is promoted to `root`; every other UID remains `user`. The first ROOT account still completes the normal email-verification flow. The UID check makes the rule deterministic and avoids count-based races.

## Errors And Verification

API errors use stable status codes: 404 for missing targets, 403 for role violations, and 409 for duplicate pending reports or active bans. Backend contract tests cover each authorization boundary and the UID=1 rule. Frontend Playwright tests cover report submission, admin banning, and author deletion controls.
