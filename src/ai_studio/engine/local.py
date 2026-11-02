from __future__ import annotations

import json
import math
import os
import re
import secrets
import socket
import subprocess
import threading
import time
from pathlib import Path
from .install import default_binary
from .memory import context_limit, allocation_context, plan_memory, effective_cache

import httpx


def sse_events(lines):
    """Yield complete SSE data events, including events spanning several lines."""
    data = []
    for line in lines:
        if line == "":
            if data:
                yield "\n".join(data)
                data = []
        elif line.startswith("data:"):
            data.append(line[5:].lstrip(" "))
    if data:
        yield "\n".join(data)


class LocalEngine:
    def __init__(self, config):
        self.config = config
        self.process = None
        self.url = ""
        self.key = secrets.token_urlsafe(32)
        self.signature = None
        self.log = None
        self.lock = threading.RLock()
        self.memory_plan = None
        self.supports_fit = False
        self.device_cache = None

    def settings_signature(self, model, binary):
        s = self.config.settings
        signature = (str(model), str(binary), s.context, s.threads, s.acceleration,
                     s.gpu_layers, s.kv_cache, s.ram_budget_gb, s.vram_budget_gb)
        # Keep the original signature for the default profile and old live sessions.
        if getattr(s, 'memory_profile', 'balanced') != 'balanced' or getattr(s, 'mmproj_path', ''):
            signature += (getattr(s, 'memory_profile', 'balanced'), getattr(s, 'mmproj_path', ''))
        return signature

    def binary(self):
        path = Path(self.config.settings.binary_path).expanduser() if self.config.settings.binary_path else default_binary(self.config.root)
        if not path.is_file():
            raise RuntimeError("Modeli çalıştıracak motor eksik. Ayarlar → Genel → Yerel motor listesinden bir motor seçip Kur’a bas.")
        return path.resolve()

    def resident_plan(self):
        """A live matching model keeps its loading budget, not today's free space."""
        if not self.process or self.process.poll() is not None or not self.memory_plan:
            return None
        s=self.config.settings
        try:
            signature=self.settings_signature(self.config.model_path(), self.binary())
        except (OSError,RuntimeError):
            return None
        return self.memory_plan if self.signature==signature else None

    def command(self, binary, model, port):
        s = self.config.settings
        layers = 0 if s.acceleration == "cpu" else (999 if s.acceleration == "gpu" else max(0,s.gpu_layers))
        if self.memory_plan:
            layers = self.memory_plan.layers
            if self.memory_plan.gpu_available and s.acceleration=='hybrid' and s.gpu_layers<0 and self.supports_fit:
                layers = 'auto'
        cache = effective_cache(s)
        low_memory = getattr(s, 'memory_profile', 'balanced') == 'low_memory'
        if cache not in {"f16", "q8_0", "q4_0"}:
            raise ValueError("Geçersiz KV cache türü")
        cmd = [str(binary), "--model", str(model), "--host", "127.0.0.1", "--port", str(port),
               "--api-key", self.key, "--ctx-size", str(self.memory_plan.context if self.memory_plan else context_limit(s,model)), "--parallel", "1", "--threads", str(s.threads),
               "--n-gpu-layers", str(layers), "--batch-size", "128" if low_memory else "256", "--ubatch-size", "32" if low_memory else "128",
               "--cache-type-k", cache, "--cache-type-v", cache, "--jinja", "--offline", "--no-webui", "--no-context-shift"]
        if cache != "f16":
            cmd += ["--flash-attn", "on"]
        projector = getattr(s, 'mmproj_path', '')
        if projector:
            path = Path(projector).expanduser()
            if not path.is_file():
                raise ValueError('Görsel projektör dosyası bulunamadı. Genel ayarlarda modelle eşleşen mmproj GGUF dosyasını seç.')
            with path.open('rb') as stream:
                if stream.read(4) != b'GGUF':
                    raise ValueError('Görsel projektör bir GGUF dosyası olmalı.')
            cmd += ['--mmproj', str(path.resolve()), '--no-mmproj-offload']
        if layers == 'auto':
            cmd += ['--fit','on','--fit-target',str(max(0,math.ceil(self.memory_plan.vram_margin*1024)))]
        if self.memory_plan and not self.memory_plan.gpu_available:
            cmd += ['--device','none','--no-op-offload']
        return cmd

    def device_info(self, binary):
        signature = (str(binary),binary.stat().st_mtime_ns)
        info = {'available':False, 'counters':{}}
        try:
            env = {k:v for k,v in os.environ.items() if not k.startswith('LLAMA_ARG_')}
            result = subprocess.run([str(binary),'--list-devices'],capture_output=True,text=True,timeout=8,cwd=binary.parent,env=env)
            text = result.stdout + result.stderr
            lines = [line for line in text.splitlines() if re.match(r'^\s*(CUDA|Vulkan|Metal|HIP|ROCm|SYCL|OpenCL|CANN|MUSA)\w*:',line)]
            info['available'] = result.returncode==0 and bool(lines)
            if lines:
                memory = re.search(r'(\d+)\s*MiB,\s*(\d+)\s*MiB free',lines[0])
                if memory:
                    total,free = map(int,memory.groups())
                    info['counters'] = {'vram_total':total/1024,'vram_used':(total-free)/1024}
            if not self.device_cache or self.device_cache[0]!=signature:
                help_result = subprocess.run([str(binary),'--help'],capture_output=True,text=True,timeout=8,cwd=binary.parent,env=env)
                self.supports_fit = '--fit-target' in help_result.stdout
        except (OSError,subprocess.TimeoutExpired):
            pass
        self.device_cache = (signature,info)
        return info

    def ensure(self, cancel: threading.Event, status=lambda _: None, messages=None, tools=None):
        with self.lock:
            model = self.config.model_path()
            if model is None or not model.is_file():
                raise RuntimeError("Model bulunamadı. Modeller bölümünden indir veya kendi GGUF dosyanı seç.")
            with model.open("rb") as f:
                if f.read(4) != b"GGUF":
                    raise ValueError("Bu motor GGUF dosyası bekliyor. Safetensors için Ayarlar’dan Transformers motorunu seç.")
            binary = self.binary()
            s = self.config.settings
            capacity = allocation_context(s, model, messages, tools)
            signature = self.settings_signature(model, binary)
            if self.process and self.process.poll() is None and self.signature == signature and self.memory_plan and self.memory_plan.context >= capacity:
                status(f"Yerel model hazır · {self.memory_plan.context:,} token çalışma bağlamı")
                return
            self.stop()
            status('Bellek bütçesi kontrol ediliyor…')
            from ..resources import snapshot
            device = self.device_info(binary)
            counters = snapshot()
            counters.update(device['counters'])
            self.memory_plan = plan_memory(s,model,counters,gpu_available=device['available'], context=capacity)
            if s.acceleration=='hybrid' and not self.memory_plan.gpu_available:
                status('GPU kullanılamıyor · CPU + RAM ile devam ediliyor')
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            self.url = f"http://127.0.0.1:{port}"
            folder = self.config.runtime / 'logs'
            folder.mkdir(parents=True, exist_ok=True)
            log_path = folder / 'engine.log'
            if log_path.exists() and log_path.stat().st_size > 2_000_000:
                log_path.replace(folder / 'engine.previous.log')
            self.log = log_path.open('a', encoding='utf-8')
            log_path.chmod(0o600)
            # Environment flags cannot redirect or enable downloads in the private engine.
            env = {k: v for k, v in os.environ.items() if not k.startswith("LLAMA_ARG_")}
            try:
                self.process = subprocess.Popen(self.command(binary, model, port), stdout=self.log, stderr=self.log,
                                                env=env, cwd=binary.parent)
            except Exception:
                self.stop()
                raise
            self.signature = signature
            status(f"Model belleğe yükleniyor · {capacity:,} token çalışma bağlamı…")
            deadline = time.monotonic() + 300
            with httpx.Client(trust_env=False, timeout=2) as client:
                while time.monotonic() < deadline:
                    if cancel.is_set():
                        self.stop()
                        raise InterruptedError("Durduruldu")
                    if self.process.poll() is not None:
                        self.stop()
                        raise RuntimeError("Motor başlatılamadı. runtime/logs/engine.log dosyasını kontrol et; CUDA kullanıyorsan sürücüyü ve model uyumluluğunu doğrula.")
                    try:
                        response = client.get(self.url + "/health", headers={"Authorization": f"Bearer {self.key}"})
                        if response.status_code == 200:
                            status("Yerel model hazır")
                            return
                    except httpx.HTTPError:
                        pass
                    cancel.wait(0.3)
            self.stop()
            raise TimeoutError("Model 5 dakika içinde hazır olamadı.")

    def stream(self, messages, tools, cancel, emit, status=lambda _: None):
        if any(isinstance(m.get('content'), list) and any(p.get('type') == 'image_url' for p in m['content']) for m in messages):
            if not getattr(self.config.settings, 'mmproj_path', ''):
                raise ValueError('Fotoğraf incelemek için görsel destekli bir model ve ona ait mmproj dosyası gerekli. Ayarlar → Genel → Görsel projektör bölümünden seç.')
        self.ensure(cancel, status, messages, tools)
        if cancel.is_set():
            return {'role':'assistant','content':''}
        status('Mesaj işleniyor…')
        s = self.config.settings
        payload = {"model": "local", "messages": messages, "stream": True,
                   "temperature": s.temperature, "max_tokens": s.max_tokens,
                   "stream_options": {"include_usage": True}, "timings_per_token": True,
                   "chat_template_kwargs": {"enable_thinking": s.deep_thinking},
                   "reasoning_effort": "high" if s.deep_thinking else "none"}
        if tools:
            payload.update(tools=tools, tool_choice="auto")
        usage = None
        calls = {}
        content = ""
        reasoning = ""
        finish_reason = None
        with httpx.Client(trust_env=False, timeout=httpx.Timeout(600, connect=5, read=600)) as client:
            finished = threading.Event()
            active_response = [None]
            def monitor_cancel():
                while not finished.wait(.1):
                    if cancel.is_set():
                        response = active_response[0]
                        if response is None:
                            # Stop the owned process if it has not sent headers yet.
                            self.stop()
                        else:
                            network = response.extensions.get('network_stream')
                            sock = network.get_extra_info('socket') if network else None
                            if sock:
                                try:
                                    sock.shutdown(socket.SHUT_RDWR)
                                except OSError:
                                    pass
                            try:
                                response.close()
                            except (OSError, RuntimeError, httpx.HTTPError):
                                pass
                        return
            monitor = threading.Thread(target=monitor_cancel,daemon=True)
            monitor.start()
            try:
                with client.stream("POST", self.url + "/v1/chat/completions", json=payload,
                                   headers={"Authorization": f"Bearer {self.key}"}) as response:
                    active_response[0] = response
                    if response.status_code != 200:
                        response.read()
                        raise RuntimeError(f"Model yanıtı alınamadı ({response.status_code}); motor günlüğünü kontrol et.")
                    for raw in sse_events(response.iter_lines()):
                        if cancel.is_set():
                            break
                        if raw == "[DONE]":
                            break
                        event = json.loads(raw)
                        if event.get("error"):
                            raise RuntimeError(str(event["error"]))
                        if event.get('usage'):
                            u = event['usage']
                            usage = {'input':u.get('prompt_tokens',0), 'output':u.get('completion_tokens',0), 'cached':u.get('prompt_tokens_details',{}).get('cached_tokens',0), 'exact':True}
                        elif event.get('timings'):
                            t = event['timings']
                            if 'prompt_n' in t and 'predicted_n' in t:
                                usage = {'input':t['prompt_n']+t.get('cache_n',0), 'output':t['predicted_n'], 'cached':t.get('cache_n',0), 'exact':True}
                        if usage is not None and getattr(self, 'usage_callback', None):
                            self.usage_callback(usage)
                        for choice in event.get("choices", []):
                            if choice.get('finish_reason'):
                                finish_reason = choice['finish_reason']
                            delta = choice.get("delta", {})
                            piece = delta.get("content") or ""
                            content += piece
                            if piece:
                                emit(piece)
                            thought = delta.get("reasoning_content") or ""
                            if thought and not reasoning:
                                status('Derin düşünme sürüyor…')
                            reasoning += thought
                            for part in delta.get("tool_calls", []):
                                call = calls.setdefault(part["index"], {"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                                if part.get("id"):
                                    call["id"] = part["id"]
                                for key in ("name", "arguments"):
                                    call["function"][key] += part.get("function", {}).get(key) or ""
            except httpx.HTTPError:
                if not cancel.is_set():
                    raise
            finally:
                finished.set()
                monitor.join(timeout=2)
        result = {"role": "assistant", "content": content}
        if calls and not cancel.is_set():
            result["tool_calls"] = list(calls.values())
        if reasoning:
            result["reasoning_content"] = reasoning
        if usage is not None:
            result['_usage'] = usage
        if finish_reason:
            result['_finish_reason'] = finish_reason
        return result

    def stop(self):
        with self.lock:
            if self.process:
                if self.process.poll() is None:
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        self.process.wait()
                self.process = None
            if self.log:
                self.log.close()
                self.log = None
            self.signature = None
            self.memory_plan = None
