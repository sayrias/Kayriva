# Mimari

```text
Kayriva/
├── src/          Native Qt arayüzü, sohbet, MCP, araştırma ve testler
├── engine/       Yerel motor derleme scripti ve engine/bin/ motor dosyaları
├── models/       GGUF modeller ve doğrulanmış öneri kataloğu
├── extensions/   MCP bağlantı örnekleri
├── runtime/      Ayarlar, SQLite sohbet/görev kayıtları, motor günlüğü, önizlemeler
├── docs/         Kullanım ve mimari belgeleri
├── README.md
├── pyproject.toml
└── kayriva.sh    Başlatma, kurulum, Linux ve Wine/Windows paketleme
```

## Hesaplama yolu

Qt arayüzü → arka plan iş parçacığı → uygulamanın başlattığı llama.cpp C/C++ süreci → yerel GGUF model.

Python arayüz ve koordinasyon için kullanılır; büyük tensör işlemleri C/C++ motorunda yapılır. Ağ üzerinden bulut modele gönderim yok. Loopback HTTP yalnızca iki yerel süreç arasındaki iletişimdir. Ağ proxy ortamı inference bağlantısında kullanılmaz. Motor otomatik model indirmez; model ve binary kullanıcının yerel seçimidir.

CPU modu tüm ağırlıkları RAM’de işler. Hibrit modu `n_gpu_layers` ile GPU’ya aktarılacak katmanları belirler; geri kalanı RAM’de kalır. GPU modu tüm katmanları aktarmayı dener. Bağlam, KV cache, hesaplama buffer’ları, ekran kullanımı ve işletim sistemi de bellek tüketir. Disk boyutlarını VRAM gereksinimi olarak okumamak gerekir. GPU + RAM varsayılandır. Otomatik katman seçimi, ayarlanabilir RAM/VRAM kullanım üst sınırları ve model yüklenmeden önce tahmini bellek bütçesi kontrolü vardır. Desteklenen motor GPU yerleşimini `--fit-target` ile iyileştirir. Bunlar kesin işletim sistemi kotaları değildir. Anlık token/s motor sayaçlarından hesaplanır.

## Araçlar

MCP istemcisi stdio ve Streamable HTTP ile araçları keşfeder. Araç adlarına sunucu bazında takma ad verilir. Araç çağrısı JSON olarak modelden gelir, seçili onay politikasına göre yürütülür, sonuç modele geri verilir. Bir yanıtta varsayılan 24, ayarlanabilir 4–128 araç turu ve 1–240 dakika çalışma sınırı vardır. Eklentiler OS kullanıcı yetkileriyle çalışır; uygulama bir sandbox sağlamaz.

Çalışma alanının yerleşik model araçları dosya listeleme, okuma, oluşturma, yazma, ekleme, tekil metin düzenleme ve klasör oluşturmadır. Tam dosya değiştirme güncel içerik özeti gerektirir. Yol kaçışı, dışarı çıkan sembolik bağlantılar ve gizli kimlik bilgisi dizinleri engellenir. Kullanıcı editörden elle kaydedebilir; dosya dışarıda değişmişse kaydetme öncesi çatışma uyarısı verilir.

## Veriler ve işler

SQLite sohbet/proje ve görev kayıtları ayrı dosyalarda tutulur. Görev köprüsü aynı yerel kuyruğa yazan stdio MCP sunucusudur. Masaüstü uygulaması açık ve dış görev kabulü etkin olduğunda köprü görev oluşturabilir. Model aynı anda tek iş üretir; araştırma işi ve normal sohbet sırayla çalışır. Görevler kaynaklar/sonuçlarıyla saklanır.

Araştırma varsayılan 1/6/18 sorguyu ayrı model planlama çağrısı olmadan hazırlar. Web istemcisi arama özetlerini toplar; Detaylı/Uzun modlarında en fazla 10/60 genel web sayfasından sınırlı metin okunur. Uzun mod 48 sorgu/400 kaynak/160 sayfa üst sınırına kadar ayarlanabilir. Kaynaklar URL bölüm bağlantısı ayıklanarak birleştirilir ve siteler arasında dönüşümlü okunur. Başlık/URL/arama özeti/okuma durumu son asistan mesajının _studio.sources alanında saklanır; bunlar sonraki model bağlamına eklenmez. Kaynaklar modalı yeniden açılan sohbetlerde de çalışır. Kaynak metinleri sınırlı bir bağlam bütçesiyle modele sunulur. Araştırma kaynakları güvenilmeyen veri olarak modele iletilir. Arama servisinin cevaplarının doğruluğu garanti edilmez.

## Yerel ölçümler

`usage.py` içerik tutmadan üretim sayaçlarını SQLite’a yazar. `resources.py` yerel sistem sayaçlarını okur. `local_logging.py` dönen hata kayıtları tutar. Model motoru SSE usage/timings alanlarıyla anlık ve tamamlanmış sayaçları bildirir; opsiyonel Transformers yolu tokenizer/çıktı kimliklerini sayar. UI sayaçları QThread sinyalleriyle alır; sistem sorguları arka planda çalışır. Eski sohbetler kullanım geçmişine dönüştürülmez.

Model hazırlığı tembel, açılışta hazır veya yanıt sonrası boşalt olarak seçilebilir. Eager hazırlık TaskWorker üzerinde çalışır ve iptal edilebilir; bellek/kurulum hatası durum satırında gösterilir. Model tek görevle kullanılır; hazırlık sırasında başka model işi başlatılmaz.

Bellekteki GGUF model için resident_plan, canlı işlem ve yükleme imzası eşleşmesini kontrol eder. Aynı model/bağlamda yeni boş bellek üzerinden yeniden plan yapılmaz. Slider yüklü modelin yükleme bütçesini korur; boş alan sistem sayacı olarak ayrı görünür. Yeni yüklemede önce eski motor kapatılıp güncel sayaçlarla plan yapılır. Linux MemAvailable zaten yeniden kullanılabilir dosya önbelleğini içerdiği için model RSS tahmini boş alana eklenmez ([kernel /proc belgesi](https://docs.kernel.org/filesystems/proc.html)).


## Model keşfi ve eklentiler

`model_import.py` yerel model biçimini, yol URI'sini, parçaları ve isteğe bağlı projektörü çözer. `catalog_sync.py` katalog kimliğini uzaktan değiştirmeden dosya metadata önbelleğini atomik günceller. Model ve eklenti katalogları dağıtımın salt okunur verileri içindedir; kullanıcı verisine kopyalanır. `extension_library.py` kullanıcı seçimiyle çalışma ortamı ayrı kurulum yapar. `github_service.py` GitHub CLI ile gözden geçirilen kaynak dosyaların temiz kopyasını yükler; kaynak Git geçmişini değiştirmez. Harici servis anahtarları kod/katalog içinde tutulmaz.

`attachments.py` metin, PDF ve Office içeriğini sınırlandırarak çıkarır. Görseller özel runtime/attachments klasöründe içerik özetli PNG olarak tutulur; SQLite yalnızca göreli tanımlayıcı taşır. Model çağrısında görseller OpenAI uyumlu image_url veri girişine dönüştürülür. Base64 taşıma boyutu düz metin token sayısı gibi hesaplanmaz. Görsel projektör CPU'da tutulur ve bellek tahminine eklenir. Gerçek uyumluluk seçilen llama.cpp mimarisine bağlıdır.

## Public-beta updates and localization

`updater.py` owns bounded public GitHub release discovery, semantic version ordering, release-manifest validation, verified staging and the optional 64 KiB copy/literal delta format. `ui/about.py` orchestrates asynchronous checking/downloading and explicit restart. Platform helper processes wait for exit before replacing the Linux portable file or running the Windows installer. Persistent user data is outside the installation. See [the update design and publisher workflow](update-system.md).

`i18n.py`, `catalog_i18n.py` and `runtime_i18n.py` contain explicit English/Turkish UI labels and known message templates. The default is English; saving a language change refreshes the existing native controls immediately, preserving chats, drafts and selected data IDs. `ui/localized.py` binds only explicit translation keys; user content is never inferred from visible text. The UI does not translate conversations or arbitrary user content. The source tree remains importable without Qt for the updater manifest CLI.

`kayriva.sh release` checks each platform's build-info version, size and SHA before producing the public update manifest. This prevents combining a stale Windows build with a newly built Linux version. It prepares files locally and never publishes to GitHub.
