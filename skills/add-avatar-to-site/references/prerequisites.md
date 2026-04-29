# Prerequisites

If any of these are missing, set them up before working through the SKILL.md.

## 1. LiveAvatar account + custom avatar

LiveAvatar (HeyGen) is the streaming-video product, distinct from regular HeyGen video generation. It has its own credit pool and its own API key.

1. Sign up at [liveavatar.com](https://liveavatar.com).
2. Train (or upload) a custom avatar. The avatar must be a **streaming** avatar — the regular HeyGen avatar variant doesn't work with LiveAvatar streaming sessions and will return cryptic 401/422 responses. Confirm in the dashboard that the avatar shows up under "LiveAvatar" / "Streaming," not just under "HeyGen Video."
3. Capture the **avatar UUID**. This is what you'll set as `AVATAR_ID` in the worker.

## 2. ElevenLabs account + Conversational AI agent

The avatar's voice and brain run on an ElevenLabs Conversational AI agent in LITE mode. You need:

1. An ElevenLabs account with a Conversational AI agent created.
2. The **agent ID** — alphanumeric (e.g. `jCFMMenhYBsub2QvAHal`). From the Conversational AI dashboard.
3. (Optional but recommended) A voice clone. The default voices work, but a clone makes the avatar sound right.

## 3. HeyGen-side ElevenLabs secret

LiveAvatar's session-token mint needs HeyGen's reference to the ElevenLabs API key, not the key itself.

1. Go to `app.heygen.com/settings/secrets`.
2. Create a new secret: "ElevenLabs API key" → paste your `ELEVENLABS_API_KEY`.
3. Capture the **secret ID** HeyGen returns. This is what you'll set as `HEYGEN_ELEVENLABS_SECRET_ID` in the worker.

## 4. Canonical secrets

Per the canonical-secrets pattern, these go in `~/.config/dev-secrets/secrets.env`:

```
LIVEAVATAR_API_KEY=...
ELEVENLABS_API_KEY=...
HEYGEN_ELEVENLABS_SECRET_ID=...
HEYGEN_API_KEY=...   # only if you also use regular HeyGen video generation
```

Never paste these into a project's `.env` or commit them.

## 5. Cloudflare account + Wrangler

The worker is deployed via Wrangler:

```bash
npm install -g wrangler
wrangler login
```

A free Cloudflare Workers plan handles the token-mint volume for most personal sites. The endpoint is read once per call start, so request volume is low.

## 6. Domain origin allowlist

Decide upfront which origins are allowed to call the worker. Typical:

```
ALLOWED_ORIGINS=https://yoursite.com,http://localhost:8080
```

Add the production domain and a localhost variant for dev. Don't wildcard.
