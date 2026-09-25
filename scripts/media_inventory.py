#!/usr/bin/env python3
"""Read-only Atlas media inventory. Never modifies MongoDB or media files."""
import argparse, json, os, re
from datetime import datetime, timezone
from pymongo import MongoClient

URL = re.compile(r"^https?://", re.I)
def walk(value, path=""):
    if isinstance(value, str) and URL.match(value): yield path, value
    elif isinstance(value, dict):
        for key, child in value.items(): yield from walk(child, f"{path}.{key}" if path else key)
    elif isinstance(value, list):
        for index, child in enumerate(value): yield from walk(child, f"{path}[{index}]")

parser=argparse.ArgumentParser(); parser.add_argument("--output", default="media-inventory.json"); args=parser.parse_args()
client=MongoClient(os.environ["MONGO_URL"], serverSelectionTimeoutMS=10000)
db=client[os.environ["DB_NAME"]]; rows=[]
for collection in db.list_collection_names():
    for doc in db[collection].find({}, {"_id": 1, "images": 1, "image": 1, "data": 1, "avatar": 1}):
        for path, url in walk(doc): rows.append({"collection": collection, "document_id": str(doc["_id"]), "path": path, "url": url, "source": "emergent" if "emergent" in url else "external"})
json.dump({"generated_at": datetime.now(timezone.utc).isoformat(), "read_only": True, "entries": rows}, open(args.output,"w"), indent=2)
print(f"Wrote {len(rows)} media references to {args.output}")