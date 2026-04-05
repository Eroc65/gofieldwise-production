# Release Notes

## 2026-04-05

### Scheduling Readiness
- Added scheduling conflict endpoint: `GET /api/jobs/scheduling/conflict`
- Added next-slot endpoint: `GET /api/jobs/scheduling/next-slot`
- Added optional dispatch buffer support via `buffer_minutes`
- Enforced default technician availability window: 8:00 AM to 7:00 PM Central, Monday to Friday

### Dispatch Operator Experience
- Added Dispatch Assistant workflow in frontend with:
  - login helper
  - job and technician pickers
  - conflict check and next-slot suggestion
  - dispatch action from selected or suggested time

### Quality and Reliability
- Added deterministic frontend e2e flow test for login -> conflict -> next slot -> dispatch
- Added CI frontend e2e run after frontend build
- Added backend schedule readiness smoke in CI
- Added startup fail-fast schema compatibility check for technician availability columns
- Added Alembic migration for technician availability columns to support non-fresh databases
