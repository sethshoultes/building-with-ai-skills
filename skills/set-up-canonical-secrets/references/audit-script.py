#!/usr/bin/env python3
"""
Audit env files for API-key drift and duplication.

For each env file under the search roots, computes a SHA-256 hash of each
key's value (truncated to 12 chars) and reports:
  - Which keys appear in which files
  - Which values are shared vs which differ (drift indicator)
  - Total counts so you can size the consolidation work

Usage:
  ./audit-script.py                          # default search roots
  ./audit-script.py ~/Code ~/Projects        # custom roots

The output is human-readable; use it to drive the consolidation in Step 3
of the SKILL.md.
"""
import argparse
import hashlib
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

DEFAULT_ROOTS = [
    "~/Local Sites",
    "~/Code",
    "~/Projects",
    "~/Dropbox",
    "~/Downloads",
]
EXCLUDE_DIRS = {"node_modules", ".next", ".git", ".venv", "venv", "__pycache__", "dist", "build"}
ENV_NAME_RE = re.compile(r"^(\.env(\..*)?|.*\.env)$")
KEY_LINE_RE = re.compile(r"^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$")

# Keys we consider "Layer 1a" — personal-everywhere credentials worth
# tracking for drift. Customize as needed.
LAYER_1A_KEYS = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_AI_API_KEY",
    "GOOGLE_API_KEY",
    "ELEVENLABS_API_KEY",
    "HEYGEN_API_KEY",
    "LIVEAVATAR_API_KEY",
    "RESEND_API_KEY",
    "GITHUB_TOKEN",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "DEEPGRAM_API_KEY",
    "TAVILY_API_KEY",
}


def find_env_files(roots):
    found = []
    for root in roots:
        root = Path(root).expanduser()
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
            for fn in filenames:
                if ENV_NAME_RE.match(fn):
                    found.append(Path(dirpath) / fn)
    return found


def parse_env(path):
    """Return list of (key, hash) for each key=value line."""
    out = []
    try:
        text = path.read_text(errors="replace")
    except (OSError, PermissionError):
        return out
    for line in text.splitlines():
        if line.lstrip().startswith("#"):
            continue
        m = KEY_LINE_RE.match(line)
        if not m:
            continue
        key, value = m.group(1), m.group(2).strip().strip('"').strip("'")
        if not value or value.startswith("$") or value in {"changeme", "your-key-here", "..."}:
            continue
        h = hashlib.sha256(value.encode()).hexdigest()[:12]
        out.append((key, h))
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("roots", nargs="*", help="search roots (defaults to common locations)")
    parser.add_argument("--all-keys", action="store_true", help="show every key, not just Layer 1a")
    args = parser.parse_args()

    roots = args.roots or DEFAULT_ROOTS
    print(f"scanning roots: {[str(Path(r).expanduser()) for r in roots]}")

    env_files = find_env_files(roots)
    print(f"found {len(env_files)} env files\n")

    # key -> { hash -> [files] }
    key_to_hash_files = defaultdict(lambda: defaultdict(list))
    for f in env_files:
        for key, h in parse_env(f):
            if not args.all_keys and key not in LAYER_1A_KEYS:
                continue
            key_to_hash_files[key][h].append(str(f))

    if not key_to_hash_files:
        print("(no Layer 1a keys found — try --all-keys to see everything)")
        return

    # Report
    drift = []
    print(f"{'KEY':<32} {'FILES':>5} {'DISTINCT VALUES':>15}")
    print("-" * 56)
    for key in sorted(key_to_hash_files):
        hashes = key_to_hash_files[key]
        files_total = sum(len(fs) for fs in hashes.values())
        n_distinct = len(hashes)
        marker = " ⚠️" if n_distinct > 1 else ""
        print(f"{key:<32} {files_total:>5} {n_distinct:>15}{marker}")
        if n_distinct > 1:
            drift.append(key)

    if drift:
        print("\n--- drift detail (multiple distinct values for the same key) ---")
        for key in drift:
            print(f"\n{key}:")
            for h, files in sorted(key_to_hash_files[key].items(), key=lambda x: -len(x[1])):
                print(f"  hash={h}  ({len(files)} file{'s' if len(files) > 1 else ''})")
                for f in files:
                    print(f"    {f}")
    else:
        print("\nno drift detected — all duplicate keys share the same value.")

    print()
    print("next: pick the canonical value for each drifted key, write it to")
    print("~/.config/dev-secrets/secrets.env, verify, then remove duplicates")
    print("from source files (per Step 7 of the SKILL.md).")


if __name__ == "__main__":
    main()
