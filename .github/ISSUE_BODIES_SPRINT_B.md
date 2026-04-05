# FrontDesk Pro Sprint B Issue Bodies

## Issue 1 — Add payment link and invoice status lifecycle endpoints

**Epic:** Billing  
**Sprint:** B  
**Priority:** p0  
**Labels:** epic:billing, sprint:5, type:backend, priority:p0

### Description
Add invoice `payment_link` support and enforce invoice states (`unpaid`, `paid`, `void`, `overdue`) through protected API endpoints.

### Acceptance Criteria
- Payment link field persists and validates URL format.
- Status transitions are enforced server-side.
- All invoice routes are organization-scoped.
- API tests cover valid and invalid transitions.

### Dependencies
None

## Issue 2 — Implement auto-invoice-on-completion service

**Epic:** Billing  
**Sprint:** B  
**Priority:** p0  
**Labels:** epic:billing, sprint:5, type:backend, priority:p0

### Description
Create deterministic service that generates one invoice per eligible completed job and prevents duplicates.

### Acceptance Criteria
- Completion creates an invoice exactly once for eligible jobs.
- Repeated completion calls do not duplicate invoices.
- Invoice links correctly to job and organization.
- Integration tests cover idempotency behavior.

### Dependencies
Issue 1

## Issue 3 — Add collection escalation scheduler logic (day 0, 3, 7, 14)

**Epic:** Billing  
**Sprint:** B  
**Priority:** p0  
**Labels:** epic:billing, sprint:5, type:backend, priority:p0

### Description
Implement reminder escalation stages for unpaid invoices on deterministic day thresholds.

### Acceptance Criteria
- Escalation runs are idempotent.
- Day thresholds match spec exactly.
- Existing escalation stage is not duplicated.
- Reminder queries are organization-scoped.

### Dependencies
Issue 1

## Issue 4 — Implement payment event handling and reminder suppression

**Epic:** Billing  
**Sprint:** B  
**Priority:** p0  
**Labels:** epic:billing, sprint:5, type:backend, priority:p0

### Description
When invoice is paid, suppress active collection reminders; when invoice is reopened, reactivate correct reminder stage.

### Acceptance Criteria
- Paid transition dismisses active collection reminders.
- Reopened invoice reactivates reminder path.
- No cross-org side effects occur.
- Integration tests cover paid and reopen flows.

### Dependencies
Issue 3

## Issue 5 — Build unpaid and overdue dashboard cards with aging buckets

**Epic:** Billing  
**Sprint:** B  
**Priority:** p1  
**Labels:** epic:billing, sprint:5, type:fullstack, priority:p1

### Description
Add owner/operator dashboard visibility for unpaid totals, overdue counts, and aging buckets.

### Acceptance Criteria
- Cards are organization-scoped.
- Aging bucket math matches backend values.
- Empty-state behavior is clear.
- Mobile layout remains usable.

### Dependencies
Issue 1

## Issue 6 — Add payment-link UX on invoice detail and collection workflow

**Epic:** Billing  
**Sprint:** B  
**Priority:** p1  
**Labels:** epic:billing, sprint:5, type:frontend, priority:p1

### Description
Expose payment link controls in invoice detail and present copy/share actions for collections follow-up.

### Acceptance Criteria
- User can set/update payment link.
- Link is rendered clearly for copy/share.
- Validation errors are actionable.
- Works on mobile viewport.

### Dependencies
Issue 1

## Issue 7 — Add collections smoke script for completion-to-payment path

**Epic:** Billing  
**Sprint:** B  
**Priority:** p1  
**Labels:** epic:billing, sprint:5, type:backend, priority:p1

### Description
Create deterministic smoke script validating complete -> invoice -> escalation -> paid suppression path.

### Acceptance Criteria
- Script exits non-zero on failure.
- Script logs each stage with status output.
- Script runs in local and CI environments.

### Dependencies
Issue 2

## Issue 8 — Add focused CI gate for billing automation path

**Epic:** Billing  
**Sprint:** B  
**Priority:** p1  
**Labels:** epic:billing, sprint:5, type:infra, priority:p1

### Description
Add targeted CI step to run billing automation integration tests before full suite.

### Acceptance Criteria
- CI executes targeted billing tests in a separate step.
- Failures stop pipeline before long-running suite.
- Workflow file stays valid and deterministic.

### Dependencies
Issue 7
