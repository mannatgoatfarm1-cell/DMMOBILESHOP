#!/usr/bin/env python3
"""Resumable media migration. Dry-run by default; --apply is owner initiated only."""
import argparse, hashlib, json, os, pathlib, shutil, urllib.request
from datetime import datetime, timezone
from pymongo import MongoClient

parser=argparse.ArgumentParser(); parser.add_argument("inventory"); parser.add_argument("--apply", action="store_true"); parser.add_argument("--rollback", action="store_true"); parser.add_argument("--log", default="media-migration-log.jsonl"); args=parser.parse_args()
root=pathlib.Path(os.environ["MEDIA_ROOT"]); root.mkdir(parents=True, exist_ok=True)
client=MongoClient(os.environ["MONGO_URL"]); db=client[os.environ["DB_NAME"]]
entries=json.load(open(args.inventory))["entries"]
if args.rollback:
    print("Rollback requires the original-document snapshots in the migration log; restore only after reviewing the log and taking a fresh Atlas backup."); raise SystemExit(2)
for item in entries:
    digest=hashlib.sha256(item["url"].encode()).hexdigest(); suffix=pathlib.PurePosixPath(item["url"].split("?",1)[0]).suffix or ".bin"; relative=f"migrated/{digest}{suffix}"; target=root/relative
    if not target.exists():
        if not args.apply: print("DRY RUN", item["url"], "->", relative); continue
        with urllib.request.urlopen(item["url"], timeout=60) as response, open(target,"wb") as out: shutil.copyfileobj(response,out)
    if target.stat().st_size == 0: raise RuntimeError(f"Verification failed: {target}")
    print("VERIFIED", relative, "for", item["url"])
print("No MongoDB reference was changed. Apply reference updates only with a reviewed collection-specific migration plan and verified backups.")