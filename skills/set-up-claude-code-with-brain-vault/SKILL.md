---
name: set-up-claude-code-with-brain-vault
description: |
  Set up a personal Obsidian knowledge vault at ~/brain wired to Claude Code as persistent memory across sessions. Use when: (1) the user wants Claude to remember things from past sessions, (2) the user mentions "brain vault," "Obsidian + Claude Code," "persistent memory," "knowledge base for AI," (3) the user is on a fresh machine and wants to set up the same flow Seth uses, (4) the user has a vault but no Claude integration. Skip when the user wants project-specific memory only — that belongs in the project's own CLAUDE.md, not a personal vault.
license: MIT
metadata:
  author: sethshoultes
  version: "1.0.0"
  reference_recipe: https://sethshoultes.com/recipes/claude-code-brain-vault.html
---

# Set up Claude Code with a brain vault

The pattern: an Obsidian vault at `~/brain` with a structured layout, a `CLAUDE.md` operating manual at the root, a `/brain` skill that saves notes during any session, lifecycle hooks that prompt for saves on session end, and an auto-committing git repo so the vault syncs across machines. The full human-readable recipe is at [sethshoultes.com/recipes/claude-code-brain-vault.html](https://sethshoultes.com/recipes/claude-code-brain-vault.html). The reference vault is [github.com/sethshoultes/building-with-ai-brain](https://github.com/sethshoultes/building-with-ai-brain).

## Step 1 — Discover what the user has

**Don't ask questions you can answer by checking.** Look first:

| Signal | Where | Means |
|---|---|---|
| `~/brain/` directory exists | local filesystem | vault already created — skip Step 2 |
| `~/brain/.git` exists | local filesystem | already a git repo — skip git init |
| `~/.claude/skills/brain/SKILL.md` exists | local filesystem | brain skill already installed — skip Step 6 |
| `SessionStart`/`Stop` keys in `~/.claude/settings.json` `hooks` field | local filesystem | hooks already configured — confirm before overwriting |
| Obsidian installed | `/Applications/Obsidian.app` (macOS) | UI step is straightforward |
| `gh auth status` returns logged-in | shell | can `gh repo create` automatically |
| `ollama list` shows `nomic-embed-text` | shell | embeddings model already pulled |

If anything's missing, the procedure below installs only what's missing — don't blow away existing config.

## Step 2 — Create the vault directory

```bash
mkdir -p ~/brain/{journal,learnings,projects,repos,runbooks,scripts,templates,claude-memory,backups}
cd ~/brain && git init -b main
echo "# Brain" > README.md
```

## Step 3 — Write the operating manual

Create `~/brain/CLAUDE.md` with the full content shown in the recipe. The key sections:

- Vault structure (which folder is for what)
- Frontmatter requirements per note type (`learnings`, `projects`, `repos`, `journal`, `runbooks`)
- File naming (date for journal, kebab-case for everything else)
- Wikilink rule (a note without links is a bug)
- What NOT to put in the vault (secrets, code that belongs in a project, prose drafts)

The full template is at [`building-with-ai-brain/CLAUDE.md`](https://github.com/sethshoultes/building-with-ai-brain/blob/main/CLAUDE.md). Copy it to `~/brain/CLAUDE.md` and customize the persona-specific bits.

## Step 4 — Add the templates

Three template files in `~/brain/templates/` — `learning.md`, `project.md`, `repo.md`. Each has YAML frontmatter and section headers. Copy from [`building-with-ai-brain/templates/`](https://github.com/sethshoultes/building-with-ai-brain/tree/main/templates) in the public skeleton repo.

The templates are what Obsidian's Templates plugin and the `/brain` skill both read when creating a new note.

## Step 5 — Wire Obsidian + Git

The UI step:

1. Open Obsidian → vault icon → Open folder as vault → select `~/brain`.
2. Settings → Community plugins → enable.
3. Install + enable the **Git** plugin.
4. Settings → Git → Vault backup interval: 10 minutes. Push on every commit: ON.

If the user is on a fresh machine and wants to clone an existing vault instead of creating a new one, point them at their own brain repo URL:

```bash
git clone https://github.com/<user>/brain.git ~/brain
```

## Step 6 — Push to GitHub

```bash
cd ~/brain
git add -A
git commit -m "Initial vault structure"
gh repo create brain --private --source=. --push
```

Default to `--private`. Most people don't want their notebook public on day one.

## Step 7 — Install the `/brain` skill

```bash
mkdir -p ~/.claude/skills/brain
# Drop a SKILL.md at ~/.claude/skills/brain/SKILL.md whose description triggers on
# phrases like "save this as a learning" / "save to brain" / "add to vault" — see
# the operating manual at building-with-ai-brain/CLAUDE.md for the slash-command
# contract this skill enforces.
```

The skill's `description` field uses trigger phrases like "save this as a learning" so it fires automatically. After install, the user runs `/reload-plugins` (or restarts Claude Code) and the skill is live.

The full operating contract the `/brain` skill must enforce is documented in [`building-with-ai-brain/CLAUDE.md`](https://github.com/sethshoultes/building-with-ai-brain/blob/main/CLAUDE.md).

## Step 8 — Wire the hooks

Edit `~/.claude/settings.json`. Merge — don't replace. The two minimum hooks:

```json
{
  "hooks": {
    "SessionStart": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "/Users/<you>/.claude/hooks/check-messages.sh",
            "timeout": 5
          }
        ]
      }
    ],
    "Stop": [
      {
        "hooks": [
          {
            "type": "command",
            "command": "echo '{\"systemMessage\": \"\\ud83e\\udde0 Anything worth saving to the brain vault? Run /brain to save a learning, runbook, or project note.\"}'",
            "timeout": 5
          }
        ]
      }
    ]
  }
}
```

The `Stop` hook is the workhorse: every session ends with a brain-vault prompt, training the habit of saving learnings.

**Gotcha — JSON escaping.** Backslashes inside the JSON-in-a-shell-command have to be double-escaped (`\\u` for unicode escapes inside the inner JSON). If the hook silently does nothing, the JSON is malformed.

The optional SessionStart script (`~/.claude/hooks/check-messages.sh`) is up to the user — typically surfaces something useful at session start (latest journal entry, agent message bus, TODO file, alerts).

## Step 9 — Add the search index

```bash
ollama pull nomic-embed-text
```

Then drop in a small Python script at `~/brain/scripts/brain-search.py` that builds and queries an embedding index. The reference implementation is at [github.com/sethshoultes/building-with-ai-brain/blob/main/scripts/brain-search.py](https://github.com/sethshoultes/building-with-ai-brain/blob/main/scripts/brain-search.py); the minimum useful version is ~80 lines and stores SQLite next to the vault.

Add a shell alias in `~/.zshrc`:

```bash
brain() {
  python3 ~/brain/scripts/brain-search.py "$@"
}
```

Then `source ~/.zshrc`. Use it: `brain index` (build), `brain "<query>"` (search).

## Step 10 — Verify

1. Open a Claude Code session in any project. The Stop hook should fire when the session ends — proves the hook is wired.
2. In the same session, do something worth remembering. Then say "save this as a learning." The agent should invoke `/brain`, draft, ask for approval, write `~/brain/learnings/<slug>.md`, and commit.
3. Wait ~10 minutes. The Obsidian Git plugin should auto-push to GitHub.
4. Run `brain "<keyword>"` — the new note should surface.

## When NOT to use this skill

- **Project-specific memory.** Cross-project knowledge belongs in `~/brain/`. Project-specific knowledge belongs in the project's own `CLAUDE.md` and `.great-authors/` (or equivalent project-bible directory). Don't put project-internal details in the personal vault.
- **Team knowledge.** A personal brain vault is single-user. For team-shared knowledge, build a shared docs site or a separate org-level vault.
- **Secrets.** The vault is a git repo. Even private repos leak. Secrets live in `~/.config/dev-secrets/secrets.env` per the canonical-secrets pattern; the vault references them but doesn't contain them.

## Trigger phrases

- "Set up a brain vault"
- "Wire Claude Code to my Obsidian vault"
- "Give me persistent memory across Claude sessions"
- "Set up the brain vault Seth uses"
- "Make Claude remember things from past sessions"
- "I want my own knowledge base for AI"

## Companion skills

- **set-up-canonical-secrets** (queued) — the credential pattern the vault explicitly excludes.
- **add-rag-to-elevenlabs-agent** — the same connective-tissue pattern, scoped to a Conversational AI agent instead of a personal vault.

## References

- [`CLAUDE.md`](https://github.com/sethshoultes/building-with-ai-brain/blob/main/CLAUDE.md) — the operating manual to drop at `~/brain/CLAUDE.md`
- [`templates/`](https://github.com/sethshoultes/building-with-ai-brain/tree/main/templates) — `learning.md`, `project.md`, `repo.md` for `~/brain/templates/`
- [`scripts/brain-search.py`](https://github.com/sethshoultes/building-with-ai-brain/blob/main/scripts/brain-search.py) — embedding-index script
- Hooks config: the SessionStart and Stop fragment is shown inline in Step 8 above — paste-ready
- Reference recipe: [Set up Claude Code with a Brain Vault](https://sethshoultes.com/recipes/claude-code-brain-vault.html)
- Reference repo: [github.com/sethshoultes/building-with-ai-brain](https://github.com/sethshoultes/building-with-ai-brain)
- Reference essay: [The Bible Reads First](https://sethshoultes.com/blog/the-bible-reads-first.html)
