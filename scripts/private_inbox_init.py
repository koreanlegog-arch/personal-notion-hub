#!/usr/bin/env python3
"""Initialize the local private inbox without printing secrets."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from companion.private_store import (  # noqa: E402
    DEFAULT_DB_PATH,
    DEFAULT_TOKEN_PATH,
    PrivateStoreError,
    create_token,
    init_private_store,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Initialize Personal Notion Hub private inbox storage.")
    parser.add_argument("--db", default=str(DEFAULT_DB_PATH), help="SQLite DB path.")
    parser.add_argument("--token-file", default=str(DEFAULT_TOKEN_PATH), help="Bearer token file path.")
    args = parser.parse_args()

    db_path = Path(args.db)
    token_path = Path(args.token_file)

    try:
        init_private_store(db_path)
        create_token(token_path, overwrite=False)
    except (OSError, PrivateStoreError) as exc:
        print(f"private_inbox_initialized=false error={exc}", file=sys.stderr)
        return 2

    print("private_inbox_initialized=true")
    print(f"db_path={display_path(db_path)}")
    print(f"token_file={display_path(token_path)}")
    print("token_set=true")
    print("token_value_printed=false")
    print("storage_scope=local_ignored_workspace")
    return 0


def display_path(path: Path) -> Path:
    resolved = path.resolve()
    try:
        return resolved.relative_to(ROOT)
    except ValueError:
        return resolved


if __name__ == "__main__":
    raise SystemExit(main())
