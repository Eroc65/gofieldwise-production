# FrontDesk Pro Sprint A Issue Bodies

## Issue 1 — Add job lifecycle timestamps and transition model

**Epic:** Scheduling/Team  
**Sprint:** A  
**Priority:** p0  
**Labels:** epic:scheduling-team, sprint:4, type:backend, priority:p0

### Description
Add `on_my_way_at`, `started_at`, and `completed_at` support with strict transition rules for dispatched jobs.

### Acceptance Criteria
- Transitions are enforced server-side.
- Invalid transitions return 422.
- Lifecycle timestamps are set once and persist correctly.
- All lifecycle routes enforce organization scoping.

### Dependencies
None

## Issue 2 — Create technician quick-action endpoints for mobile status updates

**Epic:** Scheduling/Team  
**Sprint:** A  
**Priority:** p0  
**Labels:** epic:scheduling-team, sprint:4, type:backend, priority:p0

### Description
Expose protected endpoints for `on_my_way`, `started`, and `completed` updates with minimal payloads for one-tap mobile UX.

### Acceptance Criteria
- Endpoints require auth and org-scoped access.
- Endpoint responses return updated lifecycle state.
- Timeline/audit event is emitted per state change.
- API contracts are covered with integration tests.

### Dependencies
Issue 1

## Issue 3 — Build job activity timeline model and API

**Epic:** Scheduling/Team  
**Sprint:** A  
**Priority:** p0  
**Labels:** epic:scheduling-team, sprint:4, type:backend, priority:p0

### Description
Persist actor/action timeline entries for dispatch and lifecycle changes and return timeline in job detail API.

### Acceptance Criteria
- Timeline stores actor/action/from/to/timestamp fields.
- Timeline query returns entries newest-first.
- Timeline is strictly organization-scoped.
- Integration tests cover creation and retrieval.

### Dependencies
Issue 1

## Issue 4 — Add customer notification adapter and internal channel implementation

**Epic:** Scheduling/Team  
**Sprint:** A  
**Priority:** p1  
**Labels:** epic:scheduling-team, sprint:4, type:backend, priority:p1

### Description
Implement notification adapter interface with internal channel support and pluggable SMS/email provider hooks.

### Acceptance Criteria
- Adapter interface is defined and used by lifecycle service.
- Internal channel sends deterministic payloads.
- Notification failure is captured without breaking job state transition.
- Tests cover success and failure paths.

### Dependencies
Issue 2

## Issue 5 — Wire lifecycle updates to customer notifications

**Epic:** Scheduling/Team  
**Sprint:** A  
**Priority:** p1  
**Labels:** epic:scheduling-team, sprint:4, type:fullstack, priority:p1

### Description
Trigger customer notification events on `on_my_way`, `started`, and `completed` transitions.

### Acceptance Criteria
- Each lifecycle event triggers one notification event.
- Event payload includes customer context and time context.
- Idempotent retries do not create duplicate notifications.
- End-to-end test validates event trigger points.

### Dependencies
Issue 4

## Issue 6 — Implement mobile-first technician job action card

**Epic:** Scheduling/Team  
**Sprint:** A  
**Priority:** p0  
**Labels:** epic:scheduling-team, sprint:4, type:frontend, priority:p0

### Description
Add mobile-optimized job action UI for `on_my_way`, `started`, and `completed` with <=3 taps from job detail.

### Acceptance Criteria
- All actions are visible and usable on mobile viewport.
- Loading/success/error feedback is clear.
- Updated lifecycle state appears immediately in job detail/timeline.
- Accessibility labels exist for action controls.

### Dependencies
Issue 2

## Issue 7 — Add dispatch-to-completion end-to-end smoke coverage

**Epic:** Scheduling/Team  
**Sprint:** A  
**Priority:** p0  
**Labels:** epic:scheduling-team, sprint:4, type:fullstack, priority:p0

### Description
Add deterministic smoke/e2e tests for dispatch -> lifecycle transitions -> timeline entries -> notification trigger points.

### Acceptance Criteria
- Backend integration test passes locally and in CI.
- Frontend e2e mobile viewport scenario passes.
- CI has focused gate before full suite.

### Dependencies
Issue 3

## Issue 8 — Add operational dashboard card for active lifecycle stages

**Epic:** Scheduling/Team  
**Sprint:** A  
**Priority:** p1  
**Labels:** epic:scheduling-team, sprint:4, type:fullstack, priority:p1

### Description
Add dashboard counters for `on_my_way`, `in_progress`, and `completed_today` to improve owner/operator visibility.

### Acceptance Criteria
- Cards load organization-scoped counts only.
- Empty-state behavior is clear.
- Values update after lifecycle transitions.
- Mobile layout remains usable.

### Dependencies
Issue 6
