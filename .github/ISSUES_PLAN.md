# FrontDesk Pro — GitHub Issues Plan

This file maps sprints and epics to actionable GitHub issues for the build queue. Use this as the source for creating issues in the repo.

## Sprint 0 — Foundation
- [ ] Monorepo structure
- [ ] GitHub repo config (branch strategy, PR/issue templates)
- [ ] Render/hosting setup
- [ ] Postgres provisioning
- [ ] Environment variable strategy
- [ ] R2-compatible storage config
- [ ] Initial DB schema/migrations
- [ ] Auth foundation
- [ ] Workspace/account model
- [ ] App shell, navigation, theme tokens
- [ ] Event logging base
- [ ] CI pipeline
- [ ] Staging/prod envs

## Sprint 1 — Org Setup, Dashboard, Core Models
- [ ] Org/user/tech/customer/job/estimate/invoice/reminder/note schema
- [ ] Org setup/onboarding form
- [ ] Dashboard shell
- [ ] Nav patterns
- [ ] User/org context
- [ ] Seed/demo data tools
- [ ] Event tracking

## Sprint 2 — Customers Module
- [ ] Customer CRUD, notes, history, job linking
- [ ] List/search/filter
- [ ] Add/edit forms
- [ ] Detail page
- [ ] Linked jobs/invoices/activity
- [ ] Communication log
- [ ] Mobile-friendly

## Sprint 3 — Jobs Module
- [ ] Job CRUD, status, tech assignment, notes, attachments
- [ ] List/filter
- [ ] Create/edit forms
- [ ] Detail page
- [ ] Status flow
- [ ] Mobile usability

## Sprint 4 — Scheduling/Calendar + Technicians/Team
- [ ] Tech/team CRUD
- [ ] Schedule/calendar views
- [ ] Assignment/reassignment
- [ ] Conflict indicators
- [ ] Mobile schedule
- [ ] Dashboard widgets

## Sprint 5 — Estimates, Invoices, Payments
- [ ] Estimate/invoice CRUD
- [ ] Convert estimate to invoice
- [ ] Invoice states
- [ ] Customer payment page
- [ ] Payment flow
- [ ] Filters/highlighting
- [ ] Dashboard unpaid/open

## Sprint 6 — Follow-Up/Reminder Engine
- [ ] Reminder engine schema/logic
- [ ] Reminder rules
- [ ] Reminder queue view
- [ ] Dashboard widget
- [ ] Snooze/dismiss/complete
- [ ] Notification hooks (in-app)
- [ ] Recurring rules

## Sprint 7 — AI Guide Phases 1–2
- [ ] AI Guide toggle
- [ ] Page overlays
- [ ] Guided flows
- [ ] Dismiss/skip/resume
- [ ] Business-focused copy
- [ ] Mobile support

## Sprint 8 — AI Guide Phase 3 + Dashboard Maturity
- [ ] Onboarding tracker
- [ ] Dashboard cards
- [ ] Empty states

## Sprint 9 — Mobile Optimization + Native App Prep
- [ ] Mobile audit/fixes
- [ ] Navigation/forms
- [ ] Mobile app shell
- [ ] Auth/session for mobile

## Sprint 10 — Marketing Site + Demo Path
- [ ] Homepage/pricing/demo/signup/support/SEO
- [ ] Proof sections/screenshots
- [ ] Analytics for funnel

## Sprint 11 — Reporting/Operational Visibility
- [ ] Dashboard/report views
- [ ] Date filters/exports
- [ ] Scheduled summary framework
- [ ] Admin/internal reporting

## Sprint 12 — Internal Automation Layer
- [ ] Internal task/approval model
- [ ] Automation dashboard
- [ ] Browser automation worker
- [ ] Research/content/SEO support
- [ ] Scheduled tasks
- [ ] Audit logs
