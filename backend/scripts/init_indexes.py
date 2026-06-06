"""
One-shot MongoDB index initializer for production (Atlas M0).

Run once after every schema change:

    cd backend && source .venv/bin/activate
    MONGO_URI=mongodb+srv://... python scripts/init_indexes.py

Designed for the M0 free tier:
- compound index on (user_id, status, created_at desc) turns the dashboard
  filtered list from a collection scan into an index scan
- TTL on logs(timestamp) at 90 days keeps the 512 MB cap from filling with
  agent-trace blobs
- unique indexes guard against the UUID collision class of bugs that
  caused the earlier auth regression

Safe to re-run: pymongo treats existing indexes idempotently.
"""
import os
import sys
from datetime import timedelta

from pymongo import ASCENDING, DESCENDING, MongoClient
from pymongo.errors import OperationFailure


LOG_TTL_DAYS = int(os.getenv("LOG_TTL_DAYS", "90"))


def _ensure(coll, keys, **opts):
    try:
        name = coll.create_index(keys, **opts)
        print(f"  [ok] {coll.name}: {name}  opts={opts}")
    except OperationFailure as exc:
        # 85 = IndexOptionsConflict, 86 = IndexKeySpecsConflict.
        # Both mean "an index with this name already exists with different
        # options"; treat as informational, do not abort.
        print(f"  [skip] {coll.name}: {exc}")


def main() -> int:
    uri = os.environ.get("MONGO_URI")
    if not uri:
        print("MONGO_URI must be set", file=sys.stderr)
        return 2

    client = MongoClient(uri, serverSelectionTimeoutMS=10_000)
    db = client.get_default_database()
    if db is None:
        print(
            "MONGO_URI must include a default DB name in the path "
            "(e.g. .../kpi_agent?retryWrites=true...)",
            file=sys.stderr,
        )
        return 2

    print(f"DB: {db.name}")
    print("users:")
    _ensure(db.users, [("email", ASCENDING)], unique=True, name="uniq_email")
    _ensure(db.users, [("user_id", ASCENDING)], unique=True, name="uniq_user_id")

    print("tasks:")
    _ensure(
        db.tasks,
        [("task_id", ASCENDING), ("user_id", ASCENDING)],
        unique=True,
        name="uniq_task_user",
    )
    _ensure(
        db.tasks,
        [("user_id", ASCENDING), ("status", ASCENDING), ("created_at", DESCENDING)],
        name="dashboard_filtered_list",
    )

    print("logs:")
    _ensure(
        db.logs,
        [("user_id", ASCENDING), ("timestamp", DESCENDING)],
        name="user_recent_logs",
    )
    _ensure(
        db.logs,
        [("task_id", ASCENDING), ("timestamp", DESCENDING)],
        name="task_recent_logs",
    )
    _ensure(
        db.logs,
        [("timestamp", ASCENDING)],
        name="logs_ttl",
        expireAfterSeconds=int(timedelta(days=LOG_TTL_DAYS).total_seconds()),
    )

    print("done")
    return 0


if __name__ == "__main__":
    sys.exit(main())
