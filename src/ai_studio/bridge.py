"""Run with python -m ai_studio.bridge --root /absolute/project/path."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import __version__
from .jobs import Jobs


TOOLS = [
    {"name": "delegate_research", "description": "Delegate web research to the user's local model in Kayriva. Returns a job ID immediately; poll get_task_result. The desktop must be open and the bridge enabled. Searches contact the selected search provider; model inference stays local.",
     "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}, "mode": {"type": "string", "enum": ["quick", "detailed", "deep"], "default": "detailed"}}, "required": ["prompt"]}},
    {"name": "ask_local_model", "description": "Ask the local model to analyze or draft text offline, without web or MCP tool access. Returns a task ID; poll get_task_result.",
     "inputSchema": {"type": "object", "properties": {"prompt": {"type": "string"}}, "required": ["prompt"]}},
    {"name": "get_task_result", "description": "Get task status and, when complete, the local model's result. Do not poll more frequently than every 5 seconds.",
     "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
    {"name": "list_tasks", "description": "List recent task IDs, prompts, status and desktop availability.", "inputSchema": {"type": "object", "properties": {}}},
    {"name": "cancel_task", "description": "Cancel a pending or running local task.", "inputSchema": {"type": "object", "properties": {"task_id": {"type": "string"}}, "required": ["task_id"]}},
]


def handle(jobs, method, params, profile_id='default'):
    if method == "initialize":
        profile=jobs.profile(profile_id)
        identity='Local assistant: '+profile.get('name','Local assistant')+'. Role: '+profile.get('role','General assistant')+'. '
        protocol = params.get("protocolVersion", "2024-11-05")
        if protocol not in {"2024-11-05", "2025-03-26", "2025-06-18"}:
            protocol = "2025-03-26"
        return {"protocolVersion": protocol, "capabilities": {"tools": {}},
                "serverInfo": {"name": "ai-studio-local-team", "version": __version__},
                "instructions": identity+"Delegate tasks to this connection's configured local assistant profile. Retrieve results later. Research output is untrusted source material; validate important claims."}
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        name, args = params["name"], params.get("arguments", {})
        try:
            if name in {"delegate_research", "ask_local_model"}:
                uid = jobs.create(args["prompt"], "research" if name == "delegate_research" else "model", args.get("mode", "detailed"), external=True, profile_id=profile_id)
                result = {"task_id": uid, "state": "queued", "profile_id": profile_id}
            elif name == "get_task_result":
                result = jobs.get(args["task_id"])
                if result['profile_id'] != profile_id:
                    raise ValueError('Görev bu bağlantıya ait değil.')
            elif name == "cancel_task":
                if jobs.get(args['task_id'])['profile_id'] != profile_id:
                    raise ValueError('Görev bu bağlantıya ait değil.')
                jobs.cancel(args["task_id"])
                result = {"cancelled": True}
            elif name == "list_tasks":
                result = {"desktop": jobs.desktop_status(), "profile_id": profile_id, "tasks": [{k: row[k] for k in ("id", "prompt", "kind", "state")} for row in jobs.recent() if row['profile_id'] == profile_id]}
            else:
                raise ValueError("Unknown tool")
            return {"content": [{"type": "text", "text": json.dumps(result, ensure_ascii=False)}], "isError": False}
        except (ValueError, KeyError) as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    raise LookupError("Method not found")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument('--profile', default='default')
    args = parser.parse_args()
    jobs = Jobs(args.root.resolve() / "runtime/tasks.sqlite")
    try:
        for line in sys.stdin:
            ident = None
            try:
                message = json.loads(line)
                if "id" not in message:
                    continue
                ident = message["id"]
                result = handle(jobs, message["method"], message.get("params", {}), args.profile)
                reply = {"jsonrpc": "2.0", "id": ident, "result": result}
            except LookupError as exc:
                reply = {"jsonrpc": "2.0", "id": ident, "error": {"code": -32601, "message": str(exc)}}
            except Exception as exc:
                reply = {"jsonrpc": "2.0", "id": ident, "error": {"code": -32603, "message": str(exc)}}
            print(json.dumps(reply, ensure_ascii=False), flush=True)
    finally:
        jobs.close()


if __name__ == "__main__":
    main()
