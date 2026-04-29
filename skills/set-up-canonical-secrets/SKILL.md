---
name: set-up-canonical-secrets
description: |
  Consolidate scattered API keys from many `.env` / `.env.local` / `.env.tools` files into a single canonical home at `~/.config/dev-secrets/`. Personal-everywhere keys (Anthropic, OpenAI, Gemini, ElevenLabs, GitHub) live in `secrets.env`; project-isolated keys live in `<project>/secrets.env`. Files are mode 0600, outside any git repo, excluded from Time Machine. Use when: (1) the user has multiple projects sharing the same provider keys and wants ONE source of truth, (2) the user has lost track of how many places a given key is duplicated, (3) the user is setting up a new machine and wants the right pattern from day one, (4) the user mentions ".env files," "API key drift," "rotated a key but the old one still shows up," or "where do my secrets live." Skip when the user only wants project-deployment secrets (DATABASE_URL, CRON_SECRET) — those stay in `<project>/.env.local` per existing framework conventions.
license: MIT
metadata:
  author: sethshoultes
  version: "1.0.0"
  reference_post: https://sethshoultes.com/blog/canonical-secrets.html
---

# Set up canonical secrets

The pattern: personal-everywhere credentials and project-deployment credentials are different things and belong in different files. Three layers, two homes. The reference essay is *[One File for All My Keys](https://sethshoultes.com/blog/canonical-secrets.html)* — a hash audit on one developer's hard drive turned up 17 env files holding the same handful of API keys, drifting against one another. The procedure below consolidates them.

## The three layers

| Layer | What it holds | Where it lives |
|---|---|---|
| **1a — personal-everywhere** | Keys tied to your person and billing, reused across every project (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `HEYGEN_API_KEY`, `RESEND_API_KEY`, `GITHUB_TOKEN`) | `~/.config/dev-secrets/secrets.env` |
| **1b — project-isolated** | Keys billed to a specific account, intentionally not shared (e.g., a separate Anthropic account for a client cluster) | `~/.config/dev-secrets/<project>/secrets.env` |
| **2 — project deployment** | Keys a deployed app needs at runtime (`DATABASE_URL`, `ADMIN_API_KEY`, `CRON_SECRET`, project-specific `MCP_API_KEY`) | `<project>/.env.local` |
| **3 — project tooling** | Feature flags, paths, anything that's not a credential | `<project>/.env.tools` |

The skill covers Layers 1a and 1b. Layer 2 stays where Next.js / Vercel / framework conventions expect it; Layer 3 is config, not secrets.

## Step 1 — Discover what the user has

**Don't ask questions you can answer by checking.** Run this scan:

```bash
find ~/Local\ Sites ~/Dropbox ~/Downloads ~/sethshoultes.github.io \
     -type f \( -name ".env" -o -name ".env.*" -o -name "*.env" \) \
     -not -path "*/node_modules/*" -not -path "*/.next/*" -not -path "*/.git/*" 2>/dev/null
```

(Adapt the search roots to where the user keeps projects.)

Then for each file that exists, hash its key values (truncated SHA-256) and report:

- Which keys appear in which files
- Which values are shared vs which are different (drift indicator)
- Which files are in `.archived` / forgotten directories

See `references/audit-script.py` for the working hash-audit script.

## Step 2 — Create the canonical home

```bash
mkdir -p ~/.config/dev-secrets
chmod 700 ~/.config/dev-secrets
touch ~/.config/dev-secrets/secrets.env
chmod 600 ~/.config/dev-secrets/secrets.env
tmutil addexclusion ~/.config/dev-secrets/secrets.env   # macOS only
```

The directory is mode 700 so no other user can list it. The file is mode 0600 so no other user can read it. `tmutil addexclusion` keeps it out of Time Machine snapshots, which would otherwise carry every credential into a backup volume nobody audits.

For per-project isolation:

```bash
mkdir -p ~/.config/dev-secrets/<project>
chmod 700 ~/.config/dev-secrets/<project>
touch ~/.config/dev-secrets/<project>/secrets.env
chmod 600 ~/.config/dev-secrets/<project>/secrets.env
tmutil addexclusion ~/.config/dev-secrets/<project>/secrets.env
```

## Step 3 — Migrate Layer 1a keys

Take the audit output. For each user-personal key (Anthropic, OpenAI, Gemini, etc.), pick the canonical value (the most-recent rotation; when in doubt, rotate at the provider and use the new value). Append to `~/.config/dev-secrets/secrets.env`:

```
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-proj-...
GEMINI_API_KEY=...
ELEVENLABS_API_KEY=...
HEYGEN_API_KEY=...
LIVEAVATAR_API_KEY=...
HEYGEN_ELEVENLABS_SECRET_ID=...
RESEND_API_KEY=...
GITHUB_TOKEN=ghp_...
```

**Don't delete from source files yet.** Verify first (Step 6); delete after.

## Step 4 — Migrate Layer 1b keys (if applicable)

If the user has separate billing accounts (e.g., a client cluster that uses a different Anthropic key), put those in `~/.config/dev-secrets/<project>/secrets.env`. Document which projects load which file.

## Step 5 — Update `~/.claude/CLAUDE.md`

The agent has to know where the canonical file is and how to read it. Add a section to the user's global Claude Code config:

```markdown
## CRITICAL: Credential Handling

**Two canonical homes for user-personal API credentials, both at `~/.config/dev-secrets/`:**

\`\`\`
~/.config/dev-secrets/secrets.env                       # personal-everywhere
~/.config/dev-secrets/<project>/secrets.env             # project-isolated
\`\`\`

**Rules:**
- NEVER ask the user to paste an API key in chat. Read from the file(s) instead.
- NEVER paste an API key into command output, logs, or commit messages.
- NEVER duplicate a key into a project's `.env`. The canonical file is authoritative.
- Source pattern:
  \`\`\`bash
  # Personal-only:
  set -a && source ~/.config/dev-secrets/secrets.env && set +a

  # Personal + project-isolated:
  set -a
  source ~/.config/dev-secrets/secrets.env
  source ~/.config/dev-secrets/<project>/secrets.env
  set +a
  \`\`\`
- High-blast-radius secrets (AWS, Vercel deploy tokens, SSH private keys) go in macOS Keychain, NOT plaintext files.
```

The full template is at `references/claude-md-section.md`. Append it to the existing CLAUDE.md — don't replace.

## Step 6 — Verify

Open a fresh shell. Source the canonical file:

```bash
set -a && source ~/.config/dev-secrets/secrets.env && set +a
```

Run a script in any project that previously needed `OPENAI_API_KEY` (or whichever key). It should pick up the value from environment without complaint. If not: typo, stray space, or wrong quoting in the canonical file. Fix and retry.

## Step 7 — Delete duplicates from source files

Now that the canonical file works, edit each source `.env` and remove every Layer 1a key. Add a banner at the top:

```bash
# Layer 1a credentials (Anthropic, OpenAI, etc.) live in:
#   ~/.config/dev-secrets/secrets.env
# Source that file before running scripts that need those keys.
```

Don't delete the source `.env` entirely — it may still hold Layer 2 (deployment) or Layer 3 (tooling) keys.

## Step 8 — Rotate exposed keys

Any key that appeared in a chat transcript, screen-share, screenshot, or committed file gets rotated at the provider's dashboard. The new value is written to the canonical file and only the canonical file. Every project picks up the new value on its next session, because every project now reads from the same place.

## Step 9 — Install the load-secrets skill (optional)

For Claude Code agents, drop a small skill at `~/.claude/skills/load-secrets/SKILL.md` that triggers when an agent needs credentials. It instructs the agent to source the canonical file rather than asking the user to paste a key. See `references/load-secrets-skill.md`.

## When NOT to use this skill

- **Project deployment credentials.** `DATABASE_URL`, `CRON_SECRET`, project-scoped MCP keys — leave them in `<project>/.env.local` per the framework's expectations. The canonical pattern is for user-personal credentials, not project-deployment.
- **High-blast-radius secrets.** AWS root credentials, Vercel deploy tokens, SSH private keys — these belong in macOS Keychain (`security add-generic-password`), not plaintext files. The canonical pattern is for medium-trust API keys, not crown-jewels.
- **Team-shared credentials.** A canonical file is single-user. For team-shared keys, use a vault (1Password, Vault, AWS Secrets Manager) and a check-out workflow.

## Trigger phrases

- "Set up canonical secrets"
- "Consolidate my .env files"
- "I have API keys in too many places"
- "How do I stop API key drift"
- "Where should my secrets live"
- "Audit my .env files"

## Companion skills

- **set-up-claude-code-with-brain-vault** — pairs naturally; the brain vault explicitly excludes secrets and references the canonical file.
- **add-rag-to-elevenlabs-agent** / **add-avatar-to-site** / **register-elevenlabs-client-tool** — all read from the canonical file (`ELEVENLABS_API_KEY`, `LIVEAVATAR_API_KEY`, `HEYGEN_ELEVENLABS_SECRET_ID`).

## References

- [`references/audit-script.py`](references/audit-script.py) — hash-audit script that finds drift across env files
- [`references/migrate-script.py`](references/migrate-script.py) — reads a source env, classifies each key as 1a/1b/2/3, writes to the appropriate canonical file
- [`references/claude-md-section.md`](references/claude-md-section.md) — the full block to append to `~/.claude/CLAUDE.md`
- [`references/load-secrets-skill.md`](references/load-secrets-skill.md) — the `~/.claude/skills/load-secrets/SKILL.md`
- Reference essay: [One File for All My Keys](https://sethshoultes.com/blog/canonical-secrets.html)
