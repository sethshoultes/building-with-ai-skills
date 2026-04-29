# building-with-ai-skills

Reusable Agent Skills for AI coding agents — Claude Code, Cursor, Codex, and any other [agentskills.io](https://agentskills.io)-compatible runtime. Each skill is a markdown file with frontmatter that tells an agent: *when this kind of task comes up, follow this procedure.*

These are the procedures I've used to build the avatar at [sethshoultes.com/talk/](https://sethshoultes.com/talk/), the RAG pipeline that grounds it in my blog, the Cloudflare Worker that mints the session tokens, and the GitHub Action that keeps it all in sync. Each skill links back to the blog post that explains why the pattern exists. The post tells you why; the skill makes the *how* clickable.

Companion essay: [Skills as SOPs](https://sethshoultes.com/blog/skills-as-sops.html) — the argument for treating processes as installable artifacts.

## Available skills

| Skill | What it does | Reference post |
|---|---|---|
| **add-avatar-to-site** | Put a HeyGen LiveAvatar with an ElevenLabs voice clone on any static site. Generates the Cloudflare Worker, the page, and the agent config. | [The Avatar Reads First](https://sethshoultes.com/blog/the-avatar-reads-first.html) |
| **add-rag-to-elevenlabs-agent** | Wire URL-sourced knowledge bases to an ElevenLabs Conversational AI agent. Includes the GitHub Action variant for auto-syncing from `_posts/`. | [The Bible Reads First](https://sethshoultes.com/blog/the-bible-reads-first.html) |
| **register-elevenlabs-client-tool** | Add a browser-side client tool to an agent so the agent can render UI on the page (cards, links, embedded media) by calling a tool. | [Skills as SOPs](https://sethshoultes.com/blog/skills-as-sops.html) |

More skills are queued from the brain vault — `add-cloudflare-worker-token-mint`, `add-admin-dashboard-via-worker`, `migrate-static-blog-to-jekyll`, `set-up-canonical-secrets`, `wire-rag-sync-github-action`, and others. They'll land here as the patterns prove themselves on real projects.

## Installation

### Option 1 — `npx skills add` (recommended)

```bash
# Install all skills globally (every Claude Code session, every project)
npx skills add github:sethshoultes/building-with-ai-skills -a claude-code -g

# Or install to the current project only
npx skills add github:sethshoultes/building-with-ai-skills -a claude-code

# Or install a specific skill only
npx skills add github:sethshoultes/building-with-ai-skills --skill add-avatar-to-site
```

Works with Claude Code, Cursor, Codex, and other [agentskills.io](https://agentskills.io)-compatible agents.

### Option 2 — manual

```bash
git clone https://github.com/sethshoultes/building-with-ai-skills.git
for skill in building-with-ai-skills/skills/*/; do
  ln -s "$(pwd)/$skill" ~/.claude/skills/$(basename "$skill")
done
```

Skills activate automatically when an agent detects a relevant task. Trigger phrases live in each skill's frontmatter (e.g., *"add an avatar to my site,"* *"wire RAG into ElevenLabs,"* *"register a client tool on a Conversational AI agent"*).

## Skill structure

Each skill follows the standard format:

```
skill-name/
├── SKILL.md      # frontmatter + procedural guidance for the agent
└── references/   # API endpoint specs, code examples, gotchas
```

`SKILL.md` is the agent-readable file. `references/` holds supporting material the skill points at — exact API request bodies, working code samples, troubleshooting trees.

## Design philosophy

- **Pit of success**: the correct path is the easiest path. Skills always default to the simplest pattern that works.
- **Gotcha-driven**: lead with what breaks. Silent failures (missing CORS headers, wrong audio formats, race conditions on Pages rebuild) are called out before agents hit them.
- **Backend / frontend split**: every code block is labeled with where it runs and which auth header it carries.
- **Progressive disclosure**: SKILL.md has the procedure and the rules; references hold the API specifics.

## Contributing

Open issues and PRs welcome. When adding a new skill:

1. Lead with gotchas — what breaks if you do it wrong?
2. Be explicit about backend vs frontend and which auth header to use.
3. Include trigger phrases in the skill description frontmatter.
4. Keep `SKILL.md` under 500 lines — move details to `references/`.
5. Link to a blog post or runbook that explains the pattern.

## License

MIT — see [LICENSE](./LICENSE).

## Author

Built by [Seth Shoultes](https://sethshoultes.com). Find more at [sethshoultes.com/blog](https://sethshoultes.com/blog) and the [Great Minds Constellation](https://github.com/sethshoultes/great-minds-constellation).
