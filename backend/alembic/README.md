# Production migrations
Alembic is the sole production schema-evolution owner. Production startup must run `alembic upgrade head` during deployment/release, before the application is started. `Base.metadata.create_all()` is development/test-only.

Run from repository root:

```powershell
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m alembic current
.\.venv\Scripts\python.exe -m alembic downgrade -1
```

Never run downgrade against production without a reviewed recovery plan. Take a verified `pg_dump` first. A failed migration must abort the release; restore the isolated backup or fix forward with a new revision. Every tenant backfill revision must inventory NULL and ambiguous rows and refuse to assign ownership without evidence.

Backup/restore procedure:

```powershell
pg_dump --format=custom --file=backup\ait_$(Get-Date -Format yyyyMMdd_HHmmss).dump $env:DATABASE_URL
pg_restore --list backup\ait_*.dump | Out-File backup\manifest.txt
createdb -T template0 ait_restore_check
pg_restore --clean --if-exists --no-owner --dbname=$env:RESTORE_DATABASE_URL backup\ait_*.dump
psql $env:RESTORE_DATABASE_URL -c "SELECT 1; SELECT COUNT(*) FROM colleges;"
```

Use encrypted storage with restricted access, retain daily backups for at least 30 days plus monthly backups according to the deployment policy, and document the incident/recovery decision before production rollback. Restore only into an isolated database; never overwrite the live database during verification.
