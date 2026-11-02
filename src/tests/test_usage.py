import tempfile
import unittest
from pathlib import Path
from datetime import datetime, timedelta

from ai_studio.usage import Usage
from ai_studio.local_logging import configure, failure


class UsageTests(unittest.TestCase):
    def test_local_periods_models_and_restart(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'usage.sqlite'
            usage = Usage(path)
            now = datetime(2026,10,5,12)
            for days, model, exact in [(0,'Model A',True),(2,'Model B',False),(20,'Model A',True),(40,'Model B',True)]:
                usage.add({'model':model,'input':100,'output':50,'cached':10,'seconds':2,'exact':exact},(now-timedelta(days=days)).isoformat(timespec='seconds'))
            usage.add({'model':'Model A','state':'failed','input':0,'output':0},now.isoformat(timespec='seconds'))
            total,chart,models = usage.report('day',now)
            self.assertEqual((total['requests'],total['input'],total['output'],total['failed']),(2,100,50,1))
            total,chart,models = usage.report('week',now)
            self.assertEqual((total['requests'],total['estimated'],len(chart)),(3,1,7))
            self.assertEqual(sum(n for _,n in chart),300)
            self.assertEqual(len(models),2)
            self.assertEqual(usage.report('month',now)[0]['input'],300)
            self.assertEqual(usage.report('all',now)[0]['input'],400)
            usage.close()
            usage=Usage(path)
            self.assertEqual(usage.report('all',now)[0]['requests'],5)
            usage.close()

    def test_logs_keep_failure_type_and_locations_without_exception_content(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=configure(Path(temp))
            try:
                raise ValueError('private-token-123')
            except ValueError as exc:
                failure('Test operation',exc)
            text=(folder/'app.log').read_text()
            self.assertIn('ValueError',text)
            self.assertIn('Test operation',text)
            # Source lines may contain arbitrary values, so logs must exclude source text too.
            self.assertNotIn('private-token-123',text)
