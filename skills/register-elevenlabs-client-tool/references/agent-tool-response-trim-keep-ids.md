# Trimming a tool's response — keep IDs even if you don't speak them

A common mistake when wiring a `expects_response: true` tool: the agent will read aloud whatever you return. So the instinct is to trim the response down to a clean human-readable string before returning it.

Don't trim too far. Specifically: **keep the IDs in the structured payload, even if the system prompt instructs the agent never to speak them.**

## Why

The agent does two things with a tool response:

1. **Speaks** about it in the next turn (governed by the system prompt).
2. **Conditions** subsequent tool calls on it (the LLM uses the response as context for future turns in the same conversation).

If a later turn needs to call another tool with that same ID — for example, "fetch_order_details" after "list_user_orders" — the LLM needs the ID in its context. Trimming the IDs out makes the later tool call impossible (the LLM has to ask the user to repeat the order number, which feels broken).

## The pattern

Return the full structured payload. Use the system prompt to control what's spoken.

```js
fetch_user_orders: async ({ user_id }) => {
  const orders = await fetchOrders(user_id);
  // Don't strip order.id — keep IDs for later tool calls.
  return JSON.stringify(orders);
}
```

In the system prompt:

> When you receive a list of orders from the fetch_user_orders tool, summarize
> them in human language. Do NOT read order IDs aloud — they're for internal
> reference. Say "your most recent order" or "the one from <date>" instead.
> If the user asks about a specific order, call fetch_order_details with the
> matching ID from the previous response.

## What to actually trim

- **Tokens of overhead** — e.g., remove `_metadata`, `_pagination` blobs that bloat context without adding LLM-relevant info.
- **PII the agent doesn't need** — credit card numbers, SSNs. Mask before returning.
- **Internal-only flags** — `is_test_data: false`, debug fields.

Keep:
- IDs (any field ending `_id`, `id`, `uuid`)
- Human-readable names and titles (the agent uses these to disambiguate)
- Timestamps (the agent uses these to say "your most recent ___")
- Status fields (`active`, `cancelled`, `pending`)

## Example

Bad — agent can summarize but can't follow up:

```json
[
  {"date": "2026-04-01", "items": 3, "total": "$48.00"},
  {"date": "2026-03-12", "items": 1, "total": "$22.00"}
]
```

Good — agent has what it needs for follow-ups:

```json
[
  {"id": "ord_abc123", "date": "2026-04-01", "items": 3, "total": "$48.00", "status": "shipped"},
  {"id": "ord_def456", "date": "2026-03-12", "items": 1, "total": "$22.00", "status": "delivered"}
]
```

The system prompt is what keeps `ord_abc123` from being spoken. The structured payload is what makes the next tool call possible.
