# FrontDesk Pro Issue Bodies

## Set up repo, environments, CI, and deployment pipeline

**Epic:** Foundation  
**Sprint:** 0  
**Priority:** p0  
**Labels:** epic:foundation, sprint:0, type:infra, priority:p0

### Description
Set up the FrontDesk Pro engineering foundation, including repository structure, environment strategy, CI pipeline, staging deployment, and production deployment readiness.

### Acceptance Criteria
- Repo can be cloned and run locally
- CI runs on pull requests
- Staging deploy succeeds automatically
- Production deploy path is defined but protected
- Secrets are not hardcoded

### Dependencies
None

## Build auth foundation and organization/workspace model

**Epic:** Foundation  
**Sprint:** 0  
**Priority:** p0  
**Labels:** epic:foundation, sprint:0, type:backend, type:frontend, priority:p0

### Description
Implement authentication and the base multi-tenant organization/workspace model for FrontDesk Pro.

### Acceptance Criteria
- New user can sign up and create an organization
- Authenticated users land inside the correct workspace
- Unauthenticated users cannot access app routes
- Organization context is available throughout the app

### Dependencies
Issue 1

## Create base design system and authenticated app shell

**Epic:** Foundation  
**Sprint:** 0  
**Priority:** p0  
**Labels:** epic:foundation, sprint:0, type:frontend, type:design, priority:p0

### Description
Create the base UI system for FrontDesk Pro, including layout, navigation, theme tokens, typography, buttons, forms, cards, empty states, and mobile-friendly structure.

### Acceptance Criteria
- Authenticated app has a reusable layout
- Components are consistent across pages
- Mobile navigation works cleanly
- Empty state pattern exists for future modules

### Dependencies
Issue 2

# ... (continue with all issues in this format) ...
