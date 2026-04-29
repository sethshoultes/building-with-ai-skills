# HeyGen credit pools and which key drains which

HeyGen actually has three credit pools, each authenticated by a different API key. Mixing them is the most common reason an integration silently fails.

| Pool | What it powers | Key that drains it |
|---|---|---|
| **HeyGen Video** | Async video generation (`POST /v2/video/generate`) | `HEYGEN_API_KEY` |
| **LiveAvatar Streaming** | Real-time WebRTC streaming sessions | `LIVEAVATAR_API_KEY` |
| **HeyGen Avatar IV** | Photo-to-video / Express avatars | `HEYGEN_API_KEY` (separate sub-pool) |

## Why mixing fails

`LIVEAVATAR_API_KEY` and `HEYGEN_API_KEY` look interchangeable — both are HeyGen-issued JWT-ish strings. They're not. The LiveAvatar streaming endpoint (`api.liveavatar.com/v1/sessions/token`) only accepts `LIVEAVATAR_API_KEY`. Sending `HEYGEN_API_KEY` returns a generic 401 with no useful guidance.

The reverse is also true: the regular HeyGen video endpoint won't accept `LIVEAVATAR_API_KEY`.

## How to tell them apart

In the dashboard:

- LiveAvatar key: `app.liveavatar.com/settings/api-keys` (or the LiveAvatar tab inside HeyGen settings)
- HeyGen Video key: `app.heygen.com/settings/api`

In the canonical secrets file, name them distinctly:

```
LIVEAVATAR_API_KEY=...
HEYGEN_API_KEY=...
```

## Which to budget

A LiveAvatar session burns credits per minute of streaming. The token mint itself is free. Set a reasonable session timeout in the page (auto-stop on silence, beforeunload cleanup) so a forgotten tab doesn't drain the pool overnight.

Sandbox mode (`is_sandbox: true`, avatar `dd73ea75-1218-4ef3-92ce-606d5f7fbc0a`) is free and ~1-minute. Use it during development.

## Header case

LiveAvatar's API uses **uppercase** `X-API-KEY`. Lowercase `x-api-key` returns 401. The worker template in this skill already handles this; if you write your own, mind the case.
