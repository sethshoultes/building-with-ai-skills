# Dynamic variables — passing per-session context to the agent

Dynamic variables let you pass per-session context to the agent at session start — visitor source, mobile vs desktop, signed-in user info, A/B variant — without editing the system prompt or training a new agent. The agent can reference them in its prompt template, and tools can receive them as parameters.

## How it works

At session start, the page sends a `dynamicVariables` object. The agent's system prompt can reference any variable as `{{var_name}}`. The variables also flow into client-tool calls if the tool's parameter has `dynamic_variable: "var_name"` set.

## Setting them at session start

### Path A — LiveAvatar + ElevenLabs Plugin

Dynamic variables are part of the worker's session-token mint payload:

```js
// In the Cloudflare Worker:
body: JSON.stringify({
  mode: "LITE",
  avatar_id: env.AVATAR_ID,
  is_sandbox: false,
  elevenlabs_agent_config: {
    secret_id: env.HEYGEN_ELEVENLABS_SECRET_ID,
    agent_id: env.ELEVENLABS_AGENT_ID,
    dynamic_variables: {
      visitor_source: "homepage_cta",
      device: "desktop",
      user_first_name: "Daisy"
    }
  }
})
```

The page can pass these to the worker as query string or headers, then the worker forwards them. **Never let the page set dynamic variables directly without server-side validation** — the agent will trust whatever it receives, so unvalidated input becomes a prompt-injection vector.

### Path B — ElevenLabs SDK direct

```js
const conversation = await Conversation.startSession({
  agentId: "<AGENT_ID>",
  dynamicVariables: {
    visitor_source: "homepage_cta",
    device: "desktop",
    user_first_name: "Daisy"
  }
});
```

## Referencing in the system prompt

In the agent's system prompt, use `{{var_name}}` (Mustache-style):

```
You are <persona>. You are talking to {{user_first_name}}, who came in from
{{visitor_source}} on a {{device}}. Adjust your level of background detail
accordingly: {{visitor_source}} = "homepage_cta" means they probably haven't
heard of <topic> before. {{device}} = "mobile" means keep responses short.

If a variable isn't set, fall back to neutral phrasing — don't say "Daisy"
when the variable is empty.
```

ElevenLabs substitutes variables before sending to the LLM. Missing variables resolve to empty string (not the literal `{{name}}`).

## Threading dynamic variables into tool parameters

A tool parameter can be auto-filled from a dynamic variable rather than the agent's reasoning:

```json
{
  "name": "user_first_name",
  "type": "string",
  "dynamic_variable": "user_first_name",
  "is_system_provided": false
}
```

When the agent calls this tool, the `user_first_name` parameter will come pre-populated from the session's dynamic variable, not from the agent's choice. Useful for: passing visitor identity to a tool without the agent having to ask.

## When to use them

- **Personalization** — visitor's name, account tier, geographic region.
- **Surface-specific behavior** — same agent, slightly different prompt for `/talk/` vs `/build/`.
- **A/B tests** — pass `variant: "A"` and let the prompt branch.
- **Tool routing** — tool parameters that should always come from the session, never from agent reasoning.

## When NOT to use them

- **As a substitute for tools.** If you're tempted to pass `user_recent_orders` as a dynamic variable, you actually want a tool — variables are set once at session start, tools fire per-turn.
- **For secrets.** Anything in `dynamicVariables` is visible in the agent's session log. Don't pass API keys, tokens, or anything you wouldn't want in the LLM context.
- **For large data.** Variables are interpolated into the prompt — long values bloat every turn. For anything bigger than a name + a few flags, use a tool.
