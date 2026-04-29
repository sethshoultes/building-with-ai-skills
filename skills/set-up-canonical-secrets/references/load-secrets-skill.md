# `~/.claude/skills/load-secrets/SKILL.md`

Drop this skill at `~/.claude/skills/load-secrets/SKILL.md` so any Claude Code session can pull credentials from the canonical home without prompting the user.

```markdown
---
name: load-secrets
description: |
  Source API credentials from the canonical home at `~/.config/dev-secrets/secrets.env` (personal-everywhere) and optionally `~/.config/dev-secrets/<project>/secrets.env` (project-isolated). Use when: (1) the agent needs to run a script that depends on `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, etc., (2) the user mentions "load my keys," "source my secrets," (3) any script run mentions an env var the agent doesn't yet have. NEVER ask the user to paste a key in chat — source the file silently.
license: MIT
---

# Load secrets from the canonical home

The user keeps API keys in `~/.config/dev-secrets/`. Read from there, never from chat.

## Personal-only

\`\`\`bash
set -a && source ~/.config/dev-secrets/secrets.env && set +a
\`\`\`

This exports every variable in the file into the current shell's environment. `set -a` enables auto-export; `set +a` turns it off after the source completes so unrelated assignments after this point don't leak.

## Personal + project-isolated

When the project has its own billing account (e.g., `caseproof-studio`):

\`\`\`bash
set -a
source ~/.config/dev-secrets/secrets.env
source ~/.config/dev-secrets/<project>/secrets.env
set +a
\`\`\`

The second source overrides the first for keys that exist in both. Right ordering matters.

## Variables you can expect to find

In the personal-everywhere file (typical):

- `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`
- `ELEVENLABS_API_KEY`, `HEYGEN_API_KEY`, `LIVEAVATAR_API_KEY`
- `HEYGEN_ELEVENLABS_SECRET_ID`
- `RESEND_API_KEY`
- `GITHUB_TOKEN`

If the script needs a variable that isn't there, add it to the canonical file. Don't paste into chat. Don't write to a project `.env`.

## What NOT to do

- ❌ Ask the user to paste a key in chat.
- ❌ Print key values to stdout / stderr / logs.
- ❌ Echo keys into shell command output (`echo $ANTHROPIC_API_KEY`).
- ❌ Commit a script that reads a key from a literal string instead of the env.
- ❌ Duplicate a key into a project's `.env` or `.env.local`.

## When to use which file

| Project | Source |
|---|---|
| Personal projects (own writing, blog, side experiments) | `secrets.env` only |
| Client work with separate billing | `secrets.env` + `<client-cluster>/secrets.env` |
| Team-shared deployment | The project's `.env.local` (Layer 2) — not the canonical file |
```

## How the agent actually uses this

When a script needs `OPENAI_API_KEY`, the agent's behavior should be:

1. Run the script. If `OPENAI_API_KEY` isn't set in the environment, **silently** prepend the source command:
   ```bash
   set -a && source ~/.config/dev-secrets/secrets.env && set +a && python3 my_script.py
   ```
2. If the canonical file doesn't exist or doesn't have the key the script needs, surface that to the user as: "The script needs `<KEY>` but it's not in the canonical secrets file. Should I add it to `~/.config/dev-secrets/secrets.env`?" — never as "Please paste the key here."
3. If the user provides the key in conversation anyway (because they didn't know the rule), write it to the canonical file silently and continue. Don't echo it back.

## Verifying the skill is wired

Open a fresh Claude Code session in any project. Ask: "Run a script that needs my OpenAI key." The agent should source the canonical file and execute — no prompt for the key, no chat-echo of the value.

If the agent prompts you to paste, the skill isn't being invoked — check that `~/.claude/skills/load-secrets/SKILL.md` exists and that `/reload-plugins` has been run (or the session restarted).
