# ElevenLabs Conversational AI — RAG endpoints reference

Full request/response shapes for the four endpoints used by this skill.
All endpoints take `xi-api-key: $ELEVENLABS_API_KEY` as a header.

Base URL: `https://api.elevenlabs.io`

---

## 1. GET an agent

```
GET /v1/convai/agents/{agent_id}
```

Returns the full agent config. The fields this skill cares about:

```json
{
  "agent_id": "...",
  "conversation_config": {
    "agent": {
      "prompt": {
        "prompt": "You are <persona>. ...",
        "knowledge_base": [
          {"id": "doc_...", "name": "Post Title", "type": "url", "usage_mode": "auto"}
        ],
        "rag": {"enabled": true, "embedding_model": "e5_mistral_7b_instruct"},
        "tool_ids": ["tool_..."]
      }
    }
  }
}
```

GET first so you can merge new entries in rather than overwrite. PATCH on the agent **replaces arrays wholesale** — see the gotcha below.

---

## 2. Create a URL-sourced knowledge base document

```
POST /v1/convai/knowledge-base/url
```

Body:

```json
{
  "url": "https://example.com/blog/post.html",
  "name": "Post Title",
  "enable_auto_sync": true
}
```

`enable_auto_sync: true` makes the document re-fetch when the URL's content changes (roughly daily). Use it for living content. For one-shot ingestion of stable content, set `false`.

Response:

```json
{
  "id": "doc_abc123...",
  "name": "Post Title",
  "folder_path": []
}
```

**Capture `id`.** This is what gets attached to the agent.

---

## 2b. Create a file-sourced document (alternative)

```
POST /v1/convai/knowledge-base/file
Content-Type: multipart/form-data
```

Form fields:
- `file`: the binary (PDF, txt, md, docx, etc.)
- `name`: human-readable name

Response shape matches the URL variant. File-sourced docs don't auto-sync; if the file changes, replace the document.

---

## 3. Trigger RAG indexing

```
POST /v1/convai/knowledge-base/{document_id}/rag-index
```

Body:

```json
{
  "model": "e5_mistral_7b_instruct"
}
```

Idempotent — calling on an already-indexed doc returns its current status. Calling on a fresh doc kicks off indexing (typically 30–90s per document).

Response includes a status field. Poll if you need to block on indexing completion.

---

## 4. PATCH the agent

```
PATCH /v1/convai/agents/{agent_id}
```

Body — only include the fields you want to change:

```json
{
  "conversation_config": {
    "agent": {
      "prompt": {
        "knowledge_base": [
          {"type": "url", "id": "DOC_1", "name": "Post 1", "usage_mode": "auto"},
          {"type": "url", "id": "DOC_2", "name": "Post 2", "usage_mode": "auto"}
        ],
        "rag": {"enabled": true},
        "prompt": "<full system prompt — replaces the existing one>"
      }
    }
  }
}
```

### `usage_mode`

- **`auto`** (default) — retrieved per-turn based on relevance. Right for most corpora.
- **`prompt`** — always-loaded into context. Wasteful for >5 documents; reserve for a small "always-on" set.

### Critical gotcha — PATCH replaces arrays

`knowledge_base` and `tool_ids` are replaced entirely by what you send. To add a new document, GET the agent first, append to the existing array, then PATCH the full combined list. The same applies to `tool_ids` (see register-elevenlabs-client-tool skill).

The `prompt.prompt` (system prompt) is also replaced wholesale — don't send a partial string.

---

## Errors you'll see and what they mean

| Status | Cause | Fix |
|---|---|---|
| 401 | bad / missing `xi-api-key` | check the canonical secrets file |
| 404 on PATCH | bad agent_id | confirm in dashboard |
| 422 on knowledge-base/url | URL returned 404 / non-readable HTML | for GitHub Pages, switch the trigger to `page_build` to avoid the rebuild race |
| `ReadabilityError` | the URL didn't return parseable article content | the page must have substantive `<main>`/`<article>` content; index pages (just lists) often fail |
| `IndexingError` after rag-index | document is too large | split it; ElevenLabs caps individual docs around ~500KB of text |
