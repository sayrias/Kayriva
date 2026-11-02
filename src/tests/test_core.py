import json
import os
import sys
import tempfile
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from ai_studio.config import Config
from ai_studio.engine.local import LocalEngine, sse_events
from ai_studio.jobs import Jobs
from ai_studio.mcp import MCPClient
from ai_studio.storage import History
from ai_studio.workspace import resolve_file, list_files


class CoreTests(unittest.TestCase):
    def test_project_removal_preserves_chats_and_files(self):
        with tempfile.TemporaryDirectory() as raw:
            path = Path(raw)
            file = path / "keep.txt"
            file.write_text("content")
            history = History(path / "chats.db")
            project = history.add_project("Proje", raw)
            chat = history.create("Sohbet", project)
            history.append(chat, [{"role": "user", "content": "merhaba"}])
            self.assertEqual(history.project_chats(project)[0][0], chat)
            history.remove_project(project)
            self.assertEqual(history.recent()[0][0], chat)
            self.assertEqual(history.messages(chat)[0]["content"], "merhaba")
            self.assertEqual(file.read_text(), "content")
            history.close()

    def test_workspace_rejects_traversal_and_symlink_escape(self):
        with tempfile.TemporaryDirectory() as raw:
            root = Path(raw) / "workspace"
            root.mkdir()
            (root / "file.py").write_text("print(1)")
            (root / "secret").symlink_to(Path(raw) / "private")
            (root / ".aws").mkdir()
            (root / ".aws/credentials").write_text("private")
            for value in ["../private", "secret", ".aws/credentials"]:
                with self.assertRaises(ValueError):
                    resolve_file(root, value)
            self.assertEqual(list_files(root), ["file.py"])

    def test_queue_requires_live_enabled_desktop_and_claims_once(self):
        with tempfile.TemporaryDirectory() as raw:
            jobs = Jobs(Path(raw) / "jobs.db")
            with self.assertRaises(ValueError):
                jobs.create("research", external=True)
            jobs.heartbeat(True)
            uid = jobs.create("research", external=True)
            self.assertEqual(jobs.claim()["id"], uid)
            self.assertIsNone(jobs.claim())
            jobs.finish(uid, "complete", "answer")
            self.assertEqual(jobs.get(uid)["result"], "answer")
            jobs.close()

    def test_bridge_real_stdio_lifecycle_and_queue(self):
        with tempfile.TemporaryDirectory() as raw:
            jobs = Jobs(Path(raw) / "runtime/tasks.sqlite")
            jobs.heartbeat(True)
            spec = {"command": sys.executable, "args": ["-m", "ai_studio.bridge", "--root", raw],
                    "env": {"PYTHONPATH": str(Path(__file__).resolve().parents[1])}}
            client = MCPClient(spec).open()
            try:
                names = {t["name"] for t in client.tools()}
                self.assertIn("delegate_research", names)
                result = client.call("delegate_research", {"prompt": "Compare two runtimes", "mode": "deep"})
                uid = json.loads(result["content"][0]["text"])["task_id"]
                self.assertEqual(jobs.get(uid)["mode"], "deep")
                client.call("cancel_task", {"task_id": uid})
                self.assertEqual(jobs.get(uid)["state"], "cancelled")
            finally:
                client.close()
                jobs.close()

    def test_sse_multiline_comments_and_final_event(self):
        self.assertEqual(list(sse_events([": ping", "data: first", "data: second", "", "data: last"])), ["first\nsecond", "last"])

    def test_http_mcp_session_sse_pagination_and_delete(self):
        seen = []
        def handler(request):
            seen.append(request)
            if request.method == "DELETE":
                return httpx.Response(204)
            payload = json.loads(request.content)
            method = payload["method"]
            if method == "initialize":
                return httpx.Response(200, headers={"Mcp-Session-Id": "test-session"}, json={"jsonrpc": "2.0", "id": payload["id"], "result": {"protocolVersion": "2025-03-26"}})
            self.assertEqual(request.headers["Mcp-Session-Id"], "test-session")
            if method == "notifications/initialized":
                return httpx.Response(202)
            cursor = payload["params"].get("cursor")
            result = {"tools": [{"name": "second" if cursor else "first", "inputSchema": {"type": "object"}}]}
            if not cursor:
                result["nextCursor"] = "page2"
            data = json.dumps({"jsonrpc": "2.0", "id": payload["id"], "result": result})
            return httpx.Response(200, headers={"Content-Type": "text/event-stream"}, text="event: message\ndata: " + data + "\n\n")
        original = httpx.Client
        with patch("ai_studio.mcp.httpx.Client", side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw)):
            client = MCPClient({"transport": "http", "url": "http://localhost/mcp"}).open()
            self.assertEqual([t["name"] for t in client.tools()], ["first", "second"])
            client.close()
        self.assertEqual(seen[-1].method, "DELETE")

    def test_local_engine_bind_and_memory_modes(self):
        with tempfile.TemporaryDirectory() as raw:
            config = Config(Path(raw))
            engine = LocalEngine(config)
            config.settings.gpu_layers = 12
            for mode, expected in [("cpu", "0"), ("hybrid", "12"), ("gpu", "999")]:
                config.settings.acceleration = mode
                cmd = engine.command(Path("binary"), Path("model.gguf"), 8123)
                self.assertEqual(cmd[cmd.index("--n-gpu-layers") + 1], expected)
                self.assertEqual(cmd[cmd.index("--host") + 1], "127.0.0.1")
                self.assertIn("--offline", cmd)
                self.assertIn("--no-webui", cmd)
                self.assertNotIn("--hf-repo", cmd)

    def test_model_stream_reassembles_tool_calls_and_unicode(self):
        with tempfile.TemporaryDirectory() as raw:
            engine = LocalEngine(Config(Path(raw)))
            engine.url = "http://127.0.0.1:8123"
            events = [
                {"content": "Merhaba ş", "tool_calls": [{"index": 0, "id": "call1", "function": {"name": "scene", "arguments": '{"x":'}}]},
                {"content": "imdi", "tool_calls": [{"index": 0, "function": {"arguments": '1}'}}]},
            ]
            data = "".join("data: " + json.dumps({"choices": [{"delta": e}]}, ensure_ascii=False) + "\n\n" for e in events) + "data: [DONE]\n\n"
            def handler(request):
                self.assertEqual(request.url.host, "127.0.0.1")
                self.assertEqual(json.loads(request.content)["tool_choice"], "auto")
                return httpx.Response(200, text=data, headers={"Content-Type": "text/event-stream"})
            original = httpx.Client
            chunks = []
            with patch.object(engine, "ensure"), patch("ai_studio.engine.local.httpx.Client", side_effect=lambda **kw: original(transport=httpx.MockTransport(handler), **kw)):
                result = engine.stream([], [{"type": "function"}], threading.Event(), chunks.append)
            self.assertEqual("".join(chunks), "Merhaba şimdi")
            self.assertEqual(result["tool_calls"][0]["function"]["arguments"], '{"x":1}')

    def test_engine_unlimited_and_thinking_payload_and_usage(self):
        with tempfile.TemporaryDirectory() as raw:
            config=Config(Path(raw)); config.settings.max_tokens=-1; config.settings.deep_thinking=True
            engine=LocalEngine(config); engine.url='http://127.0.0.1:8123'
            def handler(request):
                payload=json.loads(request.content)
                self.assertEqual(payload['max_tokens'],-1)
                self.assertTrue(payload['chat_template_kwargs']['enable_thinking'])
                event={'choices':[], 'usage':{'prompt_tokens':123,'completion_tokens':45,'prompt_tokens_details':{'cached_tokens':10}}}
                return httpx.Response(200,text='data: '+json.dumps(event)+'\n\ndata: [DONE]\n\n')
            original=httpx.Client
            with patch.object(engine,'ensure'), patch('ai_studio.engine.local.httpx.Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(handler),**kw)):
                result=engine.stream([],[],threading.Event(),lambda _:None)
            self.assertEqual(result['_usage'],{'input':123,'output':45,'cached':10,'exact':True})

    def test_cancel_interrupts_blocked_stream_and_preserves_partial_reply(self):
        released = threading.Event()
        cancel = threading.Event()
        class Socket:
            def shutdown(self, how):
                released.set()
        class Network:
            def get_extra_info(self, name):
                return Socket() if name == 'socket' else None
        class BlockedStream(httpx.SyncByteStream):
            def __iter__(self):
                yield b'data: {"choices":[{"delta":{"content":"Merhaba"}}]}\n\n'
                cancel.set()
                if not released.wait(3):
                    raise AssertionError('Cancellation did not interrupt the socket')
                raise httpx.ReadError('Socket closed')
        with tempfile.TemporaryDirectory() as raw:
            engine=LocalEngine(Config(Path(raw)));engine.url='http://127.0.0.1:8123'
            def handler(request):
                return httpx.Response(200,stream=BlockedStream(),extensions={'network_stream':Network()})
            original=httpx.Client;chunks=[];started=time.monotonic()
            with patch.object(engine,'ensure'), patch.object(engine,'stop') as stop, patch('ai_studio.engine.local.httpx.Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(handler),**kw)):
                result=engine.stream([],[],cancel,chunks.append)
            self.assertLess(time.monotonic()-started,1.5)
            self.assertTrue(released.is_set())
            self.assertEqual(result['content'],'Merhaba')
            self.assertEqual(chunks,['Merhaba'])
            stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
