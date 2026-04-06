## Summary
- [ ] Briefly describe the problem and solution

## Validation
- [ ] Local tests run
- [ ] CI checks pass

## Migration Safety Checklist
- [ ] Schema changes include an Alembic migration
- [ ] Migration upgrade path validated on existing DB state
- [ ] Migration handles local/dev sqlite edge cases (if applicable)
- [ ] Startup/runtime behavior is safe when schema is stale
- [ ] Rollback/downgrade path considered

## Risk
- [ ] Backward compatibility reviewed
- [ ] Operational impact reviewed

## Production Promotion Checklist
- [ ] Staging deploy completed successfully
- [ ] Post-deploy staging smoke completed successfully
- [ ] Role management flows validated
- [ ] Role audit JSON and CSV validated
- [ ] Rollback trigger and owner assigned
