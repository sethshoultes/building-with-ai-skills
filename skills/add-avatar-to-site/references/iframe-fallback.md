# Iframe fallback — when the SDK is overkill

If the only requirement is "an avatar on the page" with no client-side branding, no transcription handling, no client tools, and no programmatic control over session lifecycle, LiveAvatar's hosted page is a one-line embed.

## When to use this

- You don't need to react to events the avatar emits (no transcription scanning, no client tools, no card surfacing).
- You're fine with LiveAvatar branding in the iframe (small "Powered by HeyGen" mark).
- The avatar lives in a section of the page, not the whole page.

## When NOT to use this

- You want to surface UI alongside the avatar based on what it says (cards, embeds, navigation).
- You need to register a custom client tool the agent can call.
- You need to mint per-user session tokens (e.g., visitor identity in the agent's dynamic variables).
- You want to wire your own controls (start/stop button, status, error UI).

For any of those, use the worker + SDK pattern in the main SKILL.md.

## The embed

```html
<iframe
  src="https://embed.liveavatar.com/?avatar=<AVATAR_ID>&agent=<AGENT_ID>"
  allow="microphone; camera; autoplay"
  width="100%"
  height="540"
  frameborder="0"
  loading="lazy">
</iframe>
```

Replace `<AVATAR_ID>` and `<AGENT_ID>` with the same IDs the worker template uses. The iframe handles its own session-token minting against LiveAvatar — no Cloudflare Worker required. The tradeoff: your account's API keys are baked into LiveAvatar's hosted page on their side, so credit billing and session limits all flow through their UI controls.

## Sizing

The iframe content is a fixed 16:9 stage. On mobile, set `height` proportionally with CSS:

```html
<iframe ... style="aspect-ratio: 16/9; width: 100%; height: auto; max-height: 70vh;"></iframe>
```

## Going from iframe to SDK later

The iframe is a fine starting point. When you outgrow it (most likely: you want to surface cards or wire a client tool), switch to the worker + SDK pattern. The agent doesn't change — same `AGENT_ID` works in both.
