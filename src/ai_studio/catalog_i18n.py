"""English display labels for curated metadata; no user content is rewritten."""
EN = {
'21B toplam, 3.6B etkin parametre; 16 GB üstü toplam kullanılabilir bellek adayı. Kayriva/llama.cpp sürümünde Harmony araç biçimi ayrıca denenmeli.': '21B total and 3.6B active parameters; a candidate for more than 16 GB of combined available memory. Harmony tool formatting needs separate testing with this Kayriva/llama.cpp version.',
'27B için daha az agresif sıkıştırma · RAM + GPU adayı. Yoğun RAM kullanımı ve daha yavaş üretim beklenebilir.': 'Less aggressive compression for 27B · a RAM + GPU candidate. Expect substantial RAM use and potentially slower generation.',
'Akıl yürütme': 'Reasoning', 'Akıl yürütme · MoE': 'Reasoning · MoE', 'Araç kullanımı': 'Tool use',
'Açık eğitim yaklaşımına sahip İngilizce talimat modeli. Türkçe ve araç çağırma uyumu ayrıca değerlendirilmelidir.': 'English instruction model with an open training approach. Turkish quality and tool-call compatibility need separate evaluation.',
'Büyük model': 'Large model',
'Büyük model · RAM + GPU gerekir. RTX 2060 hibrit kısa testinde yaklaşık 0,6 token/sn; düşük bit kaliteyi azaltabilir.': 'Large model · requires RAM + GPU. A short RTX 2060 hybrid test measured about 0.6 tokens/s; low-bit compression may reduce quality.',
'Daha az sıkıştırma · 16 GB sistem RAM’inde ek GPU belleği ve kısa bağlam gerekir; çalışması henüz bu cihazda doğrulanmadı. Topluluk türevi; ret davranışı, araç kullanımı ve kalite cihazında ayrıca denenmeli.': 'Less compression · 16 GB system RAM needs additional GPU memory and a short context; operation on this device has not been verified. Community derivative: test refusal behavior, tool use and quality on your hardware.',
'Daha yüksek kalite · bu bilgisayarda RAM yetersiz kalabilir; GPU katmanlarını ayarla.': 'Higher precision · available RAM may be insufficient; adjust GPU layers.',
'Depo üzerinde kod ve ajan iş akışları için metin modeli. Dosya işlemleri Kayriva araçlarıyla uygulanır; model tek başına diske erişmez.': 'Text model for repository coding and agent workflows. Kayriva tools perform file operations; the model does not access the disk by itself.',
'Eski 27B alternatifi · RAM + GPU için. Sıkıştırma kaliteyi düşürebilir. 4 GB dosya veya tamamen 4 GB VRAM iddiası yok.': 'Earlier 27B alternative · for RAM + GPU. Compression may reduce quality. This is not a 4 GB file or a promise of fitting in 4 GB VRAM.',
'Genel': 'General', 'Genel · çok dilli': 'General · multilingual',
'Gerçek model, araç kullanımı ve hız testi henüz yapılmadı. Düşük bit kalite kaybı oluşturabilir.': 'Real-model inference, tool use and speed have not been tested. Low-bit quantization may reduce quality.',
'Gerçek model, araç kullanımı ve hız testi henüz yapılmadı. Kısa bağlamla başla.': 'Real-model inference, tool use and speed have not been tested. Start with a short context.',
'Görsel inceleme': 'Image review',
'Günlük kullanım için ilk aday · 6 GB VRAM + 16 GB RAM. Kısa bağlam ve hibrit modla başla; gerçek hız henüz ölçülmedi.': 'An initial everyday candidate for 6 GB VRAM + 16 GB RAM. Start with a short context and hybrid mode; actual speed has not been measured.',
'Hafif': 'Lightweight',
'Hafif kod, işlev çağırma ve akıl yürütme seçeneği. Küçük parametre sayısı karmaşık görev güvenilirliğini garanti etmez.': 'Lightweight coding, function-calling and reasoning option. A small parameter count does not guarantee reliability on complex tasks.',
'Hafif sansürsüz seçenek · imatrix ile kuantize. Küçük dosya; bellek ve kaliteyi cihazında ölçmek gerekir. Topluluk türevi; ret davranışı, araç kullanımı ve kalite cihazında ayrıca denenmeli.': 'Lightweight uncensored option · imatrix quantization. Small file; measure memory and quality on your device. Community derivative: test refusal behavior, tools and quality separately.',
'Hafif · kod': 'Lightweight · coding', 'Hafif · çok kipli': 'Lightweight · multimodal',
'Hafif, sıkıştırılmış sansürsüz alternatif. Kalite ve araç kullanımı bu cihazda henüz ölçülmedi. Topluluk türevi; ret davranışı, araç kullanımı ve kalite cihazında ayrıca denenmeli.': 'Lightweight compressed uncensored alternative. Quality and tool use have not been measured on this device. Community derivative: evaluate refusal behavior, tools and quality separately.',
'Hibrit Mamba-Transformer MoE. 3B etkin parametre toplam 30B ağırlık belleğini ortadan kaldırmaz; küçük GPU için hızlı çalışma vaadi yoktur.': 'Hybrid Mamba-Transformer MoE. 3B active parameters do not remove the memory cost of all 30B weights; fast operation on small GPUs is not promised.',
'Hibrit Mamba-Transformer mimarisi. Güncel yerel motor gerekir; farklı GPU arka uçlarında performans değişir.': 'Hybrid Mamba-Transformer architecture. Requires a recent local runtime; performance varies between GPU backends.',
'Hızlı sohbet · RTX 2060 / CUDA ile kısa testte yaklaşık 77 token/sn. İlk yükleme ayrıca sürer; kalite kıyaslaması yapılmadı.': 'Fast chat · a short RTX 2060 / CUDA test measured about 77 tokens/s. Initial loading takes additional time; this was not a quality benchmark.',
'Kod': 'Coding',
'Kod ve akıl yürütme için büyük yoğun model. Küçük GPU için düşük bellekli veya hızlı çalışma vaadi değildir.': 'Large dense model for coding and reasoning. Not a promise of low-memory or fast operation on small GPUs.',
'Kod ve araç kullanımı odaklı MoE. Etkin 3.3B parametre bütün ağırlık belleğinin 3B olduğu anlamına gelmez.': 'MoE focused on coding and tools. 3.3B active parameters do not mean only 3B worth of weights must be stored.',
'Kod ve bilim soruları için Qwen2.5 tabanlı akıl yürütme modeli. Türkçe kalite ve cihaz hızı ölçülmedi.': 'Qwen2.5-based reasoning model for code and science questions. Turkish quality and device speed have not been measured.',
'Kod ve matematik akıl yürütmesi için Qwen2.5 tabanlı model. Derin düşünme uzun çıktılar üretebilir.': 'Qwen2.5-based model for coding and mathematical reasoning. Extended reasoning may produce long outputs.',
'Kod · akıl yürütme': 'Coding · reasoning', 'Kod · araçlar': 'Coding · tools',
'Kod, işlev çağırma ve kontrollü akıl yürütme odaklı model. Türkçe yayıncının temel dil listesinde değildir.': 'Model focused on coding, function calls and controlled reasoning. Turkish is not in the publisher’s primary language list.',
'Kod, matematik ve bilim için daha büyük akıl yürütme seçeneği. Bağlam belleği ağırlık dosyasına ayrıca eklenir.': 'Larger reasoning option for code, mathematics and science. Context memory adds to the weight file’s memory cost.',
'Kod, matematik ve bilim odaklı yoğun 32B model; büyük RAM ve GPU bütçesi gerekir. Ağır çoklu örnekleme modu Kayriva tarafından vaat edilmez.': 'Dense 32B model for coding, mathematics and science; needs substantial RAM/GPU budgets. Kayriva does not promise a heavy multi-sampling mode.',
'Küçük bellek bütçesi için genel metin modeli. Ağırlık dosyasına çalışma belleği ve bağlam maliyeti eklenir.': 'General text model for a small memory budget. Working memory and context add to the weight file’s requirements.',
'Küçük hibrit Mamba-Transformer model. Yayıncı İngilizce ve kod odaklıdır; Türkçe yeterliliği ölçülmedi.': 'Small hybrid Mamba-Transformer model. The publisher focuses on English and code; Turkish proficiency has not been measured.',
'Küçük sohbet ve araç kullanımı modeli. Ağırlık lisansı Apache değildir; ticari kullanım için yayıncının koşullarını incele.': 'Small chat and tool-use model. The weight license is not Apache; review the publisher’s terms for commercial use.',
'Küçük çift modlu akıl yürütme ve araç kullanımı modeli. Düşünme süresi, kullanılan şablona ve göreve bağlıdır.': 'Small dual-mode reasoning and tool-use model. Reasoning time depends on the template and task.',
'Küçük İngilizce sohbet ve araç kullanımı modeli. NVIDIA model lisansı geçerlidir; araç sonuçları kullanıcı tarafından denetlenmelidir.': 'Small English chat and tool-use model. NVIDIA model license applies; users should review tool results.',
'Kısa ve hedefli işlev çağırma için eğitilmiş, düşünme üretmeyen model. Araç biçimi ve karmaşık görev başarısı motora bağlıdır.': 'Non-reasoning model trained for short, targeted function calls. Tool formatting and complex-task success depend on the runtime.',
'Kısıtlı bellek için kod odaklı talimat modeli. Küçük boyut, büyük proje değişikliklerinde aynı doğruluğu garanti etmez.': 'Coding instruction model for limited memory. Small size does not guarantee the same accuracy on large project changes.',
'Kısıtlı bellek için kompakt hibrit model. Liquid lisans koşulları geçerlidir; Türkçe ve karmaşık kod performansı ölçülmedi.': 'Compact hybrid model for limited memory. Liquid license terms apply; Turkish and complex coding performance have not been measured.',
'LFM2 ailesinin daha büyük metin seçeneği. Mimari llama.cpp tarafından desteklenir; cihazda hız ve Türkçe kalite ölçülmedi.': 'Larger text option in the LFM2 family. The architecture is supported by llama.cpp; device speed and Turkish quality have not been measured.',
'Matematik, kod ve bilim odaklı küçük akıl yürütme modeli. Uzun düşünme çıktıları küçük dosyada da süreyi artırabilir.': 'Small reasoning model for mathematics, code and science. Long reasoning output can take time even with a small weight file.',
'MoE · çok kipli': 'MoE · multimodal',
'MoE: toplam 30B ve etkin 3B. Model ağırlıkları için toplam bellek ihtiyacı sürer; motor mimari desteği gerekli.': 'MoE: 30B total and 3B active parameters. All model weights still need storage; runtime architecture support is required.',
'NVIDIA tarafından eğitilmiş Llama tabanlı sohbet ve akıl yürütme modeli. Düşünme ve araç biçimi motor şablonuna bağlıdır.': 'NVIDIA-trained Llama-based chat and reasoning model. Reasoning and tool formatting depend on the runtime template.',
'Sohbet ve araç kullanımı ailesi. Ticari kullanım başvurusu dahil özel ağırlık lisansı koşulları geçerlidir.': 'Chat and tool-use family. Custom weight license terms apply, including a commercial-use application.',
'Super ailesinin v1.5 sürümü. Ağırlıklar onlarca GB alan ister; küçük GPU için önerilen başlangıç modeli değildir.': 'Version 1.5 of the Super family. Weights require tens of GB; not a recommended first model for small GPUs.',
'Sıkıştırılmış ve ret davranışı azaltılmış topluluk türevi. Yayıncının kalite iddiaları bağımsız olarak doğrulanmadı. Topluluk türevi; ret davranışı, araç kullanımı ve kalite cihazında ayrıca denenmeli.': 'Compressed community derivative with reduced refusal behavior. Publisher quality claims have not been independently verified; test refusal behavior, tool use and quality on your device.',
'Token başına yaklaşık 3B etkin parametre; bütün uzman ağırlıkları yine bellekte veya eşlenmiş dosyada bulunmalı. 3B dosya boyutu anlamına gelmez.': 'About 3B active parameters per token; all expert weights must still be in memory or a mapped file. This does not mean a 3B-sized weight file.',
'Topluluk türevi · reddetme davranışı azaltılmış. 6 GB VRAM’de KV cache ve sistem kullanımı için hibrit mod gerekebilir. Topluluk türevi; ret davranışı, araç kullanımı ve kalite cihazında ayrıca denenmeli.': 'Community derivative with reduced refusal behavior. With 6 GB VRAM, hybrid mode may be needed for KV cache and system headroom. Test refusal behavior, tools and quality separately.',
'Türkçe dahil 23 dil için çok dilli sohbet. CC BY-NC 4.0: ticari olmayan kullanım koşulları geçerlidir.': 'Multilingual chat in 23 languages including Turkish. CC BY-NC 4.0: non-commercial terms apply.',
'Türkçe dahil çok dilli daha büyük model. CC BY-NC 4.0 koşulları ve yüksek bellek ihtiyacı dikkate alınmalıdır.': 'Larger multilingual model including Turkish. Consider CC BY-NC 4.0 terms and high memory requirements.',
'Yayıncının model ve dosya bilgileri doğrulandı; bu cihazda kalite ve hız ölçülmedi.': 'Publisher model and file information was verified; quality and speed on this device have not been measured.',
'Yeni 27B alternatifi · GGUF, MTP başlığı olmadan. Topluluk tarafından abliteration uygulanmış; ret davranışı tamamen yok olmayabilir. Topluluk türevi; ret davranışı, araç kullanımı ve kalite cihazında ayrıca denenmeli.': 'Newer 27B alternative · GGUF without an MTP head. Community ablation may not remove all refusals; evaluate refusal behavior, tool use and quality on your device.',
'Yi 1.5 ailesinin daha büyük sohbet sürümü. Kod için ayrı Yi Coder ailesi de kütüphanede bulunur.': 'Larger chat version of the Yi 1.5 family. The separate Yi Coder family is also available for coding.',
'Yüksek bellekli sistemlere yönelik yoğun model. Küçük VRAM üzerinde RAM paylaşımı çalışmayı garanti etmez; üretim yavaş olabilir.': 'Dense model for high-memory systems. Sharing RAM does not guarantee operation with little VRAM; generation may be slow.',
'Çince ve İngilizce metin odaklı model; bu kayıt görsel veya ayrı MiniCPM4-MCP sürümü değildir.': 'Model for Chinese and English text; this entry is neither a vision model nor the separate MiniCPM4-MCP version.',
'Çince ve İngilizce sohbet için genel model. Türkçe ve karmaşık araç zinciri başarısı ölçülmedi.': 'General chat model for Chinese and English. Turkish and complex tool-chain reliability have not been measured.',
'Çok kipli · araçlar': 'Multimodal · tools',
'Çok küçük sohbet modeli; kısa ve basit yerel görevler için aday. Derin kod analizi ve uzun araç zincirleri için kalite garantisi yoktur.': 'Very small chat model for short, simple local tasks. No quality guarantee for deep code analysis or long tool chains.',
'İngilizce genel talimat ve metin görevleri için daha büyük OLMo 2. Dosya boyutunun üstünde çalışma belleği gerekir.': 'Larger OLMo 2 for general English instruction and text tasks. Working memory is needed beyond the weight file size.',
'Dosyalar': 'Files', 'Belgeler': 'Documents', 'Araştırma': 'Research', 'Bellek ve plan': 'Memory and planning', 'Geliştirme': 'Development', 'Yardımcılar': 'Utilities',
'Proje dosyaları': 'Project files', 'Belge, PDF, tablo ve sunu okuma': 'Read documents, PDFs, sheets and slides', 'Tarayıcı ile araştırma': 'Browser research', 'Web sayfasını oku': 'Read a web page', 'Yerel bilgi belleği': 'Local knowledge memory', 'Adımlarla problem çözme': 'Step-by-step problem solving', 'Yerel Git işlemleri': 'Local Git operations', 'Saat ve zaman dilimi': 'Time and time zones', 'GitHub araçları': 'GitHub tools',
'Seçtiğin klasörde dosya arama, okuma, düzenleme ve klasör işlemleri.': 'Search, read, edit and manage files in your selected folder.',
'PDF, DOCX, XLSX ve PPTX içeriklerini modelin okuyabileceği metne dönüştürür. Belge oluşturma veya biçim düzenleme aracı değildir.': 'Converts PDF, DOCX, XLSX and PPTX content to text for the model. Does not create or format documents.',
'Sayfaları açma, bağlantıları izleme, formları inceleme ve tarayıcı otomasyonu.': 'Open pages, follow links, inspect forms and automate a browser.',
'Bir internet sayfasının içeriğini metne çevirip okur; genel web araması yerine verilen adresi getirir.': 'Retrieves a given web page and converts its content to text; this is not general web search.',
'Kavramları, ilişkileri ve seçtiğin bilgileri yerel bilgi grafiğinde saklar.': 'Stores selected concepts, relationships and facts in a local knowledge graph.',
'Çözüm adımlarını ve alternatif yaklaşımları bir araç akışında izler. Modelin zekâsını veya gizli düşünme yeteneğini artırma garantisi vermez.': 'Tracks solution steps and alternative approaches in a tool workflow. Does not guarantee increased model intelligence or hidden reasoning ability.',
'Seçtiğin Git deposunda değişiklikleri inceleme, dal, kayıt ve durum işlemleri.': 'Review changes and manage branches, commits and status in your selected Git repository.',
'Güncel saat ve zaman dilimleri arasında dönüşüm araçları.': 'Current time and conversion between time zones.',
"GitHub'ın resmî uzak MCP sunucusu. Kullanılabilir araçlar hesabının izinlerine göre değişir.": 'GitHub’s official remote MCP server. Available tools depend on your account permissions.',
'Seçilen klasörde okuma, yazma, taşıma ve silme. Sunucu ayrı bir yerel süreçtir.': 'Read, write, move and delete in the selected folder. Runs as a separate local process.',
'Bu sunucu kullanıcının okuyabildiği yerel dosyaları ve internet adreslerini okuyabilir. İşletim sistemi erişimini klasörle sınırlamaz.': 'Can read local files accessible to the user and internet URLs. Its operating system access is not limited to the folder field.',
'Tarayıcı üzerinden internete erişir; formlar ve oturum açılmış sayfalarda işlem yapabilir. Tarayıcı motoru ayrıca gerekli olabilir.': 'Uses the internet through a browser; can act on forms and signed-in pages. A separate browser runtime may be needed.',
'İnternet adreslerine istek gönderir. Gelen sayfa içerikleri güvenilmeyen veridir.': 'Sends requests to internet addresses. Retrieved page content is untrusted data.',
'Bilgileri runtime/extensions/memory altında saklar. Yalnızca modele verdiğin bilgiler kaydedilmelidir.': 'Stores information under runtime/extensions/memory. Save only information you intend to give the model.',
'Planlama adımlarını çalışan süreçte işler; ayrıca bir dil modeli indirmez.': 'Processes planning steps in its running process; does not download another language model.',
'Seçilen Git deposunu okuyabilir ve değiştirebilir. Dizin deponun altındaysa erişim tüm depoyu kapsar.': 'Can read and change the selected Git repository. If the folder is inside a repository, access covers that whole repository.',
'Sistem saati ve zaman dilimi bilgilerini okur.': 'Reads system clock and time-zone information.',
"GitHub'a bağlanır. KAYRIVA_GITHUB_AUTHORIZATION ortam değişkeni Bearer önekiyle tanımlanmalı; anahtar uygulama ayarına kaydedilmez. OAuth ekranı desteklenmez.": 'Connects to GitHub. Set KAYRIVA_GITHUB_AUTHORIZATION with the Bearer prefix; the key is not saved in app settings. An OAuth sign-in screen is not supported.',
'Hazır · Node.js ve npm': 'Ready · Node.js and npm', 'Node.js ve npm gerekli': 'Node.js and npm required', 'Hazır · Python': 'Ready · Python', 'Python 3.11+ gerekli': 'Python 3.11+ required', 'Hazır · uzak bağlantı': 'Ready · remote connection', 'Ortam değişkeni gerekli: ': 'Required environment variable: ',
}

EN.update({
    'Bellek sınırında': 'Near memory limit', 'GPU adayı': 'GPU candidate',
    'Kısa bağlam veya daha küçük kuantizasyon gerekebilir.': 'A shorter context or smaller quantization may be needed.',
    'Aşırı sıkıştırma; kalite kaybı yüksek olabilir.': 'Extreme compression; quality may drop significantly.',
})
# These are the exact, finite recommendation strings generated by assess().
for source, target in {
    'Kısa bağlamla GPU’da denenebilir.': 'Can be tried on the GPU with a short context.',
    'Ağırlıkların bir kısmı sistem RAM’inde kalır.': 'Some weights remain in system RAM.',
    'GPU olmadan; üretim daha yavaş olabilir.': 'Without a GPU; generation may be slower.',
}.items():
    for low, community in [(False, False), (True, False), (False, True), (True, True)]:
        EN[source + (' Düşük bit, kaliteyi azaltabilir.' if low else '') + (' Topluluk türevi.' if community else '')] = target + (' Low-bit quantization may reduce quality.' if low else '') + (' Community derivative.' if community else '')

EN.update({'Dokümantasyon': 'Documentation',
 'DeepWiki · depo araştırması': 'DeepWiki · repository research',
 'Herkese açık depoların dokümantasyon yapısını ve içeriğini okur, depo hakkında kaynak bağlamlı sorular sorar.': 'Reads '
                                                                                                                  'documentation '
                                                                                                                  'structure '
                                                                                                                  'and '
                                                                                                                  'content '
                                                                                                                  'for '
                                                                                                                  'public '
                                                                                                                  'repositories '
                                                                                                                  'and '
                                                                                                                  'answers '
                                                                                                                  'questions '
                                                                                                                  'using '
                                                                                                                  'repository '
                                                                                                                  'context.',
 'Depo adları ve sorular uzak hizmete gönderilir. Kimlik doğrulama gerekmez; özel depolara erişim sağlamaz.': 'Repository '
                                                                                                              'names '
                                                                                                              'and '
                                                                                                              'questions '
                                                                                                              'are '
                                                                                                              'sent '
                                                                                                              'to '
                                                                                                              'the '
                                                                                                              'remote '
                                                                                                              'service. '
                                                                                                              'No '
                                                                                                              'authentication '
                                                                                                              'is '
                                                                                                              'required; '
                                                                                                              'private '
                                                                                                              'repositories '
                                                                                                              'are '
                                                                                                              'not '
                                                                                                              'accessible.',
 'Microsoft Learn · teknik kaynaklar': 'Microsoft Learn · technical references',
 'Resmî Microsoft dokümanlarını ve kod örneklerini arar; makalelerin tamamını getirir.': 'Searches official '
                                                                                         'Microsoft '
                                                                                         'documentation and '
                                                                                         'code samples and '
                                                                                         'fetches full '
                                                                                         'articles.',
 'Arama sorguları ve makale adresleri Microsoft Learn hizmetine gönderilir. Yerel dosyalara erişmez.': 'Search '
                                                                                                       'queries '
                                                                                                       'and '
                                                                                                       'article '
                                                                                                       'URLs '
                                                                                                       'are '
                                                                                                       'sent '
                                                                                                       'to '
                                                                                                       'Microsoft '
                                                                                                       'Learn. '
                                                                                                       'It '
                                                                                                       'does '
                                                                                                       'not '
                                                                                                       'access '
                                                                                                       'local '
                                                                                                       'files.',
 'Cloudflare · doküman arama': 'Cloudflare · documentation search',
 'Cloudflare ürünlerinin güncel referans dokümanlarında arama yapar.': 'Searches current reference '
                                                                       'documentation for Cloudflare '
                                                                       'products.',
 'Sorular Cloudflare dokümantasyon hizmetine gönderilir. Cloudflare hesabında yönetim işlemleri yapmaz.': 'Questions '
                                                                                                          'are '
                                                                                                          'sent '
                                                                                                          'to '
                                                                                                          'the '
                                                                                                          'Cloudflare '
                                                                                                          'documentation '
                                                                                                          'service. '
                                                                                                          'It '
                                                                                                          'does '
                                                                                                          'not '
                                                                                                          'administer '
                                                                                                          'your '
                                                                                                          'Cloudflare '
                                                                                                          'account.',
 'Cloudflare Agents · SDK rehberi': 'Cloudflare Agents · SDK reference',
 'Cloudflare Agents SDK dokümanlarını araştırmak için odaklı bir referans sunucusu.': 'A focused reference '
                                                                                      'server for '
                                                                                      'researching '
                                                                                      'Cloudflare Agents SDK '
                                                                                      'documentation.',
 'Dokümantasyon sorgularını Cloudflare hizmetine gönderir. Uygulama dağıtmaz ve hesap kaynaklarını yönetmez.': 'Sends '
                                                                                                               'documentation '
                                                                                                               'queries '
                                                                                                               'to '
                                                                                                               'Cloudflare. '
                                                                                                               'It '
                                                                                                               'does '
                                                                                                               'not '
                                                                                                               'deploy '
                                                                                                               'applications '
                                                                                                               'or '
                                                                                                               'manage '
                                                                                                               'account '
                                                                                                               'resources.',
 'Context7 · kütüphane dokümanları': 'Context7 · library documentation',
 'Kütüphaneleri bulur ve sürüm bağlamına uygun dokümanlar ile kod örnekleri getirir.': 'Finds libraries and '
                                                                                       'retrieves '
                                                                                       'documentation and '
                                                                                       'code examples for '
                                                                                       'the relevant version '
                                                                                       'context.',
 'Kütüphane adları ve sorular Upstash hizmetine gönderilir. Daha yüksek limitler için isteğe bağlı API anahtarı kullanılabilir.': 'Library '
                                                                                                                                  'names '
                                                                                                                                  'and '
                                                                                                                                  'questions '
                                                                                                                                  'are '
                                                                                                                                  'sent '
                                                                                                                                  'to '
                                                                                                                                  'Upstash. '
                                                                                                                                  'An '
                                                                                                                                  'optional '
                                                                                                                                  'API '
                                                                                                                                  'key '
                                                                                                                                  'can '
                                                                                                                                  'provide '
                                                                                                                                  'higher '
                                                                                                                                  'usage '
                                                                                                                                  'limits.',
 'Hugging Face · model ve veri keşfi': 'Hugging Face · models and datasets',
 'Hub içeriğinde model, veri kümesi ve doküman araştırması. Anahtarsız bağlantıda yalnızca herkese açık araçlar kullanılabilir.': 'Research '
                                                                                                                                  'models, '
                                                                                                                                  'datasets '
                                                                                                                                  'and '
                                                                                                                                  'documentation '
                                                                                                                                  'on '
                                                                                                                                  'the '
                                                                                                                                  'Hub. '
                                                                                                                                  'This '
                                                                                                                                  'unauthenticated '
                                                                                                                                  'connection '
                                                                                                                                  'only '
                                                                                                                                  'offers '
                                                                                                                                  'public '
                                                                                                                                  'tools.',
 'Sorgular Hugging Face hizmetine gönderilir. Özel içerik ve hesap işlemleri kimlik doğrulama gerektirir; bu bağlantı hesap anahtarı içermez.': 'Queries '
                                                                                                                                                'are '
                                                                                                                                                'sent '
                                                                                                                                                'to '
                                                                                                                                                'Hugging '
                                                                                                                                                'Face. '
                                                                                                                                                'Private '
                                                                                                                                                'content '
                                                                                                                                                'and '
                                                                                                                                                'account '
                                                                                                                                                'operations '
                                                                                                                                                'require '
                                                                                                                                                'authentication; '
                                                                                                                                                'this '
                                                                                                                                                'connection '
                                                                                                                                                'includes '
                                                                                                                                                'no '
                                                                                                                                                'account '
                                                                                                                                                'credentials.',
 'Brave · web arama': 'Brave · web search',
 'Brave Search API ile web, görsel, video ve haber araması. Node.js 22+ ve kendi API anahtarın gerekir.': 'Web, '
                                                                                                          'image, '
                                                                                                          'video '
                                                                                                          'and '
                                                                                                          'news '
                                                                                                          'search '
                                                                                                          'through '
                                                                                                          'the '
                                                                                                          'Brave '
                                                                                                          'Search '
                                                                                                          'API. '
                                                                                                          'Requires '
                                                                                                          'Node.js '
                                                                                                          '22+ '
                                                                                                          'and '
                                                                                                          'your '
                                                                                                          'own '
                                                                                                          'API '
                                                                                                          'key.',
 'Arama sorguları Brave hizmetine gönderilir. BRAVE_API_KEY ortam değişkenini tanımla; hizmet planına göre ücret veya kullanım sınırı uygulanabilir.': 'Search '
                                                                                                                                                       'queries '
                                                                                                                                                       'are '
                                                                                                                                                       'sent '
                                                                                                                                                       'to '
                                                                                                                                                       'Brave. '
                                                                                                                                                       'Set '
                                                                                                                                                       'the '
                                                                                                                                                       'BRAVE_API_KEY '
                                                                                                                                                       'environment '
                                                                                                                                                       'variable; '
                                                                                                                                                       'service '
                                                                                                                                                       'fees '
                                                                                                                                                       'or '
                                                                                                                                                       'usage '
                                                                                                                                                       'limits '
                                                                                                                                                       'may '
                                                                                                                                                       'apply.',
 'Tavily · arama ve tarama': 'Tavily · search and crawl',
 'Web araması, sayfa içeriği çıkarma, site haritası ve tarama araçları. Kendi Tavily API anahtarın gerekir.': 'Web '
                                                                                                              'search, '
                                                                                                              'content '
                                                                                                              'extraction, '
                                                                                                              'site '
                                                                                                              'mapping '
                                                                                                              'and '
                                                                                                              'crawling '
                                                                                                              'tools. '
                                                                                                              'Requires '
                                                                                                              'your '
                                                                                                              'own '
                                                                                                              'Tavily '
                                                                                                              'API '
                                                                                                              'key.',
 'Sorgular ve taranacak adresler Tavily hizmetine gönderilir. TAVILY_API_KEY ortam değişkenini tanımla; hizmet planına göre ücret veya kullanım sınırı uygulanabilir.': 'Queries '
                                                                                                                                                                        'and '
                                                                                                                                                                        'crawl '
                                                                                                                                                                        'URLs '
                                                                                                                                                                        'are '
                                                                                                                                                                        'sent '
                                                                                                                                                                        'to '
                                                                                                                                                                        'Tavily. '
                                                                                                                                                                        'Set '
                                                                                                                                                                        'the '
                                                                                                                                                                        'TAVILY_API_KEY '
                                                                                                                                                                        'environment '
                                                                                                                                                                        'variable; '
                                                                                                                                                                        'service '
                                                                                                                                                                        'fees '
                                                                                                                                                                        'or '
                                                                                                                                                                        'usage '
                                                                                                                                                                        'limits '
                                                                                                                                                                        'may '
                                                                                                                                                                        'apply.'})
