import hashlib,json,tempfile,unittest
from pathlib import Path
from ai_studio.workspace import call_workspace,resolve_file,root_output_requested,root_output_arguments

class WorkspaceTests(unittest.TestCase):
    def test_single_file_request_uses_project_root_without_implicit_directories(self):
        query='pythona giriş için detaylı bi araştırma yapıp şuanki açık proje klasöründe bi dosya oluştur'
        self.assertTrue(root_output_requested(query))
        self.assertFalse(root_output_requested('yeni bir klasör oluştur ve içine bir dosya oluştur'))
        self.assertFalse(root_output_requested('notes/report.md dosyasını oluştur'))
        with tempfile.TemporaryDirectory() as raw:
            args=root_output_arguments(raw,'workspace_write',{'path':'python_giris/rehber.md','mode':'create','content':'Araştırma'})
            call_workspace(raw,'workspace_write',args)
            self.assertEqual(list(Path(raw).iterdir()),[Path(raw)/'rehber.md'])
            with self.assertRaises(ValueError):root_output_arguments(raw,'workspace_mkdir',{'path':'python_giris'})
            with self.assertRaises(ValueError):root_output_arguments(raw,'workspace_write',{'path':'../outside.md','mode':'create','content':'no'})

    def test_create_read_append_edit_replace_and_mkdir(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)
            call_workspace(root,'workspace_mkdir',{'path':'notes'})
            call_workspace(root,'workspace_write',{'path':'notes/report.md','mode':'create','content':'Türkçe araştırma\n'})
            read=json.loads(call_workspace(root,'workspace_read',{'path':'notes/report.md'}))
            self.assertEqual(read['content'],'Türkçe araştırma\n')
            self.assertEqual(read['sha256'],hashlib.sha256(read['content'].encode()).hexdigest())
            call_workspace(root,'workspace_write',{'path':'notes/report.md','mode':'append','content':'Kaynaklar\n'})
            call_workspace(root,'workspace_edit',{'path':'notes/report.md','old_text':'Kaynaklar','new_text':'Doğrulanan kaynaklar'})
            read=json.loads(call_workspace(root,'workspace_read',{'path':'notes/report.md'}))
            call_workspace(root,'workspace_write',{'path':'notes/report.md','mode':'replace','content':'Tamamlandı','expected_sha256':read['sha256']})
            self.assertEqual((root/'notes/report.md').read_text(),'Tamamlandı')

    def test_existing_file_and_changed_content_are_preserved(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw);file=root/'report.txt';file.write_text('keep')
            with self.assertRaises(FileExistsError):call_workspace(root,'workspace_write',{'path':'report.txt','mode':'create','content':'destroy'})
            with self.assertRaises(ValueError):call_workspace(root,'workspace_write',{'path':'report.txt','mode':'replace','content':'destroy','expected_sha256':'outdated'})
            with self.assertRaises(ValueError):call_workspace(root,'workspace_edit',{'path':'report.txt','old_text':'missing','new_text':'destroy'})
            self.assertEqual(file.read_text(),'keep')

    def test_write_cannot_escape_project_or_touch_private_files(self):
        with tempfile.TemporaryDirectory() as raw:
            root=Path(raw)/'project';root.mkdir();(root/'link').symlink_to(Path(raw))
            for path in ['../outside.txt','link/outside.txt','.env.local','.git/config','/tmp/outside.txt']:
                with self.assertRaises(ValueError):call_workspace(root,'workspace_write',{'path':path,'mode':'create','content':'no'})
            self.assertFalse((Path(raw)/'outside.txt').exists())
            with self.assertRaises(ValueError):call_workspace(root,'workspace_write',{'path':'large.txt','mode':'create','content':'a'*150001})
            self.assertFalse((root/'large.txt').exists())
