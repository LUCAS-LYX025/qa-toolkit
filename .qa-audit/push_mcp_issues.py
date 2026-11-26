#!/usr/bin/env python3
"""推送外部 MCP 消费层专项 issues 到 GitHub（断点续传）。"""
import json
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = "LUCAS-LYX025/qa-toolkit"
ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / ".qa-audit/mcp-issues.json"
MAP_OUT = ROOT / ".qa-audit/mcp-issue-number-map.json"


def token():
    proc = subprocess.run(
        ["git", "credential", "fill"],
        input="protocol=https\nhost=github.com\n\n",
        capture_output=True, text=True, check=True,
    )
    return next(line.split("=", 1)[1] for line in proc.stdout.splitlines()
                if line.startswith("password="))


def api(method, path, payload, tok):
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(
        f"https://api.github.com/repos/{REPO}/{path}", data=data,
        headers={"Authorization": f"Bearer {tok}",
                 "Accept": "application/vnd.github+json",
                 "Content-Type": "application/json",
                 "X-GitHub-Api-Version": "2022-11-28"},
        method=method)
    last = None
    for attempt in range(6):
        try:
            with urllib.request.urlopen(req, timeout=50) as resp:
                return json.load(resp)
        except urllib.error.HTTPError as exc:
            if exc.code in (403, 429, 502, 503):
                time.sleep(3 + attempt * 3)
                last = exc
                continue
            raise
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
        if attempt < 5:
            time.sleep(1 + attempt * 2)
    raise last


def main():
    tok = token()
    items = json.loads(SRC.read_text(encoding="utf-8"))
    nummap = json.loads(MAP_OUT.read_text(encoding="utf-8")) if MAP_OUT.exists() else {}
    for item in items:
        iid = str(item["id"])
        if iid in nummap:
            print(f"{iid} -> GitHub #{nummap[iid]} (skip)", flush=True)
            continue
        payload = {"title": item["title"], "body": item["body"], "labels": item["labels"]}
        try:
            created = api("POST", "issues", payload, tok)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:300]
            print(f"{iid} HTTP {exc.code}: {detail}", flush=True)
            MAP_OUT.write_text(json.dumps(nummap, ensure_ascii=False, indent=2), encoding="utf-8")
            raise SystemExit(2)
        nummap[iid] = created["number"]
        MAP_OUT.write_text(json.dumps(nummap, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"{iid} -> GitHub #{created['number']}", flush=True)
        time.sleep(0.6)


if __name__ == "__main__":
    main()
