# `~/.claude/CLAUDE.md` — credential handling section

Append this section to your global Claude Code config so every session understands the canonical-secrets pattern. **Append, don't replace** — leave any other config in place.

```markdown
## 🔐 CRITICAL: Credential Handling

**Two canonical homes for user-personal API credentials, both at `~/.config/dev-secrets/`:**

\`\`\`
~/.config/dev-secrets/secrets.env                       # personal-everywhere
~/.config/dev-secrets/<project>/secrets.env             # project-isolated
\`\`\`

Both are mode 0600, owned by the user, Time Machine excluded, outside any git repo.

**Personal-everywhere** (`secrets.env`) holds keys reused across all projects — `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `ELEVENLABS_API_KEY`, `HEYGEN_API_KEY`, `LIVEAVATAR_API_KEY`, `RESEND_API_KEY`, `GITHUB_TOKEN`.

**Project-isolated** (`<project>/secrets.env`) holds keys intentionally scoped to a single project or billing account.

**Rules:**
- **NEVER ask the user to paste an API key in chat.** Read from the file(s) instead.
- **NEVER paste an API key into command output, logs, or commit messages.** Source the file silently.
- **NEVER duplicate a key into a project's `.env`, `.env.local`, or `.env.tools`** — the canonical file is authoritative. Exceptions: framework-loaded envs that must contain the value at boot (Next.js `.env.local`, Vercel runtime) — keep both, treat canonical as the source of truth.
- **To use keys in a shell or script:**
  \`\`\`bash
  # Personal-only:
  set -a && source ~/.config/dev-secrets/secrets.env && set +a

  # Personal + project-isolated (project keys override personal for overlapping names):
  set -a
  source ~/.config/dev-secrets/secrets.env
  source ~/.config/dev-secrets/<project>/secrets.env
  set +a
  \`\`\`
- **If a key isn't in the canonical file but is needed,** add it there (or to the appropriate per-project subdir if billing-isolated). Don't paste it into a project env.
- **Project deployment credentials** (`DATABASE_URL`, `ADMIN_API_KEY`, `CRON_SECRET`, project-specific `MCP_API_KEY`) stay in `<project>/.env.local` per existing convention — they're tied to the deployment, not to the user.
- **High-blast-radius secrets** (AWS, Vercel deploy tokens, SSH private keys) go in macOS Keychain (`security add-generic-password`), NOT plaintext files.
```

## Why this matters

The Claude Code agent reads `~/.claude/CLAUDE.md` at session start. Without these rules, the agent will sometimes ask the user to paste keys, sometimes echo them in shell command output, and sometimes silently duplicate them into a project `.env`. With them, the agent knows where to look and what's forbidden.

The reference essay [*One File for All My Keys*](https://sethshoultes.com/blog/canonical-secrets.html) describes the audit that surfaced 17 env files holding the same handful of API keys — drift the agent itself contributed to before the rules were written down.
