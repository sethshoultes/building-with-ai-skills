// avatar-token-worker
//
// Cloudflare Worker that mints a one-shot LiveAvatar session token for a
// browser page. The page calls GET / on this worker; the worker calls
// LiveAvatar's session-token endpoint with the long-lived API key (kept as
// a worker secret) and returns the short-lived sessionToken to the browser.
//
// Required env vars (set via `wrangler secret put` for secrets, in
// wrangler.toml for the others):
//
//   LIVEAVATAR_API_KEY            (secret)  LiveAvatar API key
//   HEYGEN_ELEVENLABS_SECRET_ID   (secret)  HeyGen secret id wrapping the
//                                           ElevenLabs API key
//   AVATAR_ID                     (var)     LiveAvatar avatar UUID
//   ELEVENLABS_AGENT_ID           (var)     ElevenLabs Conversational AI agent
//   ALLOWED_ORIGINS               (var)     comma-separated list of origins
//                                           allowed to call this worker
//
// Deploy:
//   wrangler secret put LIVEAVATAR_API_KEY
//   wrangler secret put HEYGEN_ELEVENLABS_SECRET_ID
//   wrangler deploy

const SUCCESS_CODE = 1000; // LiveAvatar API "ok" code

function corsHeaders(origin, allowedSet) {
  if (!origin || !allowedSet.has(origin)) return {};
  return {
    "Access-Control-Allow-Origin": origin,
    "Access-Control-Allow-Methods": "GET, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function jsonResponse(body, init = {}, headers = {}) {
  return new Response(JSON.stringify(body), {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "Cache-Control": "no-store",
      ...headers,
    },
  });
}

async function handleTokenMint(request, env, cors) {
  if (request.method !== "GET") {
    return jsonResponse({ error: { code: "METHOD_NOT_ALLOWED" } }, { status: 405 }, cors);
  }
  if (!env.LIVEAVATAR_API_KEY) {
    return jsonResponse(
      { error: { code: "NOT_CONFIGURED", message: "LIVEAVATAR_API_KEY missing." } },
      { status: 503 }, cors
    );
  }
  if (!env.HEYGEN_ELEVENLABS_SECRET_ID) {
    return jsonResponse(
      { error: { code: "NOT_CONFIGURED", message: "HEYGEN_ELEVENLABS_SECRET_ID missing." } },
      { status: 503 }, cors
    );
  }

  try {
    const upstream = await fetch("https://api.liveavatar.com/v1/sessions/token", {
      method: "POST",
      headers: {
        // LiveAvatar uses uppercase X-API-KEY — case matters on their edge.
        "X-API-KEY": env.LIVEAVATAR_API_KEY,
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        mode: "LITE",
        avatar_id: env.AVATAR_ID,
        is_sandbox: false,
        elevenlabs_agent_config: {
          secret_id: env.HEYGEN_ELEVENLABS_SECRET_ID,
          agent_id: env.ELEVENLABS_AGENT_ID,
          dynamic_variables: {},
        },
      }),
    });

    const payload = await upstream.json();
    if (!upstream.ok || payload.code !== SUCCESS_CODE || !payload.data) {
      return jsonResponse(
        { error: { code: "UPSTREAM", message: `LiveAvatar mint failed (${upstream.status} ${payload.message ?? ""}).` } },
        { status: 502 }, cors
      );
    }

    return jsonResponse(
      { sessionToken: payload.data.session_token, sessionId: payload.data.session_id },
      { status: 200 }, cors
    );
  } catch (err) {
    return jsonResponse(
      { error: { code: "FETCH_FAILED", message: "Could not reach LiveAvatar." } },
      { status: 502 }, cors
    );
  }
}

export default {
  async fetch(request, env) {
    const allowed = new Set(
      (env.ALLOWED_ORIGINS || "").split(",").map((s) => s.trim()).filter(Boolean)
    );
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin, allowed);

    if (request.method === "OPTIONS") {
      return new Response(null, { status: 204, headers: cors });
    }

    const url = new URL(request.url);
    if (url.pathname === "/" || url.pathname === "") {
      return handleTokenMint(request, env, cors);
    }

    return jsonResponse({ error: { code: "NOT_FOUND" } }, { status: 404 }, cors);
  },
};
