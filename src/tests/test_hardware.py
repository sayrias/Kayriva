import json
import struct
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from ai_studio.config import Config
from ai_studio.hardware import Hardware, cpu_limit, model_limits


class HardwareTests(unittest.TestCase):
    def test_cpu_affinity_and_saved_cpu_profile(self):
        with patch('ai_studio.hardware.os.cpu_count', return_value=24), patch('ai_studio.hardware.os.sched_getaffinity', return_value=set(range(12)), create=True):
            self.assertEqual(cpu_limit(), 12)
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / 'runtime').mkdir()
            (root / 'runtime/settings.json').write_text(json.dumps({'threads': 24, 'hardware_vram_gb': 0}))
            with patch('ai_studio.config.cpu_limit', return_value=12), patch('ai_studio.config.detect', return_value=Hardware(12,32,8)):
                config = Config(root)
                self.assertEqual(config.settings.threads, 12)
                self.assertEqual(config.settings.hardware_ram_gb, 32)
                self.assertEqual(config.settings.hardware_vram_gb, 0)

    def test_gguf_ignores_vision_limits_and_rejects_truncated_arrays(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'test.gguf'
            entries = [('qwen35.block_count', 32), ('qwen35.context_length', 32768), ('qwen35.vision.block_count', 27)]
            data = b'GGUF' + struct.pack('<IQQ', 3, 0, len(entries))
            for key, value in entries:
                raw = key.encode()
                data += struct.pack('<Q',len(raw)) + raw + struct.pack('<II',4,value)
            path.write_bytes(data)
            self.assertEqual(model_limits(path), {'layers':32, 'context':32768})
            raw = b'tokenizer.ggml.tokens'
            data = data[:16] + struct.pack('<Q',4) + data[24:]
            data += struct.pack('<Q',len(raw)) + raw + struct.pack('<IIQ',9,4,100)
            path.write_bytes(data)
            self.assertEqual(model_limits(path), {})

    def test_transformers_reads_text_config_without_importing_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'config.json').write_text(json.dumps({'num_hidden_layers':27,'text_config':{'num_hidden_layers':32,'max_position_embeddings':8192},'auto_map':{'AutoModel':'custom.RemoteCode'}}))
            self.assertEqual(model_limits(root), {'layers':32,'context':8192})
            (root/'config.json').write_text('broken')
            self.assertEqual(model_limits(root), {})

    def test_detection_keeps_raw_bytes_without_rounding_hardware_limit(self):
        from types import SimpleNamespace
        from ai_studio.hardware import detect
        detect.cache_clear()
        try:
            def sysconf(key):
                return 4096 if key=='SC_PAGE_SIZE' else 4_000_123
            with patch('ai_studio.hardware.os.sysconf',side_effect=sysconf),patch('ai_studio.hardware.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='GPU, 5177\n')):
                result=detect()
            self.assertEqual(result.ram_bytes,4096*4_000_123)
            self.assertEqual(result.vram_bytes,5177*1024**2)
        finally:
            detect.cache_clear()

    def test_snapshot_distinguishes_total_and_available_vram_in_bytes(self):
        from types import SimpleNamespace
        from ai_studio.resources import snapshot
        with patch('ai_studio.resources.subprocess.run',return_value=SimpleNamespace(returncode=0,stdout='967, 6144, 12\n')):
            values=snapshot()
        self.assertEqual(values['vram_total_bytes'],6144*1024**2)
        self.assertEqual(values['vram_available_bytes'],5177*1024**2)
