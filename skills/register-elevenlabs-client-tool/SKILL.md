---
name: register-elevenlabs-client-tool
description: |
  Register a browser-side client tool on an ElevenLabs Conversational AI agent so the agent can call functions that run in the user's browser — surfacing UI (cards, modals, navigations, embedded media) on the page next to the avatar. Use when: (1) the user wants the agent to "show" something on the page, not just say it, (2) the user mentions "client tools," "tool calling," "function calling," "render a card," "open a link from the agent," (3) the user already has a working avatar/chat surface and wants to add an interactive layer. Skip when the desired side effect is server-side (sending an email, updating a CRM) — use a server-side webhook tool registration instead.
license: MIT
metadata:
  author: sethshoultes
  version: "1.0.0"
  reference_post: https://sethshoultes.com/blog/skills-as-sops.html
---

# Register a client tool on an ElevenLabs agent

A client tool is a function the agent can invoke that runs in the user's browser. The agent decides to call the tool; ElevenLabs ships the call to the page over a data channel; the page's tool handler runs (typically rendering UI). The agent can keep talking while the page renders.

The pattern: a two-step API flow on the agent side (create the tool, attach by id), plus a handler in the page's JavaScript that listens for the right event and executes the side effect. The reference implementation is the `show_blog_post` tool on the Seth-clone agent at sethshoultes.com — when the agent cites a post, a card surfaces on the page with the post's image, title, and "Read it" link.

## The three-way protocol

Tool calling is three-way. **All three must align** or the tool looks-almost-right but never fires:

1. **The LLM must know the tool exists.** This is the agent registration step (the agent's `prompt.tool_ids` array references the tool definition).
2. **The orchestrator (ElevenLabs) must route the call.** Handled automatically once the tool is registered.
3. **The client (browser) must execute.** This is the handler in the page's JS that listens for the tool-call event and renders.

Break any one and the other two keep working in a way that looks plausible. Symptom of a missing piece (1): the agent emits literal JSON in its spoken response (e.g., `{"tool":"show_blog_post","slug":"the-toll-dropped"}` read aloud). Symptom of a missing piece (3): the agent calls the tool, the WebSocket emits the event, no card appears.

See *[ElevenLabs Custom LLM Tool Passthrough](https://github.com/sethshoultes/brain/blob/main/learnings/ElevenLabs%20Custom%20LLM%20Tool%20Passthrough.md)* (private) for the longer treatment.

## Step 1 — Lock the inputs

1. **Agent ID.** As with all agent skills.
2. **`ELEVENLABS_API_KEY`.** Canonical secrets.
3. **The browser-side handler.** Often you'll write this first — get the rendering UX right, then register the tool. The handler subscribes to the SDK's `ELEVENLABS_AGENT_EVENT` (LiveAvatar Plugin path) or a similar SDK event, dispatches on `elevenlabs_event_type === "client_tool_call"` and `data.tool_name === "<your_tool>"`, and runs the side effect.

## Step 2 — Create the tool definition

POST `/v1/convai/tools` with the canonical client-tool shape:

```json
{
  "tool_config": {
    "type": "client",
    "name": "show_blog_post",
    "description": "Surface a clickable card on the user's screen for a blog post. Use when citing a post by title. Do NOT speak the URL — the card is already visible.",
    "response_timeout_secs": 5,
    "disable_interruptions": false,
    "force_pre_tool_speech": false,
    "pre_tool_speech": "auto",
    "assignments": [],
    "tool_call_sound": null,
    "tool_call_sound_behavior": "auto",
    "tool_error_handling_mode": "auto",
    "parameters": {
      "type": "object",
      "required": ["slug"],
      "description": "",
      "properties": {
        "slug": {
          "type": "string",
          "description": "The post's URL slug (no .html extension).",
          "enum": null,
          "is_system_provided": false,
          "dynamic_variable": "",
          "constant_value": ""
        }
      }
    },
    "expects_response": false,
    "dynamic_variables": {"dynamic_variable_placeholders": {}},
    "execution_mode": "immediate"
  }
}
```

Response: `{"id":"tool_..."}`. Capture the id.

**Critical fields:**

- **`type: "client"`** — runs in the browser, NOT a server-side webhook.
- **`expects_response`** — when `true`, the agent waits for the tool's return value before continuing speech. **On the LiveAvatar SDK + ElevenLabs Plugin path, set this to `false`** — the SDK doesn't expose a way to send tool-call results back through the data channel, so a `true` value causes the agent to time out at `response_timeout_secs`. On the ElevenLabs SDK direct path (no LiveAvatar), `true` works.
- **`response_timeout_secs: 5`** — short for fire-and-forget tools, longer (10–15s) for tools that do real work.
- **`description`** — the agent only calls the tool when its description matches the moment. Be specific: when to call, what it does, what NOT to do (especially: "do not speak the URL").

## Step 3 — Attach the tool to the agent

PATCH the agent with the merged `tool_ids` array (existing + new):

```bash
curl -X PATCH "https://api.elevenlabs.io/v1/convai/agents/$AGENT_ID" \
  -H "xi-api-key: $ELEVENLABS_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"conversation_config":{"agent":{"prompt":{"tool_ids":["tool_existing_1","tool_existing_2","tool_new"]}}}}'
```

**Gotcha — PATCH replaces arrays.** GET the existing `tool_ids` first, append, then PATCH the full combined list.

## Step 4 — Update the system prompt

Without prompt instructions, the agent has the tool but doesn't know when to call it. Add a paragraph:

> When you cite a post by title, ground an answer in a specific essay, or recommend a post for further reading, ALSO call the show_blog_post tool with that post's slug. The tool surfaces a clickable card on the user's screen. After calling it, do NOT speak the URL — say something like "I just put a card up for that on your screen" or "the card on your screen has the full post" instead. Call the tool once per post per call.

PATCH the agent with `prompt.prompt` set to the existing prompt + this insertion. (Don't blow away the existing prompt — append.)

## Step 5 — Wire the browser handler

For the **LiveAvatar SDK + ElevenLabs Plugin** path:

```js
import { LiveAvatarSession, AgentEventsEnum } from "@heygen/liveavatar-web-sdk";

const session = new LiveAvatarSession(token, { voiceChat: true });
session.on(AgentEventsEnum.ELEVENLABS_AGENT_EVENT, (event) => {
  if (event.elevenlabs_event_type === "client_tool_call" &&
      event.data?.tool_name === "show_blog_post") {
    const slug = event.data.parameters?.slug;
    renderCard(slug); // your UI render
  }
});
```

For the **ElevenLabs SDK direct** path (no LiveAvatar):

```js
import { Conversation } from "@elevenlabs/client";

const conversation = await Conversation.startSession({
  agentId: "...",
  clientTools: {
    show_blog_post: ({ slug }) => {
      renderCard(slug);
      return "card surfaced"; // expects_response: true here works
    }
  }
});
```

The two paths are different. Pick the one that matches the SDK in use.

## Step 6 — Add a fallback (passive transcription scan)

Don't rely solely on the explicit tool. Subscribe to `AVATAR_TRANSCRIPTION` events too, scan for known titles/keywords, and render cards as a fallback. Belt and suspenders. The explicit tool gives precision; the transcription scan gives coverage when the agent paraphrases or skips the tool.

## When NOT to use this skill

- **Server-side side effects** — sending email, writing to a CRM, charging a card. Use a webhook tool (`type: "webhook"`) that hits a server endpoint you control. Add as a separate skill.
- **Reading data into the conversation** — for "fetch the user's order status" type calls, the agent needs the result spoken back. That requires `expects_response: true`, which doesn't work on the LiveAvatar Plugin path. Use the ElevenLabs SDK direct path for those agents.

## Trigger phrases

- "Make the agent show me cards"
- "Register a client tool on my ElevenLabs agent"
- "Have the avatar render UI on the page"
- "Add function calling to my Conversational AI agent"
- "Surface blog post cards when the avatar mentions a post"

## Companion skills

- **add-avatar-to-site** — the avatar surface where the client tool fires.
- **add-rag-to-elevenlabs-agent** — when the agent cites posts via RAG, the tool surfaces them. The two compose naturally.

## References

- [`references/registration-script.py`](references/registration-script.py) — idempotent two-step registration
- [`references/handler-templates.js`](references/handler-templates.js) — both SDK paths
- [`references/agent-tool-response-trim-keep-ids.md`](references/agent-tool-response-trim-keep-ids.md) — when trimming tool responses, keep IDs even if the agent shouldn't speak them
- [`references/dynamic-variables.md`](references/dynamic-variables.md) — passing per-session context (visitor source, mobile vs desktop) to the agent via dynamicVariables
- ElevenLabs official tool docs: https://elevenlabs.io/docs/agents-platform/customization/tools/client-tools
- Reference essay: [Skills as SOPs](https://sethshoultes.com/blog/skills-as-sops.html)
