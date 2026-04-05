# FrontDesk Pro — Sprint Plan (v1)

## Next 2 Sprints — GoFieldWise Execution Plan

Execution artifacts for Sprint A:
- [ISSUES_IMPORT_SPRINT_A.csv](../.github/ISSUES_IMPORT_SPRINT_A.csv)
- [ISSUE_BODIES_SPRINT_A.md](../.github/ISSUE_BODIES_SPRINT_A.md)

### Sprint A (2 weeks) — Dispatch to Completion Reliability
Goal: close the loop from assignment to completed work with customer-visible status and auditability.

Scope:
- Job lifecycle events: `on_my_way`, `started`, `completed` timestamps.
- Technician quick actions API for status transitions.
- Customer notification hooks for status changes (internal first, pluggable SMS/email adapter).
- Job activity timeline (who changed what and when).
- Mobile-first action flow for technician job card.

Stories:
- As an owner, I can see when a technician is en route, has started, and has completed a job.
- As a technician, I can update status in one tap from mobile.
- As a customer, I receive clear status updates during service.
- As an admin, I can audit all dispatch/status changes by user and timestamp.

Acceptance Criteria:
- Status transition rules are enforced server-side.
- Protected routes reject cross-organization access for all lifecycle endpoints.
- Activity timeline includes actor, action, previous state, new state, timestamp.
- Mobile flow supports complete lifecycle in <=3 taps from job detail.
- Regression tests cover success/failure transitions and org scoping.

Validation:
- Backend tests for lifecycle transitions and audit events.
- API smoke script for end-to-end dispatch -> complete flow.
- Frontend e2e for technician action flow on mobile viewport.

Definition of Done:
- Feature behind no manual DB patching.
- Migration path validated on fresh and existing DB.
- CI green with targeted and full regression tests.

### Sprint B (2 weeks) — Invoice & Collections Automation
Goal: reduce missed revenue by automating invoice issuance and collection follow-up.

Scope:
- Auto-generate invoice on job completion when eligible.
- Payment-link field and status tracking (`unpaid`, `paid`, `void`, `overdue`).
- Reminder escalation cadence (day 0, day 3, day 7, day 14).
- Dashboard cards: unpaid total, overdue count, aging buckets.
- Collection reminder suppression when invoice is paid.

Stories:
- As an owner, I get an invoice out immediately after work is complete.
- As an owner, I can see what is overdue and what to chase first.
- As a team member, reminders stop automatically when payment arrives.

Acceptance Criteria:
- Completion triggers invoice creation exactly once per eligible job.
- Reminder escalation is deterministic and idempotent.
- Re-opened invoices reactivate collection reminders.
- Dashboard metrics match underlying invoice/reminder state.
- All invoice/reminder queries are organization-scoped.

Validation:
- Unit + integration tests for auto-invoice and escalation logic.
- Deterministic smoke script for completion -> invoice -> escalation -> paid suppression.
- CI job includes focused collections regression gate before full suite.

Definition of Done:
- No duplicate invoices from repeated completion actions.
- Reminder lifecycle verified across paid/unpaid transitions.
- Release notes updated with operational behavior and rollback notes.

### Dependencies and Sequence
1. Finish Sprint A schema + API first.
2. Ship Sprint A UI and timeline.
3. Implement Sprint B invoice automation.
4. Implement Sprint B reminder escalation + dashboard.

### Risks and Mitigations
- Risk: stale local schema causes runtime failures.
	Mitigation: keep idempotent migrations and startup schema checks.
- Risk: notification provider instability.
	Mitigation: adapter interface + retry-safe internal queue.
- Risk: mobile UX friction slows adoption.
	Mitigation: mobile viewport e2e and tap-count acceptance checks.

### Exit Metrics
- Dispatch-to-complete timestamp coverage >= 95% of dispatched jobs.
- Auto-invoice rate >= 90% of completed eligible jobs.
- Overdue reminder send success >= 99% (internal channel baseline).
- Median time-to-dispatch update from technician < 2 minutes.

## Sprint 0 — Foundation
- Monorepo structure
- GitHub repo config
- Render/hosting setup
- Postgres provisioning
- Environment variable strategy
- R2-compatible storage config
- Initial DB schema/migrations
- Auth foundation
- Workspace/account model
- App shell, navigation, theme tokens
- Event logging base
- CI pipeline
- Staging/prod envs

## Sprint 1 — Org Setup, Dashboard, Core Models
- Org/user/tech/customer/job/estimate/invoice/reminder/note schema
- Org setup/onboarding form
- Dashboard shell
- Nav patterns
- User/org context
- Seed/demo data tools
- Event tracking

## Sprint 2 — Customers Module
- Customer CRUD, notes, history, job linking
- List/search/filter
- Add/edit forms
- Detail page
- Linked jobs/invoices/activity
- Communication log
- Mobile-friendly

## Sprint 3 — Jobs Module
- Job CRUD, status, tech assignment, notes, attachments
- List/filter
- Create/edit forms
- Detail page
- Status flow
- Mobile usability

## Sprint 4 — Scheduling/Calendar + Technicians/Team
- Tech/team CRUD
- Schedule/calendar views
- Assignment/reassignment
- Conflict indicators
- Mobile schedule
- Dashboard widgets

## Sprint 5 — Estimates, Invoices, Payments
- Estimate/invoice CRUD
- Convert estimate to invoice
- Invoice states
- Customer payment page
- Payment flow
- Filters/highlighting
- Dashboard unpaid/open

## Sprint 6 — Follow-Up/Reminder Engine
- Reminder engine schema/logic
- Reminder rules
- Reminder queue view
- Dashboard widget
- Snooze/dismiss/complete
- Notification hooks (in-app)
- Recurring rules

## Sprint 7 — AI Guide Phases 1–2
- AI Guide toggle
- Page overlays
- Guided flows
- Dismiss/skip/resume
- Business-focused copy
- Mobile support

## Sprint 8 — AI Guide Phase 3 + Dashboard Maturity
- Onboarding tracker
- Dashboard cards
- Empty states

## Sprint 9 — Mobile Optimization + Native App Prep
- Mobile audit/fixes
- Navigation/forms
- Mobile app shell
- Auth/session for mobile

## Sprint 10 — Marketing Site + Demo Path
- Homepage/pricing/demo/signup/support/SEO
- Proof sections/screenshots
- Analytics for funnel

## Sprint 11 — Reporting/Operational Visibility
- Dashboard/report views
- Date filters/exports
- Scheduled summary framework
- Admin/internal reporting

## Sprint 12 — Internal Automation Layer
- Internal task/approval model
- Automation dashboard
- Browser automation worker
- Research/content/SEO support
- Scheduled tasks
- Audit logs
