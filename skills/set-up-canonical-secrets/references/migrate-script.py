#!/usr/bin/env python3
"""
Migrate keys from a source `.env` file into the canonical secrets file.

Reads the source file, classifies each key as Layer 1a / 1b / 2, and
writes Layer 1a entries into `~/.config/dev-secrets/secrets.env` (or a
per-project file with --project). Leaves the source file in place but
adds a banner pointing at the new home — actual deletion of the migrated
lines is a separate step done by hand after verification.

Usage:
  ./migrate-script.py /path/to/.env
  ./migrate-script.py /path/to/.env --project caseproof-studio
  ./migrate-script.py /path/to/.env --dry-run
"""
import argparse
import os
import re
import sys
from pathlib import Path

# Same Layer 1a list as audit-script.py — keep in sync.
LAYER_1A_KEYS = {
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GOOGLE_AI_API_KEY",
    "GOOGLE_API_KEY",
    "ELEVENLABS_API_KEY",
    "HEYGEN_API_KEY",
    "LIVEAVATAR_API_KEY",
    "HEYGEN_ELEVENLABS_SECRET_ID",
    "RESEND_API_KEY",
    "GITHUB_TOKEN",
    "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "DEEPGRAM_API_KEY",
    "TAVILY_API_KEY",
}

# Layer 2: project deployment — leave in place.
LAYER_2_PATTERNS = [
    re.compile(r".*DATABASE_URL$"),
    re.compile(r"^CRON_SECRET$"),
    re.compile(r"^ADMIN_API_KEY$"),
    re.compile(r"^ADMIN_TOKEN$"),
    re.compile(r"^MCP_API_KEY$"),
    re.compile(r"^NEXTAUTH_SECRET$"),
    re.compile(r"^STRIPE_(SECRET|WEBHOOK).*"),
]

KEY_LINE_RE = re.compile(r"^(\s*)([A-Z_][A-Z0-9_]*)\s*=\s*(.*)$")


def classify(key):
    if key in LAYER_1A_KEYS:
        return "1a"
    for pat in LAYER_2_PATTERNS:
        if pat.match(key):
            return "2"
    return "unknown"


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("source", help="Path to a source .env file to migrate from")
    parser.add_argument("--project", help="Migrate to ~/.config/dev-secrets/<project>/secrets.env instead of the personal-everywhere file")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be migrated; don't write anything")
    args = parser.parse_args()

    source = Path(args.source).expanduser().resolve()
    if not source.exists():
        sys.exit(f"source not found: {source}")

    if args.project:
        canonical = Path.home() / ".config" / "dev-secrets" / args.project / "secrets.env"
    else:
        canonical = Path.home() / ".config" / "dev-secrets" / "secrets.env"

    # Parse source
    migrate = []   # [(key, value, layer)]
    keep = []      # lines to leave in source
    for line in source.read_text().splitlines():
        m = KEY_LINE_RE.match(line)
        if not m:
            keep.append(line)
            continue
        _, key, value = m.group(1), m.group(2), m.group(3).strip()
        layer = classify(key)
        if layer == "1a":
            migrate.append((key, value, layer))
            keep.append(f"# (migrated to canonical) {line}")
        else:
            keep.append(line)

    print(f"source: {source}")
    print(f"canonical: {canonical}")
    print(f"keys to migrate ({len(migrate)}):")
    for k, _, _ in migrate:
        print(f"  • {k}")

    unknown = [k for k, _, layer in [(m[0], m[1], classify(m[0])) for m in [(k, v, l) for k, v, l in migrate]] if layer == "unknown"]
    if not migrate:
        print("\nnothing to migrate.")
        return

    if args.dry_run:
        print("\n(dry run — no changes made)")
        return

    # Read existing canonical to avoid duplicating keys we already have
    existing_keys = set()
    if canonical.exists():
        for raw in canonical.read_text().splitlines():
            m = KEY_LINE_RE.match(raw)
            if m:
                existing_keys.add(m.group(2))

    # Make sure canonical home exists with right perms
    canonical.parent.mkdir(parents=True, exist_ok=True)
    os.chmod(canonical.parent, 0o700)
    canonical.touch()
    os.chmod(canonical, 0o600)

    # Append new keys
    appended = 0
    with canonical.open("a") as out:
        for key, value, _ in migrate:
            if key in existing_keys:
                print(f"  (skipped {key} — already in canonical)")
                continue
            out.write(f"{key}={value}\n")
            appended += 1
    print(f"\nappended {appended} keys to {canonical}")

    # Rewrite source with migration banner + commented-out migrated lines
    banner = (
        "# Layer 1a credentials migrated to canonical home:\n"
        f"#   {canonical}\n"
        "# To use those keys, source the canonical file before running scripts:\n"
        "#   set -a && source ~/.config/dev-secrets/secrets.env && set +a\n"
        "# Once verified, you can delete the commented-out (migrated) lines below.\n"
        "\n"
    )
    source.write_text(banner + "\n".join(keep) + "\n")
    print(f"updated source ({source}) with migration banner — review before deleting commented-out lines")


if __name__ == "__main__":
    main()
