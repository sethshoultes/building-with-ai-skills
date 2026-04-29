---
name: add-rag-to-elevenlabs-agent
description: |
  Wire URL-sourced (or file-sourced) knowledge base documents to an ElevenLabs Conversational AI agent so the agent retrieves grounded context per turn before generating its response. Use when: (1) the user wants their agent to ground answers in specific content (blog posts, docs, product specs), (2) the user asks about "RAG," "knowledge base," "retrieval," or "citing sources," (3) the agent's answers are too generic and need to be anchored in user-controlled material, (4) the user wants to keep the corpus auto-synced with a source (a blog feed, a docs repo). Skip when the agent already has well-tuned knowledge_base entries and the user just wants prompt tuning.
license: MIT
metadata:
  author: sethshoultes
  version: "1.0.0"
  reference_post: https://sethshoultes.com/blog/the-bible-reads-first.html
---

# Add RAG to an ElevenLabs Conversational AI agent

The pattern: each source URL or file becomes a knowledge-base document on the agent's account. Documents are RAG-indexed (embedded) server-side. The agent's `prompt.knowledge_base` array references them; `prompt.rag.enabled` is true; the system prompt instructs the agent to retrieve before answering. ElevenLabs handles chunking, embedding, retrieval-on-each-turn, and merges the retrieved chunks into the LLM prompt automatically.

The reference essay is *[The Bible Reads First](https://sethshoultes.com/blog/the-bible-reads-first.html)*. The pattern was first applied to ground a Seth-clone avatar in 17 blog post URLs at sethshoultes.com.

## Step 1 — Lock the inputs

You need three things before writing any code:

1. **`ELEVENLABS_API_KEY`** — the workspace API key. Lives in `~/.config/dev-secrets/secrets.env`. Never reaches the browser.
2. **Agent ID** — the agent the knowledge base attaches to. Pull from the ElevenLabs Conversational AI dashboard or `vercel env pull` if it's already wired into a project.
3. **Source list** — what to ingest. URL-sourced is best for living content (blog posts that auto-resync); file-sourced is best for stable docs (PDFs, exported markdown).

GET the agent first (`GET /v1/convai/agents/{agent_id}` with `xi-api-key`) and inspect:
- `conversation_config.agent.prompt.knowledge_base` — array of attached docs (`{id, name, type, usage_mode}`)
- `conversation_config.agent.prompt.rag.enabled` — boolean
- `conversation_config.agent.prompt.prompt` — the system prompt

Don't blow these away. Merge.

## Step 2 — Create knowledge base documents

For each URL source:

```bash
curl -X POST https://api.elevenlabs.io/v1/convai/knowledge-base/url \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://example.com/blog/post.html",
    "name": "Post title here",
    "enable_auto_sync": true
  }'
```

Response: `{"id":"...", "name":"...", "folder_path":[...]}`. **Capture the id**. Each id is what gets attached to the agent.

`enable_auto_sync: true` makes the document re-fetch when the URL's content changes. Use it for living content.

For file uploads, use `POST /v1/convai/knowledge-base/file` with `multipart/form-data`. See `references/api-endpoints.md`.

## Step 3 — Trigger RAG indexing

Documents must be embedded before the agent can retrieve them. Indexing runs server-side asynchronously; you trigger it explicitly:

```bash
curl -X POST "https://api.elevenlabs.io/v1/convai/knowledge-base/$DOC_ID/rag-index" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"model": "e5_mistral_7b_instruct"}'
```

Indempotent — calling it on an already-indexed doc returns the current status. Calling it on a new doc kicks off indexing. Indexing typically completes in 30-90 seconds per document.

## Step 4 — Attach + enable RAG + tune the prompt

PATCH the agent with the merged knowledge_base list, rag.enabled=true, and an updated system prompt:

```bash
curl -X PATCH "https://api.elevenlabs.io/v1/convai/agents/$AGENT_ID" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "conversation_config": {
      "agent": {
        "prompt": {
          "knowledge_base": [
            {"type":"url","id":"DOC_ID_1","name":"Post Title 1","usage_mode":"auto"},
            {"type":"url","id":"DOC_ID_2","name":"Post Title 2","usage_mode":"auto"}
          ],
          "rag": {"enabled": true},
          "prompt": "You are <persona>. When the user asks about <subject>, retrieve from the attached knowledge base and ground your answer in the source material. Cite the source by title (e.g. 'I wrote about this in *<Post Title>*'). Don't invent anything you don't have a source for."
        }
      }
    }
  }'
```

**`usage_mode: "auto"`** = retrieved per-turn based on relevance. **`usage_mode: "prompt"`** = always-loaded into context (wasteful for large corpora). Default to `auto`.

**Gotcha — PATCH replaces arrays, doesn't merge.** If the agent already has knowledge_base entries, GET them first, append the new ones, and PATCH the FULL combined list. See `references/python-helper.py`.

## Step 5 — Auto-sync from a Jekyll blog (optional but high-value)

For a static blog where new posts should auto-attach to the agent, scaffold a GitHub Action and a small helper script:

- `scripts/add-post-to-rag.py` — reads `_posts/*.html`, GETs the agent's current knowledge_base, diffs, POSTs new URLs, indexes, PATCHes the merged list. Idempotent.
- `.github/workflows/sync-rag.yml` — fires on `page_build` (NOT `push`; see gotcha below). Runs the script. Picks up `ELEVENLABS_API_KEY` from a repo secret.

**Critical gotcha — Pages rebuild race.** A workflow fired on `push` runs ~5–10 seconds after the commit lands; GitHub Pages takes 30–90 seconds to rebuild. ElevenLabs's URL ingestor returns `ReadabilityError` when the URL 404s or returns stale content. **Use `on: page_build`** — fires after Pages finishes — instead of `on: push` for any workflow that calls a URL-fetching webhook.

See `references/page-build-workflow.yml` for the working YAML.

## Step 6 — Verify

After the PATCH, GET the agent again and confirm:
- `prompt.knowledge_base.length` matches what you expect
- `prompt.rag.enabled === true`
- `prompt.prompt` contains the retrieval guidance

Then test the agent. Ask a question whose answer is in the corpus. The agent should cite the source by title. If it answers generically, the most likely cause is indexing not yet complete — wait 1–2 minutes and retry.

## When NOT to use this skill

- **The agent's audience needs broad world knowledge, not domain-specific.** RAG narrows; if the user wants the agent to be a general assistant, leave `rag.enabled: false`.
- **The corpus changes faster than ElevenLabs can re-sync.** Auto-sync resyncs roughly daily; for streaming-fresh content (live status pages, real-time logs), use a server-side tool that fetches at conversation time.
- **The corpus contains conflicting information.** RAG retrieves what's most-similar, not what's most-correct. Reconcile contradictions in the source material first.

## Trigger phrases

- "Add RAG to my agent"
- "Ground my agent in my blog posts"
- "Make the agent cite sources"
- "Wire a knowledge base"
- "Have my AI clone read my blog before answering"
- "Auto-sync new posts into the agent"

## Companion skills

- **add-avatar-to-site** — wires the avatar surface that this RAG-equipped agent powers.
- **register-elevenlabs-client-tool** — when the agent cites a post, surface a clickable card on the page via a client tool (`show_blog_post`).

## References

- [`references/api-endpoints.md`](references/api-endpoints.md) — full request/response shapes for the four endpoints used
- [`references/python-helper.py`](references/python-helper.py) — idempotent script that GETs the agent, diffs against a local source list, POSTs new docs, indexes, PATCHes
- [`references/page-build-workflow.yml`](references/page-build-workflow.yml) — GitHub Action with the `on: page_build` trigger
- [`references/system-prompt-patterns.md`](references/system-prompt-patterns.md) — examples of system prompts that direct retrieval well
- Reference essay: [The Bible Reads First](https://sethshoultes.com/blog/the-bible-reads-first.html)
- Brain learning: [`github-pages-rebuild-race-breaks-post-publish-webhooks`](https://github.com/sethshoultes/brain/blob/main/learnings/github-pages-rebuild-race-breaks-post-publish-webhooks.md)
