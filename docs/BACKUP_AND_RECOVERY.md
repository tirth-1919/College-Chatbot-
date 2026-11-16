# Database Backup, Disaster Recovery & Business Continuity Plan

**System:** CampusAI – AI FAQ College Chatbot SaaS Platform  
**Target RPO (Recovery Point Objective):** $< 15$ Minutes  
**Target RTO (Recovery Time Objective):** $< 30$ Minutes  
**Scope:** PostgreSQL Relational Data, pgvector Embeddings, Supabase Storage Documents, Redis State  

---

## 1. Resilience & Backup Architecture

```
                    ┌───────────────────────────────┐
                    │  Production Supabase Database │
                    │   PostgreSQL 15+ & pgvector   │
                    └──────────────┬────────────────┘
                                   │
             ┌─────────────────────┴─────────────────────┐
             ▼                                           ▼
   Continuous WAL Archiving                 Daily Logical Snapshot
   (Point-in-Time Recovery)                 (pg_dump + gzip to S3/GCS)
   Retention: 30 Days                       Retention: 90 Days
```

---

## 2. Backup Schedules & Strategies

### 2.1 PostgreSQL Database
1. **Continuous WAL Archiving (Physical Backup):**
   - Managed automatically via Supabase WAL-G archiving.
   - Provides Point-In-Time Recovery (PITR) to any second within the last 30 days.
2. **Automated Daily Logical Dumps (`pg_dump`):**
   - Executed daily at 02:00 UTC via scheduled background cron.
   - Compresses schema and data using custom binary format (`-Fc`).
   - Retains 7 daily, 4 weekly, and 12 monthly snapshots in encrypted cold storage.

#### Manual On-Demand Backup Command
```bash
# Export complete schema and tenant data with pgvector embeddings
pg_dump -h db.[PROJECT-REF].supabase.co -U postgres -d postgres \
  --format=custom \
  --compress=9 \
  --file="campusai_backup_$(date +%Y%m%d_%H%M%S).dump"
```

### 2.2 Vector Embeddings (`knowledge_chunks`)
- The `knowledge_chunks` table contains both source text and 768-dimensional float arrays (`vector(768)`).
- When using `pg_dump`, pgvector data is fully preserved.
- If embeddings need complete recomputation from scratch, the system includes `scripts/reindex_embeddings.py` which reads approved `website_pages` and `document_pages` and recreates vector indexes.

### 2.3 Supabase Storage (PDF Documents & Logos)
- Original uploaded PDF documents and institutional verification proofs are stored in `college-documents` bucket.
- Cross-region replication enabled on the Supabase S3-compatible storage bucket.
- Cold backups synchronized weekly via AWS CLI / rclone:
  ```bash
  rclone sync supabase:college-documents s3://campusai-disaster-recovery-backup/documents
  ```

### 2.4 Redis Cache & Celery State
- Redis is configured with Append-Only File (`appendonly yes`) with `appendfsync everysec`.
- Since Redis holds transient cache, session locks, and job queues, lost Redis data will not corrupt core relational data. Active crawler or OCR jobs will be re-queued upon worker restart.

---

## 3. Disaster Recovery & Restoration Procedures

### 3.1 Point-in-Time Recovery (PITR) Execution
To recover from an accidental administrative deletion or schema corruption:
1. Navigate to the Supabase Dashboard -> **Database** -> **Backups**.
2. Select **Point in Time Recovery**.
3. Choose the target restoration timestamp (e.g., 5 minutes prior to incident).
4. Initiate restoration. The platform automatically provisions a recovery instance and transitions active connections.

### 3.2 Cold Restoration from Logical Dump
If restoring to a fresh PostgreSQL instance:
```bash
# 1. Enable pgvector extension on the clean database
psql -h target-host -U postgres -d postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"

# 2. Restore schema and data
pg_restore -h target-host -U postgres -d postgres \
  --clean --if-exists --no-owner --no-privileges \
  campusai_backup_YYYYMMDD_HHMMSS.dump

# 3. Apply any uncommitted migration scripts in sequence
alembic upgrade head
```

### 3.3 Post-Restoration Verification Checklist
- [ ] Connect via `GET /api/v1/health/ready` and confirm `checks.database: true`.
- [ ] Run automated test suite: `node scripts/test_phase13_phase14.js`.
- [ ] Execute sample vector similarity search to confirm pgvector index integrity:
  `SELECT chunk_id, content FROM knowledge_chunks ORDER BY embedding <=> '[...]' LIMIT 3;`
- [ ] Verify college tenant count and recent support tickets.

---

## 4. Disaster Recovery Testing Cadence

| Test Type | Frequency | Target Objective |
| :--- | :--- | :--- |
| **Automated Backup Integrity Test** | Weekly | Download latest dump and restore to transient container |
| **Simulated PITR Recovery Drill** | Bi-Annually | Restore database to staging and verify tenant isolation |
| **Failover Health Probe Test** | Monthly | Test automated failover of Redis and Celery worker restart |

