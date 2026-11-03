import threading,unittest
import time
from unittest.mock import patch
import httpx
from ai_studio.config import Settings
from ai_studio.research import Research,Source,PageText

class ResearchTests(unittest.TestCase):
    def test_large_research_is_bounded_and_distributes_page_reads_across_sites(self):
        import hashlib
        from urllib.parse import urlparse
        research=Research(Settings());read=[]
        def search(query,count):
            slug=hashlib.sha256(query.encode()).hexdigest()[:12]
            return [Source('Guide',f'https://site{n%7}.example/{slug}/{n}','Summary') for n in range(count)]
        def page(url,cancel):read.append(url);return 'Actual source contents '*100
        with patch.object(research,'search',side_effect=search),patch.object(research,'read_page',side_effect=page):
            sources=research.run('Python giriş','deep',threading.Event())
        self.assertEqual(len(sources),200)
        self.assertEqual(len(read),60)
        self.assertEqual(len({urlparse(s['url']).hostname for s in sources[:7]}),7)
        self.assertLessEqual(len(research.context(sources,budget=4000)),4000)
        self.assertGreater(research.context(sources).count('Okunan metin:'),18)

    def test_deep_has_eighteen_queries_without_model_planning_and_reads_sources(self):
        research=Research(Settings());queries=[];read=[];statuses=[]
        def search(query,count):
            queries.append(query)
            n=len(query)
            return [Source('Source '+str(n),'https://example.org/'+str(n),'snippet')]
        def page(url,cancel):read.append(url);return 'Verified source content '*20
        with patch.object(research,'search',side_effect=search),patch.object(research,'read_page',side_effect=page):
            sources=research.run('Python başlangıç şu anki proje klasöründe dosya oluştur','deep',threading.Event(),statuses.append)
        self.assertEqual(len(queries),18)
        self.assertFalse(any('klasör' in q for q in queries))
        self.assertGreater(len(read),1)
        self.assertTrue(all(s.get('text') for s in sources))
        self.assertIn('Okunan metin:',research.context(sources))
        self.assertIn('metin incelendi',statuses[-1])

    def test_quick_does_not_fetch_pages_and_failed_reads_are_reported(self):
        research=Research(Settings());results=[Source('Guide','https://example.org/guide','summary')]
        with patch.object(research,'search',return_value=results),patch.object(research,'read_page',side_effect=RuntimeError('unavailable')) as read:
            quick=research.run('Guide','quick',threading.Event());read.assert_not_called()
            detailed=research.run('Guide','detailed',threading.Event())
        self.assertFalse(quick[0].get('text'))
        self.assertIn('yalnızca',detailed[0]['read_error'])
        self.assertIn('Kaynak metni alınamadı',research.context(detailed))

    def test_page_reader_extracts_text_and_rejects_private_redirect(self):
        research=Research(Settings());original=httpx.Client
        seen=[]
        def handler(request):
            seen.append(str(request.url))
            if request.url.path=='/redirect':return httpx.Response(302,headers={'location':'http://127.0.0.1/secret'})
            return httpx.Response(200,headers={'content-type':'text/html'},text='<nav>Navigation</nav><script>hidden()</script><h1>Python guide</h1><p>'+('Meaningful instructions. '*20)+'</p>')
        def address(host,*args,**kwargs):return [(2,1,6,'',('127.0.0.1' if host=='127.0.0.1' else '93.184.216.34',443))]
        with patch('ai_studio.research.socket.getaddrinfo',side_effect=address),patch('ai_studio.research.httpx.Client',side_effect=lambda **kw:original(transport=httpx.MockTransport(handler),**kw)):
            text=research.read_page('https://example.org/guide',threading.Event())
            self.assertIn('Python guide',text);self.assertNotIn('Navigation',text);self.assertNotIn('hidden()',text)
            with self.assertRaises(ValueError):research.read_page('https://example.org/redirect',threading.Event())
        self.assertFalse(any('127.0.0.1' in url for url in seen))

    def test_context_keeps_multiple_read_sources_in_a_bounded_prompt(self):
        sources=[{'title':'Guide','url':'https://example.org/'+str(n),'snippet':'summary'*100,'text':'Full source '*1000} for n in range(12)]
        context=Research.context(sources)
        self.assertLess(len(context),12000)
        self.assertIn('https://example.org/11',context)
        self.assertEqual(context.count('Okunan metin:'),12)

    def test_cancel_does_not_wait_for_blocked_search_requests(self):
        research=Research(Settings());cancel=threading.Event();release=threading.Event()
        def search(query,count):
            release.wait(2)
            return [Source('Guide','https://example.org','summary')]
        timer=threading.Timer(.1,cancel.set);timer.start();started=time.monotonic()
        try:
            with patch.object(research,'search',side_effect=search):
                with self.assertRaises(InterruptedError):research.run('Guide','deep',cancel)
            self.assertLess(time.monotonic()-started,.7)
        finally:release.set();timer.cancel()

    def test_provider_failure_opens_circuit_before_all_queries_are_scheduled(self):
        research=Research(Settings());queries=[]
        def denied(query,count):
            queries.append(query)
            raise RuntimeError('provider bot challenge')
        with patch.object(research,'search',side_effect=denied),patch.object(research,'read_page') as read:
            with self.assertRaisesRegex(RuntimeError,'provider bot challenge'):
                research.run('Guide','deep',threading.Event())
        self.assertLessEqual(len(queries),5)
        read.assert_not_called()

    def test_phase_budget_stops_blocked_requests_and_keeps_completed_sources(self):
        research=Research(Settings());release=threading.Event()
        def action(value):
            if value==0:return 'fast'
            release.wait(2)
            return 'late'
        started=time.monotonic();results=[]
        try:
            with self.assertRaises(TimeoutError):
                for future,value in research.parallel(action,range(8),threading.Event(),timeout=.15):
                    results.append(future.result())
            self.assertLess(time.monotonic()-started,.7)
            self.assertEqual(results,['fast'])
        finally:release.set()

    def test_completed_search_is_checkpointed_before_page_read_cancel(self):
        research=Research(Settings());cancel=threading.Event();saved=[]
        research.on_sources=lambda sources:saved.append([dict(source) for source in sources])
        def page(url,event):
            cancel.set()
            raise InterruptedError('Stopped')
        with patch.object(research,'search',return_value=[Source('Guide','https://example.org','Summary')]),patch.object(research,'read_page',side_effect=page):
            with self.assertRaises(InterruptedError):
                research.run('Guide','detailed',cancel)
        self.assertTrue(saved)
        self.assertEqual(saved[0][0]['url'],'https://example.org')
