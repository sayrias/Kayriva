# Eklenti kütüphanesi ve GitHub

Bağlantılar → **Kütüphane**, yerel modele araç eklemek için hazırlanmış MCP sunucularını gösterir. Arama ve alan filtresi vardır. Bir satır seçildiğinde yayıncı, resmî kaynak, gerçek yetenek, erişim kapsamı ve gerekli çalışma ortamı gösterilir.

## Kurulum davranışı

- Kütüphaneyi açmak paket indirmez veya sunucu başlatmaz. **Kur ve ekle** seçimi kurulum yetkisidir. Ağ kapalıysa kurulum başlatılmaz.
- Node.js paketleri `runtime/extensions/<id>/node_modules` içine, npm kurulum betikleri kapalı olarak yüklenir. Çözülmüş sürüm `package-lock.json` ve `installed.json` ile kaydedilir. Sonraki sohbetler npm/npx çağırıp kendiliğinden güncellemez; doğrudan Node giriş dosyası kullanılır. Windows'ta da npm'nin JavaScript girişi Node üzerinden çalışır; `cmd` içinde metin birleştirilmez.
- Python paketleri her eklentinin ayrı sanal ortamına kurulur; yalnızca hazır wheel paketleri kabul edilir. Sistem Python/Node/npm uygulamayla dağıtılmaz; yoksa panel açıklayıcı bir gereksinim gösterir. Playwright'ın tarayıcı motoru ayrıca gerekli olabilir.
- Sunucular varsayılan kapalı eklenir. Kullanıcı isterse **Kurulumdan sonra etkinleştir** seçeneğini açar; etkin araçlar sohbetin işlem onayı ayarına göre çağrılır. Bir sunucuyu etkinleştirmek, ayrı bir süreç çalıştırma yetkisi verir. Kayriva tüm üçüncü taraf sunucuları işletim sistemi düzeyinde sandbox içine almaz.
- Silinen bağlantı paket dosyalarını ve yerel belleği otomatik silmez; veri kaybı yaşanmaz. Yeniden ekleme için kütüphane kullanılır. Katalogdaki yayıncı veya API'nin değişmeyeceği garanti edilemez; resmî kaynak bağlantısı ve kaydedilmiş sürüm incelenebilir.

## Katalog kapsamı

`extensions/catalog.json` yerel, sürümlenebilir başlangıç listesidir. 2 Kasım 2026'da birincil kaynaklarından doğrulanan başlangıç sunucuları:

| Alan | Sunucu / kaynak | Kapsam |
|---|---|---|
| Dosyalar | [Filesystem](https://github.com/modelcontextprotocol/servers/tree/main/src/filesystem) | Seçilen klasörde okuma, yazma, arama, taşıma ve silme |
| Belgeler | [Microsoft MarkItDown MCP](https://github.com/microsoft/markitdown/tree/main/packages/markitdown-mcp) | PDF, DOCX, XLSX ve PPTX içeriklerini metne dönüştürme; biçimli dosya oluşturma/düzenleme değildir |
| Araştırma | [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) | Tarayıcı otomasyonu ve sayfa inceleme |
| Araştırma | [Fetch](https://github.com/modelcontextprotocol/servers/tree/main/src/fetch) | Verilen web adresinin içeriğini getirme |
| Bellek | [Memory](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | Yerel bilgi grafiği |
| Plan | [Sequential Thinking](https://github.com/modelcontextprotocol/servers/tree/main/src/sequentialthinking) | Araç üzerinden çözüm adımları; başka model veya zekâ garantisi değildir |
| Geliştirme | [Git](https://github.com/modelcontextprotocol/servers/tree/main/src/git) | Seçilen depoda Git işlemleri |
| Yardımcı | [Time](https://github.com/modelcontextprotocol/servers/tree/main/src/time) | Saat ve zaman dilimi |
| Geliştirme | [GitHub'ın resmî MCP sunucusu](https://github.com/github/github-mcp-server) | GitHub hesabının izin verdiği uzak araçlar |

Başka uygulamalara özel belge, tablo, PDF ve sunum eklentileri doğrudan taşınabilen paketler değildir. Katalog bunların aynısıymış gibi davranmaz: belge okuma karşılığı MarkItDown'ın gerçekten sunduğu dönüştürmedir. Kayriva'nın yerel metin/kod dosyası araçları ayrıca kullanılabilir. MarkItDown kullanıcının okuyabildiği dosyalara erişebilir; klasör alanı onun erişimini sınırlıyormuş gibi gösterilmez.

Uzak GitHub MCP kimlik doğrulaması `KAYRIVA_GITHUB_AUTHORIZATION` ortam değişkeninden tam `Bearer …` başlığı olarak okunur. Anahtar kataloğa/ayar dosyasına yazılmaz. OAuth yönlendirme akışı bu istemcide henüz yoktur. GitHub CLI üzerinden proje yönetimi bu MCP bağlantısından bağımsızdır.

**JSON yapıştır** `mcpServers` / `servers` nesnelerini doğrular ve bağlantıları kapalı ekler. İçe aktarma çalıştırma yapmaz. **Bağlantıları kopyala** açık kimlik bilgisi ortamlarını, kimlik doğrulama başlıklarını, anahtar taşıyan URL parametrelerini ve bilinen CLI anahtar argümanlarını ayıklar; ortam değişkeni referanslarını korur. Aktarılan özel bir yapılandırmanın tüm keyfî alanlarında anahtar bulunmadığını garanti eden bir sır tarayıcısı değildir.

## GitHub: görüntüle, oluştur, yükle

Projeler başlığından, proje menüsünden veya Proje dosyaları araçlarından GitHub paneli açılır. Mevcut proje yolu önceden seçilidir; başka klasör de seçilebilir. [GitHub CLI](https://cli.github.com/) ve Git gerekir. Kayriva CLI'nin mevcut oturumunu kullanır; anahtar istemez veya saklamaz. **Oturum açma komutunu kopyala**, kullanıcının kendi terminalinde çalıştıracağı resmî web oturum komutunu verir. **Hesabı ve depoları yenile** hesabı ve en fazla 50 depoyu okur. Depo seçilip GitHub'da açılabilir.

Yeni boş depo veya proje kaynaklarını içeren yeni depo oluşturulabilir. Varsayılan görünürlük **Özel**'dir. Uzak işlem yalnızca hesabı bağlı kullanıcı görünürlüğü/dosyaları incelediğini işaretleyip oluştur/yükle düğmesine bastığında yapılır. Arayüzü açmak depo oluşturmaz ve otomatik yayın yapmaz.

Proje yükleme akışı:

1. Geçici, bağımsız Git diziniyle gerçek `.gitignore` kuralları uygulanır; kaynak projenin `.git` dizini/indeksi değiştirilmez.
2. Çalışma verileri (`runtime`), anahtar dosyaları, `.env`, model ağırlıkları, bağımlılıklar ve derlemeler ayrıca dışarıda bırakılır. Bilinen PAT/özel anahtar biçimleri aranır; bu kontrol bütün sır biçimlerini kapsamaz. Dosya listesi kullanıcı tarafından incelenebilir ve dosya seçimi kaldırılabilir.
3. En fazla 2000 dosya / toplam 100 MB, dosya başına 25 MB incelenir. Sembolik bağlantılar yüklenmez. Proje dışına kaçan yollar reddedilir.
4. Yüklemeden önce seçilen dosyaların SHA-256 özeti tekrar hesaplanır. Önizlemeden sonra değişiklik varsa yeniden önizleme istenir.
5. Yalnızca seçilen kaynakların geçici bir kopyası yeni depoya yüklenir. Kaynak projenin Git geçmişi, dalları ve uzak bağlantıları taşınmaz/değiştirilmez. Bu akış mevcut uzak depoya senkronizasyon veya pull/push yöneticisi değildir.

Komutlar `shell=False` argüman dizileriyle çağrılır. Ham GitHub hata çıktısı anahtar sızdırmamak için arayüze/loglara kopyalanmaz. Ağ hatasında uzakta depo oluşturulmuş ancak yükleme tamamlanmamış olabilir; hata bunu söyler ve tekrar denemeden depo listesi kontrol edilir. Geri alma adına uzak depo silinmez.

GitHub CLI davranışı: [repo create](https://cli.github.com/manual/gh_repo_create), [repo list](https://cli.github.com/manual/gh_repo_list), [auth status](https://cli.github.com/manual/gh_auth_status).

## Doğrulama

`src/tests/test_integrations.py` gerçek geçici Git önizlemesi, `.gitignore`, symlink ve sır hariç tutma, SHA-256 değişiklik reddi, sadece seçili dosyaların snapshot'a alınması, özel görünürlük, ayrı argv ve hatalarda sır gizleme davranışlarını doğrular. Ağ/yayın/üçüncü taraf kurulumları testlerde taklit edilir. `test_integration_ui.py` filtre/boş durum ve hesap/onay/önizleme koşullarını doğrular. Geliştirme sırasında gerçek GitHub hesabında depo açılmadı, sunucu veya paket kurulmadı.

## Kütüphanede gezinme

Katalog 17 bağlantı içerir. Alan filtresinin yanında **Tümü**, **Yerel**, **Uzak** ve **Eklenenler** sekmeleri bulunur. Sol listede eklentilerin gerçek adları, ikinci satırda alanları görünür. Arama ve filtre yenilemesi seçili eklenti görünmeye devam ediyorsa seçimi korur. Ayrıntılar kaydırılabilir; kurulum ve resmî kaynak düğmeleri görünür kalır.

Yeni bağlantılar: [DeepWiki](https://docs.devin.ai/work-with-devin/deepwiki-mcp), [Microsoft Learn](https://learn.microsoft.com/en-us/training/support/mcp), [Cloudflare Docs ve Agents SDK](https://developers.cloudflare.com/agents/model-context-protocol/cloudflare/servers-for-cloudflare/), [Context7](https://github.com/upstash/context7), [Hugging Face](https://huggingface.co/docs/hub/agents-mcp), [Brave Search](https://github.com/brave/brave-search-mcp-server) ve [Tavily](https://github.com/tavily-ai/tavily-mcp). Uzak bağlantı eklemek yerel paket indirmez; sorgular ilgili hizmete gider. Katalog açıklaması her hizmetin kapsamını belirtir.

Brave için `BRAVE_API_KEY`, Tavily için `TAVILY_API_KEY` uygulama başlatılmadan önce ortamda tanımlanır. Bu iki eklenti anahtar eksikken etkin olarak eklenemez; kapalı bağlantı olarak kurulabilir. Brave Node.js 22+ ister. Anahtarlar katalogda, kurulum kaydında veya dışa aktarılan yapılandırmada bulunmaz. Bu katalog genişletmesinde ücretli araç çağrısı veya yeni paket kurulumu yapılmadı; kullanıcı seçimiyle kurulum ve bağlantı testi gerekir.
