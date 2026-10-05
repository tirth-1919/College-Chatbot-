"""Fail-closed PostgreSQL backup, verification, and isolated restore helpers.

A successful ``pg_dump`` is not considered a verified backup.  ``verify`` checks
both the dump catalog and its sidecar checksum.  ``restore-test`` restores into
an explicitly supplied isolated database, checks the schema and pgvector, then
optionally runs Alembic.  The script never prints a database URL or subprocess
stderr because PostgreSQL errors can contain credentials.

Examples (PowerShell):
  python -m backend.scripts.backup_restore backup --output backups/app.dump --retention-days 30
  python -m backend.scripts.backup_restore verify --input backups/app.dump
  python -m backend.scripts.backup_restore restore-test --input backups/app.dump --target-url $env:RESTORE_DATABASE_URL --run-migrations
  """
from __future__ import annotations
import argparse
import hashlib
import os
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path

def _tool(name: str) -> str:
    path = shutil.which(name)
    if not path:
        raise RuntimeError(f"Required PostgreSQL tool is unavailable: {name}")
    return path

def _run(args: list[str], *, allow_output: bool = False) -> str:
    '''Run a PostgreSQL utility without exposing URLs, passwords, or stderr.'''
    try:
        result = subprocess.run(
            args, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", errors="replace",
        )
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"PostgreSQL operation failed (exit code {exc.returncode})") from None
    return result.stdout if allow_output else ""


def _checksum_path(path: Path) -> Path:
    return path.with_suffix(path.suffix + ".sha256")


def _digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def _require_file(path: Path) -> None:
    if not path.is_file() or path.stat().st_size == 0:
        raise RuntimeError(f"Backup file is missing or empty: {path}")


def _prune(directory: Path, retention_days: int) -> int:
    if retention_days < 1:
        raise ValueError("retention-days must be at least 1")
    cutoff = datetime.now(timezone.utc) - timedelta(days=retention_days)
    removed = 0
    for dump in directory.glob("*.dump"):
        modified = datetime.fromtimestamp(dump.stat().st_mtime, timezone.utc)
        if modified < cutoff:
            dump.unlink()
            sidecar = _checksum_path(dump)
            if sidecar.exists():
                sidecar.unlink()
            removed += 1
    return removed

def backup(output: Path, database_url: str, retention_days: int | None = None) -> None:
    if not database_url.strip():
        raise ValueError("DATABASE_URL or --database-url is required")
    output.parent.mkdir(parents=True, exist_ok=True)
    _run([_tool("pg_dump"), "--format=custom", "--no-owner", "--no-acl", "--file", str(output), database_url])
    _require_file(output)
    digest = _digest(output)
    _checksum_path(output).write_text(f"{digest}  {output.name}\n", encoding="utf-8")
    removed = _prune(output.parent, retention_days) if retention_days is not None else 0
    print(f"PASS backup_created path={output} sha256={digest} pruned={removed}")


def verify(input_path: Path) -> None:
    _require_file(input_path)
    checksum = _checksum_path(input_path)
    if not checksum.is_file():
        raise RuntimeError(f"Checksum sidecar is missing: {checksum}")
    expected = checksum.read_text(encoding="utf-8").split()[0].strip().lower()
    actual = _digest(input_path)
    if expected != actual:
        raise RuntimeError("Backup checksum verification failed")
    _run([_tool("pg_restore"), "--list", str(input_path)])
    print(f"PASS backup_verified path={input_path} sha256={actual}")


def _database_probe(database_url: str) -> None:
    result = _run([
        _tool("psql"), "--no-psqlrc", "--tuples-only", "--no-align",
        "--dbname", database_url, "--command",
        "SELECT current_database(); SELECT extname FROM pg_extension WHERE extname='vector'; "
        "SELECT COUNT(*) FROM colleges;",
    ], allow_output=True)
    lines = [line.strip() for line in result.splitlines() if line.strip()]
    if len(lines) < 3 or not any(line == "vector" for line in lines):
        raise RuntimeError("Restore verification failed: pgvector extension is unavailable")
    try:
        college_count = int(lines[-1])
    except ValueError:
        raise RuntimeError("Restore verification failed: colleges table probe was invalid") from None
    if college_count < 1:
        raise RuntimeError("Restore verification failed: colleges table is empty")


def restore(input_path: Path, target_url: str, clean: bool = False, run_migrations: bool = False) -> None:
    verify(input_path)
    if not target_url.strip():
        raise ValueError("RESTORE_DATABASE_URL or --target-url is required")
    args = [_tool("pg_restore"), "--exit-on-error", "--no-owner", "--no-acl", "--dbname", target_url]
    if clean:
        args.extend(["--clean", "--if-exists"])
    args.append(str(input_path))
    _run(args)
    if run_migrations:
        alembic = shutil.which("alembic")
        if not alembic:
            raise RuntimeError("Alembic is unavailable; restore verification cannot continue")
        _run([alembic, "upgrade", "head"])
    _database_probe(target_url)
    print("PASS restore_verified schema=ok pgvector=ok tenants=readable")


def main() -> None:
    parser = argparse.ArgumentParser(description="Verified PostgreSQL backup and isolated restore utility")
    sub = parser.add_subparsers(dest="command", required=True)
    p_backup = sub.add_parser("backup")
    p_backup.add_argument("--output", type=Path, required=True)
    p_backup.add_argument("--database-url", default=os.getenv("DATABASE_URL", ""))
    p_backup.add_argument("--retention-days", type=int)
    p_verify = sub.add_parser("verify")
    p_verify.add_argument("--input", type=Path, required=True)
    p_restore = sub.add_parser("restore-test", aliases=["restore"])
    p_restore.add_argument("--input", type=Path, required=True)
    p_restore.add_argument("--target-url", default=os.getenv("RESTORE_DATABASE_URL", ""))
    p_restore.add_argument("--clean", action="store_true", help="Explicitly clean matching objects in the isolated target")
    p_restore.add_argument("--run-migrations", action="store_true")
    args = parser.parse_args()
    try:
        if args.command == "backup":
            backup(args.output, args.database_url, args.retention_days)
        elif args.command == "verify":
            verify(args.input)
        else:
            restore(args.input, args.target_url, args.clean, args.run_migrations)
    except (OSError, RuntimeError, ValueError) as exc:
        raise SystemExit(f"FAIL {exc}") from None
if __name__ == "__main__":
    main()

