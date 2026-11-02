from __future__ import annotations

import gc
import queue
import threading
from pathlib import Path
from .memory import context_limit, plan_memory


class TransformersEngine:
    """Optional in-process backend; loads only local files, never remote code.

    Text generation only. Prequantized GPTQ/AWQ checkpoints additionally
    require the compatible quantizer package. GGUF is preferred for tools and
    fine-grained CPU/GPU layer placement.
    """

    def __init__(self, config):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.signature = None

    def ensure(self, cancel, status=lambda _: None):
        try:
            import torch
            from transformers import AutoConfig, AutoTokenizer, AutoModelForCausalLM, AutoModelForImageTextToText, BitsAndBytesConfig
        except ImportError as exc:
            raise RuntimeError("Transformers ek kurulumu gerekli. engine/README.md içindeki yerel Safetensors kurulumunu tamamla.") from exc
        s = self.config.settings
        path = Path(s.model_path).expanduser().resolve() if s.model_path else None
        if not path or not path.is_dir() or not (path / "config.json").exists():
            raise ValueError("Yerel Transformers model klasörü seç: config.json, tokenizer ve ağırlık dosyaları gerekli.")
        signature = (str(path), s.acceleration, s.transformer_dtype,s.ram_budget_gb,s.vram_budget_gb)
        if self.model is not None and signature == self.signature:
            return
        self.stop()
        status("Yerel Safetensors modeli yükleniyor…")
        gpu = s.acceleration != 'cpu' and torch.cuda.is_available()
        if s.acceleration == 'gpu' and not gpu:
            raise ValueError("PyTorch CUDA cihazı bulamadı; CPU modunu seç veya sürücüyü kontrol et.")
        if s.acceleration == 'hybrid' and not gpu:
            status('GPU bulunamadı · Transformers CPU + RAM ile hazırlanıyor')
        kwargs = {"local_files_only": True, "trust_remote_code": False, "device_map": "auto" if gpu else "cpu"}
        plan = plan_memory(s,path,gpu_available=gpu and torch.cuda.is_available())
        if gpu:
            kwargs['max_memory']={0:f'{max(1,int(plan.vram_budget*1024))}MiB','cpu':f'{max(1,int(plan.ram_budget*1024))}MiB'}
        dtype = s.transformer_dtype
        if dtype in {"int8", "nf4"}:
            if not gpu:
                raise ValueError("bitsandbytes INT8/NF4 için bu sürümde CUDA GPU modu gerekli. CPU’da 2/4/8 bit için GGUF kullan.")
            kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=dtype == "int8", load_in_4bit=dtype == "nf4", bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
            kwargs["dtype"] = torch.float16
        else:
            kwargs["dtype"] = "auto" if dtype == "auto" else getattr(torch, dtype)
        config = AutoConfig.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        loader = AutoModelForImageTextToText if hasattr(config, "vision_config") else AutoModelForCausalLM
        self.tokenizer = AutoTokenizer.from_pretrained(path, local_files_only=True, trust_remote_code=False)
        self.model = loader.from_pretrained(path, **kwargs)
        self.model.eval()
        self.signature = signature
        if cancel.is_set():
            self.stop()
            raise InterruptedError("Durduruldu")
        status("Yerel Transformers modeli hazır")

    def stream(self, messages, tools, cancel, emit, status=lambda _: None):
        if any(isinstance(m.get('content'), list) for m in messages):
            raise ValueError('Bu Transformers yolu metin içindir. Fotoğraf için GGUF görsel model ve eşleşen mmproj projektörü kullan.')
        if tools:
            raise ValueError("Transformers motoru bu sürümde yalnızca metin üretir. Araçlar kutusunu kapat veya MCP için GGUF motoruna geç.")
        self.ensure(cancel, status)
        import torch
        from transformers import TextIteratorStreamer, StoppingCriteria, StoppingCriteriaList
        s = self.config.settings
        encoded = self.tokenizer.apply_chat_template(messages, tokenize=True, add_generation_prompt=True, return_tensors="pt", return_dict=True, enable_thinking=s.deep_thinking)
        prompt_tokens = encoded['input_ids'].shape[-1]
        remaining = context_limit(s,self.config.model_path()) - prompt_tokens
        if remaining <= 0:
            raise ValueError('Girdi seçili bağlamı doldurdu; yeni sohbet aç veya bağlamı artır.')
        budget = remaining if s.max_tokens <= 0 else min(s.max_tokens, remaining)
        encoded = {key: value.to(self.model.device) for key, value in encoded.items()}
        callback = getattr(self, 'usage_callback', None)
        class CountingStreamer(TextIteratorStreamer):
            count = 0
            initial = True
            def put(self, value):
                if self.initial:
                    self.initial = False
                else:
                    self.count += value.numel()
                if callback:
                    callback({'input':prompt_tokens,'output':self.count,'cached':0,'exact':True})
                super().put(value)
        streamer = CountingStreamer(self.tokenizer, skip_prompt=True, skip_special_tokens=True, timeout=1)
        class Stop(StoppingCriteria):
            def __call__(self, input_ids, scores, **kwargs):
                return cancel.is_set()
        errors, generated = [], []
        def generate():
            try:
                with torch.inference_mode():
                    options = {"max_new_tokens": budget, "do_sample": s.temperature > 0,
                               "streamer": streamer, "stopping_criteria": StoppingCriteriaList([Stop()])}
                    if s.temperature > 0:
                        options["temperature"] = s.temperature
                    generated.append(self.model.generate(**encoded, **options))
            except Exception as exc:
                errors.append(exc)
                streamer.end()
        generation = threading.Thread(target=generate, daemon=True)
        generation.start()
        text = ""
        try:
            while True:
                try:
                    piece = next(streamer)
                    text += piece
                    emit(piece)
                except queue.Empty:
                    if not generation.is_alive():
                        break
                except StopIteration:
                    break
        finally:
            generation.join()
        if errors:
            raise errors[0]
        output_tokens = max(0, generated[0].shape[-1] - prompt_tokens) if generated else 0
        return {"role": "assistant", "content": text, '_usage': {'input':prompt_tokens, 'output':output_tokens, 'cached':0, 'exact':True}}

    def stop(self):
        self.model = None
        self.tokenizer = None
        self.signature = None
        gc.collect()
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except ImportError:
            pass
