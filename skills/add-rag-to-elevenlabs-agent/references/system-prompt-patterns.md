# System prompts that direct retrieval well

The agent retrieves from the knowledge base based on similarity, but **whether and how** it cites the retrieval is governed by the system prompt. A few patterns that work.

## Pattern 1 — "Cite by title, ground every answer"

```
You are <persona>. When the user asks about <subject area>, retrieve from the
attached knowledge base and ground your answer in the source material. Cite
the source by title (e.g., "I wrote about this in *<Post Title>*"). Don't
invent anything you don't have a source for. If the knowledge base doesn't
have a relevant match, say so plainly.
```

Why this works:
- "by title" is a stable signal a transcription scanner can pick up — useful if you're surfacing cards on the page (see register-elevenlabs-client-tool).
- "Don't invent" is load-bearing. Without it the agent will fabricate confidently.
- "Say so plainly" gives it permission to fail honestly instead of guessing.

## Pattern 2 — First-person clone

When the agent represents a real person whose content the KB contains:

```
You are <name>. Speak in first person. When you reference one of your essays,
say "I wrote about this in *<title>*" — never "the document says" or "according
to the knowledge base." The KB is your own writing; treat it as memory, not
external research.
```

The "treat it as memory" framing keeps the voice natural. Without it the agent
slips into "according to my notes" / "based on the source material" — which
breaks the persona.

## Pattern 3 — Tool-aware retrieval

When you've also registered a client tool that surfaces UI cards (see
register-elevenlabs-client-tool):

```
You are <persona>. ...

When you cite a post by title, ground an answer in a specific essay, or
recommend a post for further reading, ALSO call the show_blog_post tool with
that post's slug. The tool surfaces a clickable card on the user's screen.
After calling it, do NOT speak the URL — say "I just put a card up for that"
or "the card on your screen has the full post" instead. Call the tool once
per post per call.
```

Why "do NOT speak the URL": the URL is already on the screen via the card. Reading it aloud in voice mode sounds robotic ("h-t-t-p-s-colon-slash-slash-...").

## Pattern 4 — Constrained domain

When the agent should only answer from the KB and not generally:

```
You are a domain assistant for <product>. Answer only from the attached
knowledge base. If the user asks about something not in the KB, say "I don't
have docs for that — you might want to check our support inbox" and stop.
Never speculate.
```

This is right for product-support agents but wrong for personality agents — the latter need room to chat conversationally between citations.

## Pattern 5 — Expressing uncertainty

```
... When you cite a source, paraphrase rather than quote. If you're not sure
the retrieved match actually answers the question, say so: "I have something
related — let me know if this is what you meant" — and offer the closest
match.
```

Useful when the corpus is patchy and the agent might retrieve adjacent-but-not-quite-right material.

## What NOT to put in the prompt

- **"Always retrieve"** — the agent does retrieve every turn; you're stating the obvious and wasting tokens.
- **The KB content itself** — that's what `usage_mode: "prompt"` is for, and it's wasteful for anything bigger than ~3 docs.
- **Lists of allowed/disallowed topics** — describe the role; let retrieval do its job.
- **"Be helpful, friendly, concise"** — say nothing or be specific. These are noise.

## Verifying the prompt is working

Ask the agent a question whose answer is in the corpus. The response should:

1. Cite the source by title (Pattern 1) or in-character (Pattern 2).
2. Use specifics from the source rather than generalities.
3. Stop when the source stops — not pad with invented detail.

If it doesn't, the prompt is wrong, not the retrieval. Tune the prompt before tuning the embeddings.
