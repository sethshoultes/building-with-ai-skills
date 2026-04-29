#!/usr/bin/env python3
"""
Idempotent registration of an ElevenLabs Conversational AI client tool.

Two-step flow:
  1. POST /v1/convai/tools  → create the tool definition. Returns tool_id.
  2. PATCH /v1/convai/agents/{agent_id} → merge the new tool_id into
     conversation_config.agent.prompt.tool_ids (preserving existing entries).

Idempotency: GETs the agent's current tool_ids first. If a tool with the
same name is already attached, exits without re-creating. To force re-create,
delete the tool in the dashboard and re-run.

Required env:
  ELEVENLABS_API_KEY      xi-api-key value
  ELEVENLABS_AGENT_ID     the agent the tool attaches to
"""
import json
import os
import sys
import urllib.request
import urllib.error

API_KEY = os.environ["ELEVENLABS_API_KEY"]
AGENT_ID = os.environ["ELEVENLABS_AGENT_ID"]
BASE = "https://api.elevenlabs.io"


# ---- the tool definition ----
# Adapt this to your needs. The shape below is a fire-and-forget client tool
# (no return value expected). For tools that need to return data to the agent,
# set expects_response: true and only use the ElevenLabs SDK direct path
# (see references/handler-templates.js for which paths support which).
TOOL_DEF = {
    "tool_config": {
        "type": "client",
        "name": "show_blog_post",
        "description": (
            "Surface a clickable card on the user's screen for a blog post. "
            "Use when citing a post by title. Do NOT speak the URL — the card "
            "is already visible."
        ),
        "response_timeout_secs": 5,
        "disable_interruptions": False,
        "force_pre_tool_speech": False,
        "pre_tool_speech": "auto",
        "assignments": [],
        "tool_call_sound": None,
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
                    "enum": None,
                    "is_system_provided": False,
                    "dynamic_variable": "",
                    "constant_value": "",
                }
            },
        },
        "expects_response": False,
        "dynamic_variables": {"dynamic_variable_placeholders": {}},
        "execution_mode": "immediate",
    }
}


def call(method, path, body=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={"xi-api-key": API_KEY, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")
        sys.exit(f"\n{method} {path} → HTTP {e.code}\n{body_text}")


def main():
    tool_name = TOOL_DEF["tool_config"]["name"]

    # 1. Check if a tool with this name is already attached.
    agent = call("GET", f"/v1/convai/agents/{AGENT_ID}")
    prompt_obj = agent["conversation_config"]["agent"]["prompt"]
    existing_tool_ids = list(prompt_obj.get("tool_ids", []) or [])

    # The agent only stores tool_ids; resolve each to its name.
    existing_names = []
    for tid in existing_tool_ids:
        info = call("GET", f"/v1/convai/tools/{tid}")
        existing_names.append(info.get("tool_config", {}).get("name"))

    if tool_name in existing_names:
        idx = existing_names.index(tool_name)
        print(f"Tool '{tool_name}' already attached as {existing_tool_ids[idx]}. Nothing to do.")
        return

    # 2. Create the tool.
    print(f"Creating tool '{tool_name}'...")
    resp = call("POST", "/v1/convai/tools", TOOL_DEF)
    tool_id = resp["id"]
    print(f"  tool_id: {tool_id}")

    # 3. Attach to the agent (PATCH replaces the array — preserve existing).
    new_tool_ids = existing_tool_ids + [tool_id]
    print(f"Attaching to agent (tool_ids: {len(existing_tool_ids)} + 1 = {len(new_tool_ids)})...")
    call("PATCH", f"/v1/convai/agents/{AGENT_ID}", {
        "conversation_config": {
            "agent": {
                "prompt": {"tool_ids": new_tool_ids}
            }
        }
    })
    print("  done.")
    print()
    print("Next: update the agent's system prompt to instruct it WHEN to call")
    print("the tool. Without that paragraph, the agent has the tool but never")
    print("uses it. See references/system-prompt-additions.md.")


if __name__ == "__main__":
    main()
