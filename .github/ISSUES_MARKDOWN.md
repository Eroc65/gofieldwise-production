# FrontDesk Pro — GitHub Issue Queue (by Sprint)

## Suggested Labels

- epic:foundation
- epic:crm-jobs
- epic:scheduling-team
- epic:billing
- epic:follow-up
- epic:ai-guide
- epic:mobile
- epic:marketing-site
- epic:reporting
- epic:internal-automation
- sprint:0 ... sprint:12
- type:backend
- type:frontend
- type:fullstack
- type:infra
- type:design
- type:product
- priority:p0 (highest), priority:p1, priority:p2

---

## Sprint 0 — Foundation and System Setup

### Issue 1 — Set up repo, environments, CI, and deployment pipeline
- **Epic:** Foundation
- **Sprint:** 0
- **Description:** Set up the FrontDesk Pro engineering foundation, including repository structure, environment strategy, CI pipeline, staging deployment, and production deployment readiness.
- **Acceptance Criteria:**
  - Repo can be cloned and run locally
  - CI runs on pull requests
  - Staging deploy succeeds automatically
  - Production deploy path is defined but protected
  - Secrets are not hardcoded
- **Dependencies:** None
- **Labels:** epic:foundation sprint:0 type:infra priority:p0
- **Priority:** p0

### Issue 2 — Build auth foundation and organization/workspace model
- **Epic:** Foundation
- **Sprint:** 0
- **Description:** Implement authentication and the base multi-tenant organization/workspace model for FrontDesk Pro.
- **Acceptance Criteria:**
  - New user can sign up and create an organization
  - Authenticated users land inside the correct workspace
  - Unauthenticated users cannot access app routes
  - Organization context is available throughout the app
- **Dependencies:** Issue 1
- **Labels:** epic:foundation sprint:0 type:backend type:frontend priority:p0
- **Priority:** p0

### Issue 3 — Create base design system and authenticated app shell
- **Epic:** Foundation
- **Sprint:** 0
- **Description:** Create the base UI system for FrontDesk Pro, including layout, navigation, theme tokens, typography, buttons, forms, cards, empty states, and mobile-friendly structure.
- **Acceptance Criteria:**
  - Authenticated app has a reusable layout
  - Components are consistent across pages
  - Mobile navigation works cleanly
  - Empty state pattern exists for future modules
- **Dependencies:** Issue 2
- **Labels:** epic:foundation sprint:0 type:frontend type:design priority:p0
- **Priority:** p0

# ... (truncated for brevity, continue with all issues as above) ...

## Recommended Issue Creation Order

1. Issue 1
2. Issue 2
3. Issue 3
4. Issue 4
5. Issue 5
6. Issue 6
7. Issue 7
8. Issue 8
9. Issue 9
10. Issue 10
11. Issue 11
12. Issue 12
13. Issue 13
14. Issue 14
15. Issue 15
16. Issue 16
17. Issue 17
18. Issue 18
19. Issue 19
20. Issue 20
21. Issue 21
22. Issue 22
23. Issue 23
24. Issue 24
25. Issue 25
26. Issue 26
27. Issue 27
28. Issue 28
29. Issue 29
30. Issue 30
31. Issue 31
32. Issue 32
33. Issue 33
34. Issue 34

## Suggested GitHub Projects Board Structure

- Columns:
  - Backlog
  - Sprint 0 (In Progress, Review, Done)
  - Sprint 1 (In Progress, Review, Done)
  - ...
  - Sprint 12 (In Progress, Review, Done)
  - Blocked
  - Ready for Release

- Views:
  - By Epic
  - By Sprint
  - By Priority
  - By Type

## CSV-Style Issue Import (Sample)

| Title | Epic | Sprint | Description | Acceptance Criteria | Dependencies | Labels | Priority |
|-------|------|--------|-------------|--------------------|--------------|--------|----------|
| Set up repo, environments, CI, and deployment pipeline | Foundation | 0 | Set up the FrontDesk Pro engineering foundation, including repository structure, environment strategy, CI pipeline, staging deployment, and production deployment readiness. | Repo can be cloned and run locally; CI runs on pull requests; Staging deploy succeeds automatically; Production deploy path is defined but protected; Secrets are not hardcoded | None | epic:foundation,sprint:0,type:infra,priority:p0 | p0 |
| Build auth foundation and organization/workspace model | Foundation | 0 | Implement authentication and the base multi-tenant organization/workspace model for FrontDesk Pro. | New user can sign up and create an organization; Authenticated users land inside the correct workspace; Unauthenticated users cannot access app routes; Organization context is available throughout the app | Issue 1 | epic:foundation,sprint:0,type:backend,type:frontend,priority:p0 | p0 |
| ... | ... | ... | ... | ... | ... | ... | ... |
