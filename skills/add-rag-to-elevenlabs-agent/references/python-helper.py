#!/usr/bin/env python3
"""
Add new URL-sourced documents to an ElevenLabs Conversational AI agent's RAG
knowledge base. Idempotent: re-running with no changes is a no-op.

Reads a list of source URLs from one of:

  1. A `posts.json` / `sources.json` file at the repo root, OR
  2. A directory of files (default: `_posts/*.html`) whose URLs follow a
     predictable site pattern (override SITE_BASE + URL_PATTERN below).

For each source:
  GET    the agent → diff the new sources against the existing KB by `name`
  POST   /v1/convai/knowledge-base/url   (creates the KB doc, returns doc_id)
  POST   /v1/convai/knowledge-base/{doc_id}/rag-index   (kick off embedding)
  PATCH  the agent → merge new entries into knowledge_base (preserves existing)

Configure with env vars:
  ELEVENLABS_API_KEY  (required)   xi-api-key value
  ELEVENLABS_AGENT_ID (required)   the agent to attach docs to

Usage:
  python3 add-rag-helper.py                  # auto-detect new sources
  python3 add-rag-helper.py --dry-run        # show what would change
  python3 add-rag-helper.py <slug>           # force-add a specific source
"""
import argparse
import json
import os
import re
import sys
import urllib.request
import urllib.error
from pathlib import Path

# ---- configure for your project ----
ROOT = Path(__file__).resolve().parent.parent
POSTS_DIR = ROOT / "_posts"           # directory to scan for source files
SITE_BASE = "https://example.com"     # base URL of the public site
URL_PATTERN = "/blog/{slug}.html"     # how slug → public URL
EMBEDDING_MODEL = "e5_mistral_7b_instruct"
# ----

AGENT_ID = os.environ.get("ELEVENLABS_AGENT_ID")
API_KEY = os.environ.get("ELEVENLABS_API_KEY")
if not API_KEY:
    sys.exit("ELEVENLABS_API_KEY not set")
if not AGENT_ID:
    sys.exit("ELEVENLABS_AGENT_ID not set")


def call(method, path, body=None):
    url = f"https://api.elevenlabs.io{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"xi-api-key": API_KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        sys.exit(f"\n{method} {path} → HTTP {e.code}\n{body_text}")


def discover_sources():
    """Yield (slug, title, url) for every source file."""
    for p in sorted(POSTS_DIR.glob("*.html")):
        m = re.match(r"\d{4}-\d{2}-\d{2}-(.+)\.html$", p.name)
        if not m:
            continue
        slug = m.group(1)
        title_match = re.search(r'^title:\s*"([^"]+)"', p.read_text(), re.MULTILINE)
        title = title_match.group(1) if title_match else slug
        yield slug, title, f"{SITE_BASE}{URL_PATTERN.format(slug=slug)}"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("slug", nargs="?", help="Force-add a specific slug.")
    parser.add_argument("--dry-run", action="store_true", help="Show what would change; no writes.")
    args = parser.parse_args()

    agent = call("GET", f"/v1/convai/agents/{AGENT_ID}")
    prompt_obj = agent["conversation_config"]["agent"]["prompt"]
    existing_kb = prompt_obj.get("knowledge_base", []) or []
    existing_names = {entry.get("name") for entry in existing_kb}
    print(f"agent already has {len(existing_kb)} KB entries.")

    if args.slug:
        match = next((p for p in discover_sources() if p[0] == args.slug), None)
        if not match:
            sys.exit(f"no source found with slug '{args.slug}'")
        to_add = [match]
    else:
        to_add = [p for p in discover_sources() if p[1] not in existing_names]

    if not to_add:
        print("nothing to add. Up to date.")
        return

    print(f"\nsources to add ({len(to_add)}):")
    for slug, title, url in to_add:
        print(f"  • {title}\n    {url}")

    if args.dry_run:
        print("\n(dry run — no changes made.)")
        return

    new_entries = []
    print()
    for slug, title, url in to_add:
        print(f"  POST knowledge-base/url  {url}", flush=True)
        resp = call("POST", "/v1/convai/knowledge-base/url", {
            "url": url,
            "name": title,
            "enable_auto_sync": True,
        })
        doc_id = resp["id"]
        print(f"    id: {doc_id}")
        new_entries.append({
            "type": "url",
            "id": doc_id,
            "name": title,
            "usage_mode": "auto",
        })
        print(f"  index   {title}", flush=True)
        call("POST", f"/v1/convai/knowledge-base/{doc_id}/rag-index", {"model": EMBEDDING_MODEL})

    # PATCH replaces the knowledge_base array — preserve existing entries.
    combined = list(existing_kb) + new_entries
    print(f"\nPATCH agent (knowledge_base: {len(existing_kb)} + {len(new_entries)} new = {len(combined)})...")
    call("PATCH", f"/v1/convai/agents/{AGENT_ID}", {
        "conversation_config": {
            "agent": {
                "prompt": {"knowledge_base": combined}
            }
        }
    })
    print("  done.")
    print("\nRAG indexing runs in the background; first call after this may not have the new docs ready yet.")


if __name__ == "__main__":
    main()
