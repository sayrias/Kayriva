import struct
import tempfile
import unittest
from pathlib import Path
from ai_studio.config import Settings
from ai_studio.engine.memory import context_limit, allocation_context, plan_memory, memory_budgets


def model(path, size=5):
    entries=[('qwen3.block_count',32),('qwen3.context_length',32768)]
    data=b'GGUF'+struct.pack('<IQQ',3,0,len(entries))
    for key,value in entries:
        key=key.encode();data+=struct.pack('<Q',len(key))+key+struct.pack('<II',4,value)
    with path.open('wb') as out:
        out.write(data);out.truncate(size*1024**3)  # Sparse test file, no model weights.


class MemoryTests(unittest.TestCase):
    def test_default_hybrid_and_adjustable_margins_limit_layers(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'test.gguf';model(path)
            settings=Settings();self.assertEqual(settings.acceleration,'hybrid')
            settings.hardware_vram_gb=6
            counters={'ram_total':16,'ram_used':3,'vram_total':6,'vram_used':1}
            plan=plan_memory(settings,path,counters)
            self.assertLessEqual(plan.vram,4);self.assertGreater(plan.layers,0)
            settings.vram_budget_gb=2;settings.gpu_layers=32
            limited=plan_memory(settings,path,counters)
            self.assertLess(limited.layers,plan.layers)
            self.assertLessEqual(limited.vram,2)

    def test_insufficient_current_free_ram_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'test.gguf';model(path,size=3)
            settings=Settings();settings.acceleration='cpu'
            with self.assertRaisesRegex(ValueError,'bellek bütçesine sığmıyor'):
                plan_memory(settings,path,{'ram_total':16,'ram_used':12},gpu_available=False)
            plan=plan_memory(settings,path,{'ram_total':16,'ram_used':2},gpu_available=False)
            self.assertEqual(plan.layers,0);self.assertFalse(plan.gpu_available)

    def test_unlimited_context_uses_model_limit_and_checks_memory(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'test.gguf';model(path)
            settings=Settings(context=0,acceleration='cpu')
            self.assertEqual(context_limit(settings,path),32768)
            with self.assertRaises(ValueError):plan_memory(settings,path,{'ram_total':8,'ram_used':1},gpu_available=False)
            with self.assertRaisesRegex(ValueError,'bağlam sınırı okunamadı'):context_limit(settings,None)

    def test_gpu_only_without_real_device_is_rejected(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'test.gguf';model(path,size=1)
            with self.assertRaisesRegex(ValueError,'GPU kullanılamıyor'):
                plan_memory(Settings(acceleration='gpu'),path,{'ram_total':16},gpu_available=False)

    def test_auto_engine_uses_fit_margin_and_disables_gpu_for_fallback(self):
        from ai_studio.config import Config
        from ai_studio.engine.local import LocalEngine
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);path=root/'test.gguf';model(path)
            config=Config(root);config.settings.model_path=str(path);config.settings.hardware_vram_gb=6
            engine=LocalEngine(config);engine.supports_fit=True
            engine.memory_plan=plan_memory(config.settings,path,{'ram_total':16,'vram_total':6})
            cmd=engine.command(Path('binary'),path,8000)
            self.assertEqual(cmd[cmd.index('--n-gpu-layers')+1],'auto')
            self.assertEqual(cmd[cmd.index('--fit-target')+1],'1024')
            engine.memory_plan=plan_memory(config.settings,path,{'ram_total':16},gpu_available=False)
            cmd=engine.command(Path('binary'),path,8000)
            self.assertEqual(cmd[cmd.index('--n-gpu-layers')+1],'0')
            self.assertIn('--no-op-offload',cmd)

    def test_memory_guard_runs_before_model_process_starts(self):
        import threading
        from unittest.mock import patch
        from ai_studio.config import Config
        from ai_studio.engine.local import LocalEngine
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);path=root/'test.gguf';model(path,size=3)
            binary=root/'llama-server';binary.write_text('unused')
            config=Config(root);config.settings.model_path=str(path);config.settings.binary_path=str(binary)
            engine=LocalEngine(config)
            with patch.object(engine,'device_info',return_value={'available':False,'counters':{}}),patch('ai_studio.resources.snapshot',return_value={'ram_total':16,'ram_used':12}),patch('ai_studio.engine.local.subprocess.Popen') as launch:
                with self.assertRaisesRegex(ValueError,'bellek bütçesine sığmıyor'):engine.ensure(threading.Event())
                launch.assert_not_called()

    def test_unlimited_allocates_small_context_then_grows_with_prompt(self):
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'test.gguf';model(path)
            settings=Settings(context=0,max_tokens=-1,acceleration='cpu')
            short=allocation_context(settings,path,[{'role':'user','content':'Merhaba'}])
            self.assertEqual(short,4096)
            long=allocation_context(settings,path,[{'role':'user','content':'a'*9000}])
            self.assertGreater(long,short)
            self.assertLessEqual(long,32768)
            plan=plan_memory(settings,path,{'ram_total':16,'ram_used':3},gpu_available=False,context=short)
            self.assertEqual(plan.context,4096)
            settings.context=2048
            self.assertEqual(allocation_context(settings,path,[{'content':'a'*9000}]),2048)

    def test_ready_context_reuses_engine_until_growth_is_needed(self):
        import threading
        from unittest.mock import Mock, patch
        from ai_studio.config import Config
        from ai_studio.engine.local import LocalEngine
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);path=root/'test.gguf';model(path)
            binary=root/'llama-server';binary.write_text('unused')
            config=Config(root);s=config.settings
            s.model_path=str(path);s.binary_path=str(binary);s.context=0;s.max_tokens=-1
            engine=LocalEngine(config)
            engine.memory_plan=plan_memory(s,path,{'ram_total':16},gpu_available=False,context=4096)
            engine.signature=(str(path),str(binary),s.context,s.threads,s.acceleration,s.gpu_layers,s.kv_cache,s.ram_budget_gb,s.vram_budget_gb)
            engine.process=Mock();engine.process.poll.return_value=None
            self.assertIs(engine.resident_plan(),engine.memory_plan)
            with patch.object(engine,'stop') as stop:
                with patch('ai_studio.resources.snapshot',side_effect=AssertionError('Resident memory must not be deducted again')):
                    engine.ensure(threading.Event(),messages=[{'content':'Merhaba'}])
                stop.assert_not_called()
            command=engine.command(binary,path,8000)
            self.assertEqual(command[command.index('--ctx-size')+1],'4096')
            self.assertEqual(command[command.index('--parallel')+1],'1')
            with patch.object(engine,'stop'),patch.object(engine,'device_info',return_value={'available':False,'counters':{}}),patch('ai_studio.resources.snapshot',return_value={'ram_total':8,'ram_used':5}),patch('ai_studio.engine.local.subprocess.Popen') as launch:
                with self.assertRaises(ValueError):
                    engine.ensure(threading.Event(),messages=[{'content':'a'*9000}])
                launch.assert_not_called()

    def test_manual_budgets_mean_memory_for_model_and_do_not_preallocate(self):
        settings=Settings(ram_budget_gb=12,vram_budget_gb=5)
        counters={'ram_total':16,'ram_used':2,'vram_total':6,'vram_used':.5}
        ram,gpu,margin=memory_budgets(settings,counters)
        self.assertEqual((ram,gpu,margin),(12,5,.5))
        settings.ram_budget_gb=14;settings.vram_budget_gb=5.5
        larger=memory_budgets(settings,counters)
        self.assertGreater(larger[0],ram);self.assertGreater(larger[1],gpu)
        counters.update(ram_used=8,vram_used=3)
        self.assertEqual(memory_budgets(settings,counters),(8,3,0))
        with tempfile.TemporaryDirectory() as raw:
            path=Path(raw)/'test.gguf';model(path,size=1)
            settings.acceleration='cpu'
            plan=plan_memory(settings,path,{'ram_total':16,'ram_used':2},gpu_available=False)
            self.assertLess(plan.ram,plan.ram_budget)

    def test_manual_vram_budget_is_passed_to_engine_fitting(self):
        from ai_studio.config import Config
        from ai_studio.engine.local import LocalEngine
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);path=root/'test.gguf';model(path)
            config=Config(root);config.settings.vram_budget_gb=3
            engine=LocalEngine(config);engine.supports_fit=True
            engine.memory_plan=plan_memory(config.settings,path,{'ram_total':16,'vram_total':6,'vram_used':1})
            cmd=engine.command(Path('binary'),path,8000)
            self.assertEqual(cmd[cmd.index('--fit-target')+1],'2048')
            self.assertLessEqual(engine.memory_plan.vram,3)

    def test_legacy_margins_migrate_without_inverting_meaning(self):
        import json
        from unittest.mock import patch
        from ai_studio.config import Config
        from ai_studio.hardware import Hardware
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);(root/'runtime').mkdir()
            path=root/'runtime/settings.json'
            path.write_text(json.dumps({'ram_reserve_gb':4,'vram_reserve_gb':2}))
            with patch('ai_studio.config.detect',return_value=Hardware(12,16,6)):
                config=Config(root)
            self.assertEqual(config.settings.ram_budget_gb,12)
            self.assertEqual(config.settings.vram_budget_gb,4)
            config.save();data=json.loads(path.read_text())
            self.assertNotIn('ram_reserve_gb',data)
            self.assertEqual(data['ram_budget_gb'],12)
            path.write_text(json.dumps({'ram_reserve_gb':2,'vram_reserve_gb':1}))
            with patch('ai_studio.config.detect',return_value=Hardware(12,16,6)):
                config=Config(root)
            self.assertEqual((config.settings.ram_budget_gb,config.settings.vram_budget_gb),(0,0))

    def test_invalid_memory_budget_is_rejected(self):
        for value in [-1,float('inf'),float('nan')]:
            with self.assertRaises(ValueError):
                memory_budgets(Settings(ram_budget_gb=value),{'ram_total':16})
