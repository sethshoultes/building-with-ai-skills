---
name: add-avatar-to-site
description: |
  Put a real-time, lip-synced video avatar on any static or framework-based site, voiced by an ElevenLabs Conversational AI agent. Use when: (1) the user wants to add an interactive avatar of themselves (or a brand persona) to a website, (2) the user has an ElevenLabs Conversational AI agent already (or needs guidance creating one), (3) the user mentions "talking head," "live avatar," "HeyGen LiveAvatar," "voice clone on my site," or "make my site talk back," (4) the goal is voice + video conversation, not text chat. Skip when the user wants only text chat (no avatar) — use add-rag-to-elevenlabs-agent and a chat UI instead.
license: MIT
metadata:
  author: sethshoultes
  version: "1.0.0"
  reference_post: https://sethshoultes.com/blog/the-avatar-reads-first.html
---

# Add an avatar to a site

The pattern: a Cloudflare Worker mints short-lived LiveAvatar session tokens (so the long-lived API keys never reach the browser), the page loads the `@heygen/liveavatar-web-sdk` and starts a session with that token, the avatar's voice and brain run on an ElevenLabs Conversational AI agent (LITE mode + ElevenLabs Plugin). The reference implementation is at [sethshoultes.com/talk/](https://sethshoultes.com/talk/) and the architectural argument is in *[The Avatar Reads First](https://sethshoultes.com/blog/the-avatar-reads-first.html)*.

## Step 1 — Discover what the user has

**Do not ask questions the codebase or conversation already answers.** Check first:

| Signal | Where | Means |
|---|---|---|
| `LIVEAVATAR_API_KEY` in `~/.config/dev-secrets/secrets.env` | canonical secrets | LiveAvatar account already provisioned |
| `ELEVENLABS_API_KEY` in canonical secrets | canonical secrets | ElevenLabs account already provisioned |
| `HEYGEN_ELEVENLABS_SECRET_ID` in canonical secrets | canonical secrets | ElevenLabs key already registered as a HeyGen secret |
| Existing ElevenLabs agent ID | env vars or dashboard | agent and persona already configured |
| Custom HeyGen avatar trained | dashboard | avatar likeness ready (otherwise must be created — manual UI step) |
| Existing Cloudflare Workers | `~/Local Sites/*-worker` dirs | extend an existing worker or stand up a new one |

If any LiveAvatar / ElevenLabs prereq is missing, see `references/prerequisites.md`.

## Step 2 — Lock the configuration

You need four IDs/secrets before writing any code. Lock them in this order:

1. **Avatar ID** — UUID of the user's HeyGen LiveAvatar (NOT the standard HeyGen avatar — must be the "streaming" variant). From the LiveAvatar dashboard.
2. **ElevenLabs agent ID** — alphanumeric string (e.g. `jCFMMenhYBsub2QvAHal`). From the ElevenLabs Conversational AI dashboard.
3. **HeyGen ElevenLabs Secret ID** — UUID HeyGen issues when you register the ElevenLabs API key as a HeyGen secret. From `app.heygen.com/settings/secrets`.
4. **`LIVEAVATAR_API_KEY`** — distinct from `HEYGEN_API_KEY`; routes to a different credit pool. Live in canonical secrets, never in the browser.

**Gotcha:** `LIVEAVATAR_API_KEY` and `HEYGEN_API_KEY` look interchangeable but are not. LiveAvatar streaming sessions only authenticate with `LIVEAVATAR_API_KEY`. Mixing them returns 401 with no helpful guidance. See `references/heygen-credit-pools.md`.

## Step 3 — Stand up the Cloudflare Worker

The Worker has one job: take a request from the page, POST to LiveAvatar's session-token endpoint with the API key, return the short-lived session token to the browser.

Reference Worker: `references/worker-template.js`. Adapt the `AVATAR_ID`, `ELEVENLABS_AGENT_ID`, and `ALLOWED_ORIGINS` env vars to the project. Set `LIVEAVATAR_API_KEY` and `HEYGEN_ELEVENLABS_SECRET_ID` as Worker secrets via `wrangler secret put`. Deploy with `wrangler deploy`.

CORS: restrict `ALLOWED_ORIGINS` to the production domain plus localhost for dev. Don't wildcard.

**Gotcha:** LiveAvatar uses uppercase `X-API-KEY` header — case matters on their edge. Lowercase `x-api-key` returns 401.

## Step 4 — Build the page

The page does three things: fetch a session token from the Worker, load the SDK from a CDN (or bundle), and start a `LiveAvatarSession` attached to a `<video>` element.

Reference page: `references/talk-page-template.html`. Adapt the `WORKER_URL`, the styling, and the placeholder content (a portrait + welcome text before the call starts).

The minimum SDK dance:

```js
import { LiveAvatarSession } from "https://esm.sh/@heygen/liveavatar-web-sdk@0.0.17";
const { sessionToken } = await fetch(WORKER_URL).then(r => r.json());
const session = new LiveAvatarSession(sessionToken, { voiceChat: true });
await session.start();
session.attach(videoElement);
await session.voiceChat.start();
```

**Gotcha — mobile aspect ratio:** if you constrain `.stage` with `aspect-ratio: 16/9`, the placeholder content (avatar photo + heading + description) gets clipped on narrow viewports. Move the aspect-ratio to the `<video>` and `<iframe>` elements themselves so the stage can grow taller for the placeholder. See `references/talk-page-template.html` for the working CSS.

## Step 5 — Wire the agent

The avatar's brain is the ElevenLabs agent. Set its system prompt to the persona it should speak as (first person, voice rules, what it knows about the user). If the user wants the avatar to ground answers in their own content, immediately apply the **add-rag-to-elevenlabs-agent** skill next.

Default `voiceChat: true` is correct for a normal conversational session. The page should also handle: stop button (calls `session.stop()`), `beforeunload` listener (graceful disconnect), error states (token mint failure, SDK load failure, mic permission denial).

## Step 6 — Verify end-to-end

1. Deploy the Worker. `curl -i -H "Origin: https://YOURDOMAIN" $WORKER_URL` should return 200 with `sessionToken` and `Access-Control-Allow-Origin: https://YOURDOMAIN`.
2. Load the page, click Start, allow microphone. The video element should populate within ~2 seconds.
3. Speak. The avatar should respond in voice within ~3 seconds.
4. If silent: check the browser console for SDK errors, the Worker logs (`wrangler tail`), and that the agent's TTS output format is **PCM 24K** (LiveAvatar's hard requirement; see `references/lite-mode-audio.md`).

## When NOT to use this skill

- **Text chat** without an avatar — use a regular chat UI + the agent in text mode. Skill for that is queued (`add-text-chat-with-elevenlabs`).
- **Custom STT/LLM/TTS pipeline** — use FULL Mode with custom LLM. The HeyGen `liveavatar-integrate` skill covers that pathway in detail.
- **Just an iframe** — if the user doesn't need any control or branding, the LiveAvatar embed iframe is one line of HTML. Use `references/iframe-fallback.md` and skip the Worker entirely.

## Trigger phrases

- "Add an avatar to my site"
- "Put my voice clone on the homepage"
- "Build a Talk to Seth page"
- "Wire up HeyGen LiveAvatar"
- "Make my site talk back"
- "Live avatar with ElevenLabs voice"

## Companion skills

- **add-rag-to-elevenlabs-agent** — ground the avatar's answers in user-controlled content (URLs, files, blog posts). Run after this skill if the avatar should know about specific material.
- **register-elevenlabs-client-tool** — add browser-side client tools so the avatar can render UI on the page (cards, links, embedded media) by calling a tool.

## References

- [`references/worker-template.js`](references/worker-template.js) — full Cloudflare Worker source
- [`references/talk-page-template.html`](references/talk-page-template.html) — full HTML page with mobile-friendly CSS
- [`references/heygen-credit-pools.md`](references/heygen-credit-pools.md) — HeyGen has three credit pools; which API key drains which
- [`references/lite-mode-audio.md`](references/lite-mode-audio.md) — PCM 24K audio format requirement and how to verify
- [`references/iframe-fallback.md`](references/iframe-fallback.md) — when the iframe is enough
- Reference essay: [The Avatar Reads First](https://sethshoultes.com/blog/the-avatar-reads-first.html)
- HeyGen's official skills: [liveavatar-agent-skills](https://github.com/heygen-com/liveavatar-agent-skills)
