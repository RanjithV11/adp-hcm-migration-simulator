# ADP HCM Migration Runbook

## Cutover Procedure

### Pre-Cutover (T-24 hours)
1. ✅ Validate source system freeze window confirmed
2. ✅ Run full validation report on current target state
3. ✅ Verify backup of target HCM schema completed
4. ✅ Confirm stakeholder communication sent

### Cutover (T-0)
1. **Freeze source** — Disable writes to legacy HR
2. **Run delta extraction** — Capture changes since last full load
   `ash
   python run_pipeline.py --mode=delta --since=2026-01-15
   `
3. **Run validation suite** — All checks must PASS
   `ash
   python run_validation.py
   `
4. **Stakeholder sign-off** — Share validation report JSON

### Post-Cutover (T+4 hours)
1. **Parallel run** — Run payroll/HR reports on both systems
2. **Monitor validation metrics** — Automated alerts on drift
3. **Rollback trigger** — If >0.1% salary variance or >5 critical nulls

## Rollback Procedure

If validation fails post-cutover:
`ash
# 1. Restore target schema from backup
pg_restore -h localhost -U etl -d migration_demo backup_hcm_20260115.dump

# 2. Re-enable legacy HR writes
# 3. Communicate rollback to stakeholders
# 4. Root cause analysis within 24 hours
`

## Troubleshooting

| Issue | Resolution |
|-------|------------|
| worker_status_cd null | Check ef_status_mapping table populated; verify MAP_STATUS rule |
| Salary mismatch >0.1% | Verify currency rates in ef_currency_rate; check INR→USD conversion |
| FK orphans (dept/job) | Run LOAD_DEPTS_JOBS step before employees; check lookup cache |
| Duplicate SSN | Check source data quality; review deduplication logic in mapping |
| Redis connection failed | Verify Redis container healthy; check REDIS_HOST env var |

## Key Contacts

| Role | Name | Channel |
|------|------|---------|
| Migration Lead | [Your Name] | Teams/Slack |
| ADP Implementation Consultant | TBD | Email |
| Client HR Lead | TBD | Email |
| Infra/DB Admin | TBD | PagerDuty |

## Escalation Matrix

| Severity | Response Time | Action |
|----------|---------------|--------|
| P1 - Data loss / corruption | 15 min | Page DB Admin, halt cutover |
| P2 - Validation FAIL | 1 hour | Run diagnostics, engage ADP consultant |
| P3 - Performance degradation | 4 hours | Check Redis, DB indexes, query plans |
| P4 - Minor data quality | 24 hours | Log, fix in next delta load |

## Validation Thresholds

| Check | PASS | WARN | FAIL |
|-------|------|------|------|
| Row count diff | 0 | <2% | ≥2% |
| Salary total diff | <0.1% | <1% | ≥1% |
| Critical nulls | 0 | 0 | >0 |
| Duplicate SSN | 0 | 0 | >0 |
| FK orphans | 0 | <10 | ≥10 |
| Business rule violations | 0 | <5 | ≥5 |
