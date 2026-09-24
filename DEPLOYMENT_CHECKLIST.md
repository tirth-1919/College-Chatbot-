# Production Deployment Checklist
**AI FAQ College Chat Bot - Multi-College Platform**

**Date:** 2026-09-24  
**Version:** 1.0.0  
**Environment:** Production (Render/Docker)

---

## PRE-DEPLOYMENT

### 1. Code Review ✅

- [x] Security fixes reviewed and tested
- [x] Tenant isolation verified with comprehensive test suite
- [x] All tests passing (13/13 security tests + 23/23 E2E tests)
- [x] No blocking issues identified

### 2. Database Preparation ⚠️ **REQUIRED**

**CRITICAL: Run before deploying code changes**

#### A. Backup Production Database

```bash
# Connect to production PostgreSQL
# Create backup
pg_dump -h <POSTGRES_HOST> -U <POSTGRES_USER> -d <POSTGRES_DB> > backup_$(date +%Y%m%d_%H%M%S).sql
```

#### B. Verify Database State

```sql
-- Check for records with NULL college_id
SELECT COUNT(*) as records_needing_backfill
FROM knowledge_records
WHERE college_id IS NULL;

-- If count > 0, proceed to backfill
```

#### C. Run Backfill Script

**File:** `backend/app/scripts/backfill_record_college_ids.sql`

```bash
# Execute backfill SQL against production
psql -h <POSTGRES_HOST> -U <POSTGRES_USER> -d <POSTGRES_DB> -f backend/app/scripts/backfill_record_college_ids.sql
```

**Expected Output:**
```
BEFORE BACKFILL: X total records, Y with college_id, Z missing
AFTER BACKFILL: X total records, X with college_id, 0 missing
```

#### D. Verify Backfill Success

```sql
-- Should return 0
SELECT COUNT(*) FROM knowledge_records WHERE college_id IS NULL;

-- Verify distribution looks reasonable
SELECT 
    c.name as college_name,
    COUNT(kr.id) as record_count
FROM colleges c
LEFT JOIN knowledge_records kr ON kr.college_id = c.id
GROUP BY c.id, c.name
ORDER BY record_count DESC;
```

### 3. Environment Variables Verification

**Required Environment Variables:**

```bash
# Production essentials
DATABASE_URL=postgresql+psycopg2://user:password@host:5432/database
SECRET_KEY=<strong-secret-key-min-32-chars>
ENVIRONMENT=production

# API Keys
GEMINI_API_KEY=<your-key>
GROQ_API_KEY=<your-key>
OPENROUTER_API_KEY=<your-key>

# Optional but recommended
ADMIN_BOOTSTRAP_PASSWORD=<strong-password>
REDIS_URL=redis://host:6379/0
USE_REDIS=true
```

**Security Checks:**
- [ ] SECRET_KEY is strong (32+ characters, not a default value)
- [ ] ENVIRONMENT is set to "production"
- [ ] DATABASE_URL points to PostgreSQL (not SQLite)
- [ ] ADMIN_BOOTSTRAP_PASSWORD is set (or plan for manual admin creation)

### 4. Local Testing with PostgreSQL

**Optional but recommended:**

```bash
# Start local PostgreSQL via Docker
docker-compose up postgres

# Set environment
export DATABASE_URL="postgresql+psycopg2://ait_admin:ait_secure_pass_2026@localhost:5432/ait_db"

# Run tests
python -m pytest backend/tests/test_tenant_isolation_security.py -v
python -m pytest backend/tests/test_knowledge_categories_e2e.py -v

# Should see: 13 passed + 1 passed
```

---

## DEPLOYMENT

### 5. Deploy Code Changes

#### Via Render

```bash
# Commit changes
git add backend/app/api/v1/admin/knowledge_categories.py
git add backend/app/migrations/fix_category_uniqueness.py
git commit -m "fix: tenant isolation security - enforce college_id filtering on all CRUD operations"

# Push to production branch
git push origin main

# Render will auto-deploy
```

#### Via Docker

```bash
# Build new image
docker-compose build backend

# Stop old container
docker-compose stop backend

# Start new container
docker-compose up -d backend

# Watch logs
docker-compose logs -f backend
```

### 6. Post-Deployment Verification

#### A. Health Check

```bash
curl https://your-app.onrender.com/health

# Expected:
# {
#   "status": "healthy",
#   "app": "AI FAQ College Chat Bot",
#   "institution": "Multi-College Platform",
#   "environment": "production",
#   "version": "1.0.0"
# }
```

#### B. Database Connection

```bash
# Check logs for successful database connection
# Should see: "Database URL: postgresql+psycopg2://***"
# Should NOT see: "Database URL: sqlite:///"
```

#### C. Migration Execution

```bash
# Check logs for migration success
# Should see: "[MIGRATION] Category uniqueness constraints successfully migrated to tenant-scoped"
# Should see: "[PLATFORM] Platform infrastructure initialization complete"
```

#### D. Manual API Testing

**Test 1: Category Creation (College Admin)**

```bash
# Login as college admin
curl -X POST https://your-app.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@college.edu", "password": "password"}'

# Create category
curl -X POST https://your-app.onrender.com/api/v1/admin/knowledge-db/categories \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Category", "key": "test-category"}'

# Should return: 200 OK
```

**Test 2: Cross-Tenant Access Blocked**

```bash
# Try to access another college's category/record by ID
curl -X GET https://your-app.onrender.com/api/v1/admin/knowledge-db/records/<other-college-record-id> \
  -H "Authorization: Bearer <college-a-admin-token>"

# Should return: 404 Not Found (not 200!)
```

**Test 3: Super Admin Access**

```bash
# Login as super admin
curl -X POST https://your-app.onrender.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@platform.aifaq.bot", "password": "<bootstrap-password>"}'

# Should be able to access any college's data
```

---

## POST-DEPLOYMENT

### 7. Monitoring (First 24 Hours)

#### Error Monitoring

```bash
# Watch application logs
# Look for:
# - SQLAlchemy errors
# - 500 Internal Server Error
# - Unexpected 404s
# - Authentication failures
```

#### Database Monitoring

```sql
-- Check for new records with NULL college_id (should be 0)
SELECT COUNT(*) FROM knowledge_records WHERE college_id IS NULL;

-- Monitor record creation rate
SELECT 
    DATE(created_at) as date,
    COUNT(*) as new_records
FROM knowledge_records
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;
```

#### Security Monitoring

```sql
-- Monitor audit logs for suspicious activity
SELECT 
    action,
    user_id,
    resource,
    status,
    created_at
FROM audit_logs
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND status = 'FAILURE'
ORDER BY created_at DESC
LIMIT 50;

-- Check for unauthorized access attempts
SELECT 
    event_type,
    severity,
    ip_address,
    user_id,
    created_at
FROM security_events
WHERE created_at > NOW() - INTERVAL '24 hours'
  AND severity IN ('HIGH', 'CRITICAL')
ORDER BY created_at DESC;
```

### 8. User Communication

#### Notify Existing College Admins

**Subject:** Platform Security Enhancement Deployed

**Body:**
```
Dear College Administrator,

We've deployed important security enhancements to the AI FAQ College Chat Bot platform.

What changed:
- Enhanced tenant isolation ensures your college's data remains private
- Improved database performance and reliability
- No action required on your part

If you experience any issues accessing your college's data, please contact support immediately.

Best regards,
Platform Team
```

### 9. Rollback Plan

**If critical issues are discovered:**

#### A. Restore Database

```bash
# Restore from backup
psql -h <POSTGRES_HOST> -U <POSTGRES_USER> -d <POSTGRES_DB> < backup_YYYYMMDD_HHMMSS.sql
```

#### B. Revert Code

```bash
# Via Git
git revert <commit-hash>
git push origin main

# Render will auto-deploy previous version
```

#### C. Verify Rollback

```bash
# Check health endpoint
curl https://your-app.onrender.com/health

# Verify database state
psql -h <POSTGRES_HOST> -U <POSTGRES_USER> -d <POSTGRES_DB> -c "SELECT COUNT(*) FROM knowledge_records"
```

---

## COMPLETION CHECKLIST

### Pre-Deployment
- [ ] Production database backed up
- [ ] Backfill SQL executed successfully
- [ ] Environment variables verified
- [ ] Local PostgreSQL tests passing

### Deployment
- [ ] Code deployed to production
- [ ] Application started successfully
- [ ] No critical errors in logs

### Post-Deployment
- [ ] Health check passing
- [ ] Database connection verified (PostgreSQL not SQLite)
- [ ] Migrations executed successfully
- [ ] Manual API tests passing
- [ ] Cross-tenant security verified
- [ ] Monitoring dashboards checked
- [ ] College admins notified (if applicable)

### Documentation
- [ ] Deployment documented in changelog
- [ ] Known issues logged
- [ ] Rollback procedure verified

---

## CONTACTS

**Emergency Contacts:**
- **Platform Lead:** [Your contact]
- **Database Admin:** [DBA contact]
- **Security Team:** [Security contact]

**Escalation Path:**
1. Check logs and monitoring dashboards
2. Review audit report: `POSTGRESQL_PRODUCTION_AUDIT.md`
3. Execute rollback if necessary
4. Contact platform lead
5. Create incident report

---

## SUCCESS CRITERIA

Deployment is considered successful when:

✅ **Application Health:** Health endpoint returns 200 OK  
✅ **Database:** PostgreSQL connection active, all migrations applied  
✅ **Tenant Isolation:** Cross-tenant access attempts return 404  
✅ **Data Integrity:** All knowledge_records have non-NULL college_id  
✅ **Performance:** API response times < 500ms (95th percentile)  
✅ **Errors:** Error rate < 0.1% of requests  
✅ **Security:** No unauthorized access events in 24 hours  

**If all criteria met:** ✅ Deployment successful, proceed to normal operations  
**If any criteria failed:** ⚠️ Investigate immediately, consider rollback  

---

**Deployment Completed By:** _________________  
**Date/Time:** _________________  
**Sign-off:** _________________  

