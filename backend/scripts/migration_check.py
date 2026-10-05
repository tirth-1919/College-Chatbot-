'''Read-only migration safety checks with redacted, machine-readable output.'''
from __future__ import annotations
import importlib.util
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
VERSIONS = ROOT / "alembic" / "versions"

def main() -> int:
    files = sorted(VERSIONS.glob("*.py"))
    if not files:
        print("FAIL no_migration_files")
        return 1
    revisions = {}
    errors = []
    for path in files:
        try:
            spec = importlib.util.spec_from_file_location(path.stem, path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            revision = getattr(module, "revision", None)
            if not revision:
                errors.append(f"missing_revision:{path.name}")
            elif revision in revisions:
                errors.append(f"duplicate_revision:{revision}")
            else:
                revisions[revision] = (path.name, getattr(module, "down_revision", None))
        except Exception:
            errors.append(f"unloadable:{path.name}")
    referenced = {down for _, down in revisions.values() if down}
    missing = sorted(referenced - set(revisions))
    if missing:
        errors.append("missing_dependency:" + ",".join(missing))
    heads = [rev for rev in revisions if rev not in referenced]
    if errors:
        print("FAIL errors=" + ",".join(errors))
        return 1
    if len(heads) != 1:
        print(f"FAIL heads={len(heads)}")
        return 1
    print(f"PASS migrations={len(revisions)} head={heads[0]}")
    return 0
if __name__ == "__main__":
    raise SystemExit(main())
