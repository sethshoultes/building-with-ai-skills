// Browser-side handlers for client-tool calls. Two SDK paths — they're
// different, pick the one that matches your integration.

// ============================================================
// Path A — LiveAvatar SDK + ElevenLabs Plugin (LITE mode)
// ============================================================
// This is the path the avatar pages on sethshoultes.com use. The LiveAvatar
// SDK proxies ElevenLabs events through a single ELEVENLABS_AGENT_EVENT.
// Tool-call events arrive as:
//   { elevenlabs_event_type: "client_tool_call", data: { tool_name, parameters } }
//
// CRITICAL: in this path, expects_response MUST be false on the tool definition.
// The SDK doesn't expose a way to send tool-call results back through the data
// channel — setting expects_response: true causes the agent to time out at
// response_timeout_secs.

import { LiveAvatarSession, AgentEventsEnum } from "@heygen/liveavatar-web-sdk";

const session = new LiveAvatarSession(sessionToken, { voiceChat: true });

session.on(AgentEventsEnum.ELEVENLABS_AGENT_EVENT, (event) => {
  const evType = event?.elevenlabs_event_type;
  const data = event?.data || {};

  if (evType !== "client_tool_call") return;

  // CRITICAL: ElevenLabs wraps tool calls one level deeper than the obvious
  // shape — `data.client_tool_call.tool_name`, NOT `data.tool_name`. Some SDK
  // paths may flatten, so read defensively. A silent mismatch here means the
  // tool fires (per the conversation transcript) but the page UI never reacts.
  const tool = data.client_tool_call || data;
  const toolName = tool.tool_name || data.tool_name;
  const params = tool.parameters || data.parameters || {};

  switch (toolName) {
    case "show_blog_post": {
      const slug = params.slug;
      if (slug) renderCard(slug); // your UI renderer
      break;
    }
    case "another_tool": {
      // ... handle another tool ...
      break;
    }
    default:
      // Unknown tool — log full event so future you can diagnose without grepping.
      console.warn("Unhandled client tool:", toolName, "raw:", event);
  }
});

// Optional: belt-and-suspenders fallback. Subscribe to AVATAR_TRANSCRIPTION
// and scan for known titles/keywords. Useful when the agent paraphrases or
// skips the tool. The explicit tool gives precision; the scan gives coverage.
session.on(AgentEventsEnum.AVATAR_TRANSCRIPTION, (event) => {
  scanForKnownTitles(event?.text || "");
});

// ============================================================
// Path B — ElevenLabs SDK direct (no LiveAvatar)
// ============================================================
// When the agent powers a chat or voice surface that's NOT going through
// LiveAvatar, use the ElevenLabs SDK directly. This path supports
// expects_response: true — the handler's return value is sent back to the
// agent and shows up in the next LLM turn.

import { Conversation } from "@elevenlabs/client";

const conversation = await Conversation.startSession({
  agentId: "<AGENT_ID>",
  clientTools: {
    show_blog_post: ({ slug }) => {
      renderCard(slug);
      return "card surfaced"; // expects_response: true → agent sees this
    },
    fetch_user_orders: async ({ user_id }) => {
      const orders = await fetch(`/api/orders/${user_id}`).then(r => r.json());
      // Return data the agent can speak about. Be careful what you return —
      // anything in the response can be spoken aloud by the agent unless its
      // system prompt is instructed otherwise.
      return JSON.stringify(orders);
    },
  },
  // Other startSession options (overrides, dynamicVariables, etc.) here.
});

// ============================================================
// Picking a path
// ============================================================
// - You have an avatar (HeyGen LiveAvatar)        → Path A
// - You have voice/chat WITHOUT an avatar          → Path B
// - You need server-side side effects (email, DB)  → neither — use a webhook
//                                                    tool (type: "webhook")
//                                                    that hits your server.
//
// Path A and Path B can coexist if you have two separate surfaces (e.g., an
// avatar page AND a text chat widget) — the SAME agent with the SAME tool_ids
// works for both, but the handler code is different.
