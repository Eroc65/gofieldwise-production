## Summary
<!-- What does this PR do? Why? -->

## Changes
<!-- Bullet-point list of notable changes -->

## Testing
<!-- How was this tested? -->

---

## Migration safety
<!-- Required for any PR that touches alembic/versions/ or app/models/ -->

- [ ] New migration is backwards-compatible (columns are nullable or have a server default)
- [ ] `alembic upgrade head` runs cleanly on a fresh DB
- [ ] `alembic upgrade head` runs cleanly on an existing DB with live data (or N/A)
- [ ] `alembic downgrade -1` is implemented and tested (or downgrade path documented)
- [ ] Schema guard in `backend/app/startup.py` still passes after migration
- [ ] No data-destructive operations (DROP COLUMN, truncation) without explicit sign-off

<!-- If this PR has NO schema changes, check the box below and delete the checklist above. -->
- [ ] No schema changes in this PR
