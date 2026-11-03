from __future__ import annotations

import json
import os
import queue
import re
import subprocess
import threading
import time
from collections import deque
from urllib.parse import urlparse

import httpx

from .engine.local import sse_events
from . import __version__


class MCPClient:
    """MCP tools client: newline stdio and POST JSON/SSE Streamable HTTP.

    Supports tools and pagination. Does not advertise sampling, elicitation,
    roots, OAuth, or the legacy HTTP+SSE transport.
    """

    def __init__(self, spec, offline=False, *, cancel=None, timeout=90):
        self.spec = spec
        self.offline = offline
        self.cancel = cancel if cancel is not None else threading.Event()
        self.timeout = max(.1, min(90, float(timeout)))
        self.aborted = False
        self.process = None
        self.http = None
        self.session = None
        self.incoming = queue.Queue()
        self.logs = deque(maxlen=40)
        self.seq = 0
        self.protocol = "2025-03-26"
        self._lock = threading.RLock()

    def check_cancelled(self):
        if self.cancel.is_set():
            self.aborted = True
            raise InterruptedError("MCP işlemi durduruldu")

    def open(self):
        try:
            self.check_cancelled()
            if self.spec.get("transport", "stdio") == "stdio":
                command = self.spec["command"]
                env = os.environ.copy()
                for key, value in self.spec.get("env", {}).items():
                    env[key] = str(value)
                self.process = subprocess.Popen([command, *self.spec.get("args", [])], stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", bufsize=1,
                    env=env, cwd=self.spec.get("cwd") or None)
                threading.Thread(target=self._reader, daemon=True).start()
                threading.Thread(target=self._stderr, daemon=True).start()
            else:
                url = self.spec["url"]
                if urlparse(url).scheme not in {"http", "https"}:
                    raise ValueError("MCP adresi HTTP(S) olmalı")
                if self.offline and urlparse(url).hostname not in {"127.0.0.1", "localhost", "::1"}:
                    raise ValueError("Çevrimdışı modda uzak MCP kapalı")
                headers = dict(self.spec.get("headers", {}))
                for header, variable in self.spec.get("header_env", {}).items():
                    if not os.environ.get(variable):
                        raise ValueError(f"MCP için {variable} ortam değişkeni gerekli")
                    headers[header] = os.environ[variable]
                self.http = httpx.Client(trust_env=False, timeout=httpx.Timeout(self.timeout, connect=min(10,self.timeout)), headers=headers)
            result = self.request("initialize", {"protocolVersion": self.protocol, "capabilities": {},
                "clientInfo": {"name": "Kayriva", "version": __version__}})
            self.protocol = result["protocolVersion"]
            self.notify("notifications/initialized")
            return self
        except Exception:
            self.close()
            raise

    def _reader(self):
        for line in self.process.stdout:
            try:
                value = json.loads(line)
                for message in value if isinstance(value, list) else [value]:
                    self.incoming.put(message)
            except ValueError:
                self.logs.append("Sunucu stdout’a geçersiz JSON yazdı")
        self.incoming.put(None)

    def _stderr(self):
        for line in self.process.stderr:
            self.logs.append(line.rstrip())

    def _post(self, message, expected=None):
        headers = {"Accept": "application/json, text/event-stream", "MCP-Protocol-Version": self.protocol}
        if self.session:
            headers["Mcp-Session-Id"] = self.session
        with self.http.stream("POST", self.spec["url"], json=message, headers=headers) as response:
            response.raise_for_status()
            if response.headers.get("Mcp-Session-Id"):
                self.session = response.headers["Mcp-Session-Id"]
            if response.status_code in {202, 204}:
                return None
            if "text/event-stream" in response.headers.get("content-type", ""):
                events = (json.loads(raw) for raw in sse_events(response.iter_lines()))
            else:
                response.read()
                events = iter([response.json()])
            for value in events:
                self.check_cancelled()
                for item in value if isinstance(value, list) else [value]:
                    if item.get("id") == expected and "method" not in item:
                        return item
                    if "method" in item and "id" in item:
                        reply = self._server_reply(item)
                        self._post(reply)
        return None

    def _send(self, message):
        if self.process:
            self.process.stdin.write(json.dumps(message, ensure_ascii=False) + "\n")
            self.process.stdin.flush()
        else:
            # Poll a daemon request so a silent HTTP/SSE server cannot keep the
            # caller waiting after cancellation. Socket timeouts still bound it.
            replies = queue.Queue(maxsize=1)
            def post():
                try:replies.put((True,self._post(message,message.get("id"))))
                except Exception as exc:replies.put((False,exc))
            threading.Thread(target=post,daemon=True,name='mcp-http').start()
            deadline=time.monotonic()+self.timeout
            while True:
                self.check_cancelled()
                remaining=deadline-time.monotonic()
                if remaining<=0:
                    self.aborted=True
                    raise TimeoutError("MCP yanıt süresi aşıldı")
                try:ok,value=replies.get(timeout=min(.1,remaining))
                except queue.Empty:continue
                if not ok:raise value
                return value

    def notify(self, method, params=None):
        message = {"jsonrpc": "2.0", "method": method}
        if params is not None:
            message["params"] = params
        self._send(message)

    @staticmethod
    def _server_reply(message):
        if message["method"] == "ping":
            return {"jsonrpc": "2.0", "id": message["id"], "result": {}}
        return {"jsonrpc": "2.0", "id": message["id"], "error": {"code": -32601, "message": "Client capability not supported"}}

    def request(self, method, params=None):
        with self._lock:
            self.check_cancelled()
            self.seq += 1
            ident = self.seq
            message = {"jsonrpc": "2.0", "id": ident, "method": method, "params": params or {}}
            result = self._send(message)
            if self.process:
                deadline = time.monotonic() + self.timeout
                while time.monotonic() < deadline:
                    self.check_cancelled()
                    try:
                        item = self.incoming.get(timeout=min(.1, max(0.01, deadline - time.monotonic())))
                    except queue.Empty:
                        continue
                    if item is None:
                        raise RuntimeError("MCP sunucusu kapandı: " + "\n".join(self.logs)[-1000:])
                    if "method" in item:
                        if "id" in item:
                            self._send(self._server_reply(item))
                        continue
                    if item.get("id") == ident:
                        result = item
                        break
            if not result:
                raise TimeoutError(f"MCP yanıt vermedi: {method}")
            if "error" in result:
                raise RuntimeError(result["error"].get("message", "MCP hatası"))
            return result.get("result", {})

    def tools(self):
        all_tools, cursor, seen = [], None, set()
        for _ in range(100):
            result = self.request("tools/list", {"cursor": cursor} if cursor else {})
            all_tools.extend(result.get("tools", []))
            cursor = result.get("nextCursor")
            if not cursor:
                return all_tools
            if cursor in seen:
                raise RuntimeError("MCP sayfalama döngüsü")
            seen.add(cursor)
        raise RuntimeError("MCP araç sayısı sınırı aşıldı")

    def call(self, name, arguments):
        return self.request("tools/call", {"name": name, "arguments": arguments})

    def close(self):
        if self.process:
            if self.process.poll() is None:
                self.process.terminate()
                try:
                    self.process.wait(3)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait()
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream:
                    stream.close()
            self.process = None
        if self.http:
            if self.session and not self.cancel.is_set() and not self.aborted:
                try:
                    self.http.delete(self.spec["url"], headers={"Mcp-Session-Id": self.session,
                                                              "MCP-Protocol-Version": self.protocol}, timeout=3)
                except httpx.HTTPError:
                    pass
            self.http.close()
            self.http = None


def tool_alias(server_index, name):
    return f"mcp_{server_index}_" + re.sub(r"[^A-Za-z0-9_-]", "_", name)[:45]
