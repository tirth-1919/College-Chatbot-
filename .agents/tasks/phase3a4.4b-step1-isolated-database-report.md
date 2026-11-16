# Phase 3A.4.4B — Step 1: Isolated Database Report

## Final status: READY FOR MIGRATION VALIDATION

The disposable PostgreSQL 17 + pgvector test environment passed the Step 1 environment and extension checks. The container is intentionally left running for the later migration-validation phase. **No migrations were inspected or executed.**

## Docker verification

| Check | Result |
|---|---|
| Docker Client | PASS — version 29.9.3, API 1.56, `windows/amd64` |
| Docker Server | PASS — Docker Desktop 4.99.0, Engine 29.9.3, `linux/amd64` |
| `docker version` | PASS — Client and Server sections returned successfully |
| `docker info` | PASS — server information returned successfully |
| Pre-creation Docker inventory | PASS — 0 containers, 0 images, 0 volumes before image pull/resource creation |

## Image verification

| Check | Result |
|---|---|
| Image | `pgvector/pgvector:pg17` |
| Registry manifest | PASS — Linux/amd64 manifest present |
| Pulled image digest | `sha256:b513c48566e4777cd3370451400000c78eda6a08131d68f4c31d4a76f27bd8fd` |
| Image metadata | PASS — Linux/amd64; `PG_MAJOR=17`; `PG_VERSION=17.12-1.pgdg12+1` |
| PostgreSQL image executable | PASS — `PostgreSQL 17.12 (Debian 17.12-1.pgdg12+1)` |
| pgvector image files | PASS — `vector.control` and `vector.so` present |
| pgvector image default version | `0.8.7` |

## Disposable resource and isolation verification

Before creating resources, the requested exact container and volume names were checked and had no conflicts. Host port 55439 was checked by binding a temporary listener to `127.0.0.1`; it was available. No existing container, volume, database, or credential was reused.

| Check | Result |
|---|---|
| Container | PASS — `college-chatbot-pg17-test`, running and healthy |
| Database | PASS — `college_chatbot_test` |
| Host binding | PASS — Docker reports host IP `127.0.0.1`, port `55439`, container port `5432` |
| External client connection | PASS — psql reported connection to database `college_chatbot_test` on host `127.0.0.1` at port `55439` |
| PostgreSQL server | PASS — `17.12 (Debian 17.12-1.pgdg12+1)` |
| Data directory | PASS — `/var/lib/postgresql/data` |
| Data volume | PASS — mounted at the data directory from the newly created named volume `college-chatbot-pg17-test-data`; Docker reports its dedicated volume mountpoint as `/var/lib/docker/volumes/college-chatbot-pg17-test-data/_data` |
| Production isolation | PASS — no Supabase connection or production credential was used |
| Existing Windows PostgreSQL service/data directory | PASS — not accessed or modified |

The test-only PostgreSQL password was generated using a cryptographic random generator, stored in a session-local file with a restricted ACL, and mounted read-only as a password file. It was not placed in command-line arguments, logs, or this report. The file is retained for authorized follow-up tests.

## Extension verification

Only the following extension installation statements changed the new disposable database. They were run through psql over the verified loopback connection:

```sql
CREATE EXTENSION vector;
CREATE EXTENSION pgcrypto;
CREATE EXTENSION "uuid-ossp";
```

| Extension/check | Result |
|---|---|
| `vector` | PASS — version `0.8.7`; `vector_dims('[1,2,3]'::vector)` returned `3`; identical-vector distance returned `0` |
| `pgcrypto` | PASS — version `1.3`; a SHA-256 digest function check returned `true` |
| `uuid-ossp` | PASS — version `1.1`; `uuid_generate_v4()` returned a value (`true` check) |

The server identity query returned database `college_chatbot_test`, user `postgres`, server version `17.12`, and data directory `/var/lib/postgresql/data`.

## Command and result notes

- The initial combined psql command had a quoted-identifier parsing error at `uuid-ossp`. A subsequent read-only catalog query confirmed no extensions had been installed by that failed attempt. The corrected SQL was executed from a temporary file, and all three extension creations and functional checks succeeded.
- The temporary SQL file was removed after execution.
- No migration files were inspected or executed. No application role, RLS policy, signing key, synthetic application row, or invitation was created.
- The existing Windows PostgreSQL service remains untouched.

## Cleanup commands — not executed

The environment remains available for follow-up. Do not run these until all authorized validation is complete:

```powershell
docker stop college-chatbot-pg17-test
docker rm college-chatbot-pg17-test
docker volume rm college-chatbot-pg17-test-data
Remove-Item -LiteralPath 'C:\Users\HP\.copilot\session-state\305399f6-e77f-40ce-91ea-ae4adf622fdb\files\phase3a4.4b-step1\postgres_password' -Force
```

These commands target only the named disposable container, its dedicated volume, and the test-only password file. They do not target the existing Windows PostgreSQL service or its data directory.

## Next step

**READY FOR MIGRATION VALIDATION.** Begin the next approved Phase 3A.4.4B phase by reviewing the migration inventory and dependencies, then run migrations only against this verified disposable database. Keep the container bound to `127.0.0.1`; do not provide production settings or credentials.
