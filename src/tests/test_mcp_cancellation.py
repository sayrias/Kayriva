"""Cancellation stays responsive even when an MCP transport is silent."""
import sys
import threading
import time
import unittest
from unittest.mock import patch
from ai_studio.mcp import MCPClient


class MCPCancellationTests(unittest.TestCase):
    def test_silent_stdio_initialization_can_be_cancelled(self):
        cancel=threading.Event()
        client=MCPClient({'command':sys.executable,'args':['-u','-c','import sys,time; sys.stdin.readline(); time.sleep(15)']},cancel=cancel,timeout=10)
        timer=threading.Timer(.15,cancel.set);timer.start();started=time.monotonic()
        try:
            with self.assertRaises(InterruptedError):client.open()
            self.assertLess(time.monotonic()-started,1)
            self.assertIsNone(client.process)
        finally:timer.cancel();client.close()

    def test_silent_http_can_be_cancelled_without_waiting_for_response(self):
        cancel=threading.Event();release=threading.Event()
        client=MCPClient({'transport':'http','url':'https://example.invalid/mcp'},cancel=cancel,timeout=10)
        timer=threading.Timer(.15,cancel.set);timer.start();started=time.monotonic()
        try:
            with patch.object(client,'_post',side_effect=lambda *args:release.wait(5)):
                with self.assertRaises(InterruptedError):client.request('tools/list')
            self.assertLess(time.monotonic()-started,.7)
        finally:timer.cancel();release.set();client.close()

    def test_silent_http_deadline_is_bounded(self):
        release=threading.Event();client=MCPClient({'transport':'http','url':'https://example.invalid/mcp'},timeout=.15)
        started=time.monotonic()
        try:
            with patch.object(client,'_post',side_effect=lambda *args:release.wait(5)):
                with self.assertRaises(TimeoutError):client.request('tools/list')
            self.assertLess(time.monotonic()-started,.7)
        finally:release.set();client.close()
