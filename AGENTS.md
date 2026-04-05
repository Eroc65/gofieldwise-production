# When git commands time out or hang, do not stop and do not ask the user how to proceed. Retry with lighter git commands, check for stale lock files and stuck git processes, inspect repo/worktree state, and continue until the repository state is proven or a true blocker is identified.
# AGENTS.md

# IMPORTANT NOTES

- Keep this as the only root instruction file for now.
- Do not turn on nested AGENTS behavior until the repo is stable enough to justify separate backend/frontend instructions.

## FrontDesk Pro Repository Instructions

This repository is for **FrontDesk Pro**.

FrontDesk Pro is **AI-first front desk software for small trades businesses**. It is built for one-truck plumbers, two-person HVAC shops, family-run electrical companies, and similar service businesses that need enterprise-level efficiency without enterprise overhead.

The core product promise is:

**give tradespeople their trade back**

The product should help small service businesses:
- answer faster
- follow up consistently
- stay organized
- reduce missed revenue
- operate with the discipline of a much larger business

---

## Product Context

FrontDesk Pro exists because tradespeople started their businesses to do skilled work, not to spend their days:
- answering phones
- chasing invoices
- managing missed follow-up
- juggling scheduling chaos
- handling fragmented office/admin work

The product must feel:
- practical
- clear
- fast
- mobile-friendly
- useful in the moment
- simple enough for solo operators
- strong enough for small growing crews

Do not build this product like bloated enterprise software.

---

## Repo Priorities

When working in this repository, prioritize:

1. **shipping working vertical slices**
2. **mobile-friendly usability**
3. **plain-language UX**
4. **small-business practicality**
5. **deterministic validation**
6. **organization-scoped data safety**
7. **clear, maintainable code over clever abstractions**

Avoid:
- unnecessary complexity
- premature abstraction
- enterprise-style clutter
- jargon-heavy UX
- speculative features that are not part of the current roadmap

---

## Current Build Priorities

Unless a task explicitly says otherwise, prioritize work in this order:

1. backend/API foundation
2. organization/workspace-safe data model
3. customers, jobs, technicians, schedule, invoices, reminders
4. auth and protected route correctness
5. dashboard-supporting backend endpoints
6. AI Guide onboarding features
7. mobile-friendly frontend workflows
8. marketing site and demo path
9. internal automation/tooling

If frontend tooling is blocked, continue backend and infrastructure work automatically.

---

## Execution Standard

When given a task, do the work directly in the repository whenever possible.

Expected behavior:
- inspect relevant files first
- identify what already exists
- implement the smallest complete solution
- run validations after changes
- fix failures and rerun validation
- continue unblocked work automatically

Do not stop at:
- recommendations
- pseudocode
- “here’s how to do it”
- “would you like me to...”
- “choose a path”

Only ask for user input if one of these is required:
- credentials
- destructive actions
- external publishing
- spending money
- irreversible data deletion
- legal/compliance-sensitive action

---

## Validation Rules

Do not treat any of the following as proof by themselves:
- file exists
- route exists
- server started once
- documentation was updated
- command produced no output

Use deterministic validation.

### For backend/API work
Prefer:
- pytest or equivalent tests
- FastAPI TestClient tests
- smoke scripts that print status codes and JSON
- migration validation
- boot validation
- protected route validation

### For auth flows
Validate:
- signup/login path
- protected route rejects unauthenticated requests
- protected route succeeds with valid auth
- current organization/workspace context resolves correctly

### For database work
Validate:
- migrations generate
- migrations apply
- tables are created
- backend still boots cleanly

### For CRUD work
Validate:
- create works
- list works
- detail works
- update works
- organization scoping works

If one validation method is unreliable, switch to a more deterministic one.

---

## Dependency and Tooling Rules

When required tooling is missing, treat that as implementation work, not as a blocker.

If possible:
- install the missing dependency
- persist it in the correct dependency file
- restart affected services
- rerun validation
- continue automatically

This applies to:
- ORM tooling
- migration tooling
- test tooling
- runtime dependencies
- config scaffolding

Only declare a blocker after deterministic checks prove the task cannot continue with the tools and permissions available.

---

## FrontDesk Pro Domain Rules

Keep the product aligned with these realities:

### Target users
- one-truck plumbers
- two-person HVAC shops
- family-run electrical companies
- small service businesses without a full office staff

### UX expectations
- many users will work from their phone
- many users are not technical
- speed and clarity matter more than feature density
- every page should help the user know what to do next

### Product tone
Use plain language.
Prefer:
- “customers”
- “jobs”
- “team”
- “schedule”
- “invoice”
- “follow-up”

Avoid enterprise-heavy wording like:
- “resource orchestration”
- “workflow optimization layer”
- “organizational performance management”

---

## Coding Standards

Favor:
- small, readable functions
- clear naming
- explicit data flow
- strong request/response schemas
- organization-scoped queries
- simple service layers
- practical test coverage for business-critical behavior

Avoid:
- magic behavior
- hidden global state
- over-abstracted architecture
- unused framework complexity
- premature microservice splits

If you create new modules, keep naming and structure consistent with the existing repo.

---

## Data and Multi-Tenant Safety

FrontDesk Pro is organization/workspace based.

Always preserve:
- organization scoping
- protected access rules
- safe query boundaries
- no cross-organization leakage

When adding routes, services, or queries:
- scope records to the current organization where appropriate
- validate access through auth context
- prefer explicit filters over assumptions

---

## File and Planning Artifact Rules

For repo planning or GitHub-related tasks, use `.github/` as the default home.

Common planning files may include:
- `.github/ISSUES_IMPORT.csv`
- `.github/ISSUE_BODIES.md`
- `.github/labels.md`
- `.github/project-board.md`
- `.github/agents/`

When editing planning artifacts:
- use **FrontDesk Pro** consistently
- remove legacy naming
- keep markdown clean and copy-paste ready
- keep CSV import-friendly and deterministic

---

## Agent Behavior in This Repo

If acting as an execution agent:
- do the work first
- summarize after execution
- keep summaries short and factual

Preferred summary format:

### Completed
- files created or changed
- features implemented or fixes made

### Commands Run
- exact commands executed

### Validation
- exact checks performed
- exact results

### Remaining Blockers
- only true blockers
- if none, say `None`

Do not claim success if the validation section contradicts itself.

If results are contradictory:
- stop
- audit the repo/runtime state
- determine the truth with deterministic checks
- repair and rerun validation

---

## Architecture Direction

FrontDesk Pro should evolve as:
- a clean backend/API foundation
- a mobile-friendly product surface
- a guided onboarding experience
- a practical operations layer for small trades businesses

Do not let temporary environment blockers derail progress in unblocked areas.

If frontend tooling is unavailable, continue:
- backend/API work
- schema work
- tests
- seed data
- migrations
- planning artifacts
- docs tied directly to implemented behavior

---

## North Star

Every meaningful change should support this goal:

**help small trades businesses run with less chaos, fewer missed opportunities, and less office overhead**

When in doubt, choose the option that is:
- simpler
- more usable
- easier to validate
- safer for organization-scoped data
- more helpful to a busy owner-operator
