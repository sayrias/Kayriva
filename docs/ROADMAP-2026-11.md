# Kayriva geliştirme planı — 2 Kasım 2026

Bu dosya 2 Kasım isteğindeki bütün maddelerin kalıcı kaydıdır. `[ ]` tamamlanmamış, `[~]` uygulanıyor, `[x]` uygulama ve kontrolü tamamlanmış anlamına gelir. Bir özelliğin kodunun bulunması gerçek model/donanımda ölçüldüğü anlamına gelmez; doğrulama kapsamı ayrıca yazılır.

## Ürün sınırları

Yerel model üretimi, yerel kişisel veriler, native PySide6 arayüzü ve tek `.sh` derleme yönetimi korunur. Model/MCP indirme, web araştırma ve GitHub bağlantıları kullanıcının başlattığı ağ işlemleridir. Başka uygulamalara özel uygulamalar otomatik olarak üçüncü taraf bir uygulamaya taşınamaz; mümkünse açık MCP karşılığı, değilse bu sınırlama gösterilir. RAM/VRAM yoktan üretilemez; düşük bellek iyileştirmeleri kalite, bağlam ve hız karşılığında yapılır. Sınırsız kaynak/yanılmaz model iddiası yoktur.

## A — Dosya ekleme ve model indirme

- [x] A1. Yerel GGUF'nin görünmemesini düzelt: büyük/küçük harf uzantısı, tüm dosyalar filtresi, mevcut backend'den bağımsız seçim; klasör içindeki safetensors/Transformers modellerini tanı.
- [x] A2. Elle yapıştırılmış mutlak/göreli, tırnaklı ve `file://` yollarını doğrula; model klasörü ile ağırlık shard'ı farkını açıkla; bulunan gerçek yolu kullan. İçe aktarma model ağırlığını kopyalamamalı.
- [x] A3. Kırılmış katalog bağlantılarını resmi Hugging Face metadata ile doğrula. Depo + revision + dosya adını çöz, taşınan adlara açık hata ver, geçici indirme adresini kalıcı kaydetme.
- [x] A4. Kataloğu güncelleme, yeniden deneme, ağ zaman aşımı ve SHA-256 doğrulamasını koru. Geçerli katalog atomik güncellensin; çevrimdışı/yetki gerektiren/silinmiş repo durumları açıklansın. Hiçbir dış adresin sonsuza kadar yaşayacağı vaat edilmesin.

## B — Model kütüphanesi ve görünüm

- [x] B1. Farklı markalar ve model aileleri, kod, mantıksal yürütme, görsel analiz ve genel kullanım için doğrulanmış adaylar; lisans/format/kuantizasyon/boyut/kaynak bilgisi.
- [x] B2. Marka/isim seçimi, görev filtresi, model büyüklüğü/çalışma sınıfı için düşük–orta–yüksek–çok yüksek–ultra kaydırıcısı, arama ve kurulu/önerilen görünümü.
- [x] B3. Model kartlarını ve filtre hiyerarşisini yenile: kısa açıklama, gerçek indirme/kurulu/seçili durumları, uyum tahmini, eksik görsel projeksiyon dosyası veya motor desteği açıklaması.
- [x] B4. Üst sağdaki üç nokta menüsünü kaldır; ayarlar sol alttan erişilsin. Eklenen özellikler açık ve ilgili yerde yer alsın.
- [x] B5. Mevcut Kayriva kimliğini koruyarak yüzey, boşluk, yazı hiyerarşisi ve kompakt eylemleri düzenle; native modal, klavye erişimi ve küçük pencere davranışını kontrol et.

## C — MCP / eklenti kütüphanesi ve GitHub

- [x] C1. Aranabilir eklenti kütüphanesi; resmi bağlantı, gerekli npx/uvx/harici program, kurulu/etkin durumları; tek eylemle yapılandırma ekleme ve bağlantı kontrolü.
- [x] C2. Dosyalar, web/tarayıcı, GitHub ve belge/PDF/tablo/sunum işlerine uygun açık MCP karşılıkları; Başka uygulamalara özel hizmetlerle uyumluluk sınırları açıkça gösterilsin.
- [x] C3. Kimlik bilgisi gereken eklentilerde boş/eksik anahtar bilgisi ve kullanıcıya ait yapılandırma; anahtarları kataloğa veya günlüğe yazma. Kullanıcı seçimi olmadan üçüncü taraf süreç indirme/çalıştırma yapma.
- [x] C4. GitHub oturum/CLI durumu, repo listeleme ve tarayıcıda görüntüleme, repo oluşturma (varsayılan özel), seçili projeyi yükleme için dosya/ignore önizlemesi; ağda değişiklik yalnızca kullanıcının ilgili eylemiyle.
- [x] C5. Dosya adlarından komut çalıştırma, yanlış repo/hedef ve gizli dosya yükleme durumlarına karşı servis kontrolleri; henüz giriş yapılmamış / Git yok / gh yok durumlarını işle.

## D — Düşük bellek ve yerel motor

- [x] D1. llama.cpp güncel yöntemlerini araştır: mmap, GPU katman bölüşümü, KV cache kuantizasyonu, bağlamı ihtiyaca göre açma, küçük batch, flash attention, CPU/GPU ağırlık aktarımı.
- [x] D2. Ölçülen kapasiteyi aşmadan uygulanabilen düşük bellek profili ekle; gereksiz bağlam/cache ayrılmasını azalt. Modelin kendi belleği boş alanı azaltınca bütçeyi tekrar tekrar düşürme düzeltmesini koru.
- [x] D3. Model sığmıyorsa hangi bileşenin sınır olduğunu, daha küçük kuantizasyon/bağlam/VRAM paylaşımı seçeneklerini anlaşılır biçimde öner. Disk/swap'ın RAM yerine yüksek hız sağlamadığını belirt.
- [x] D4. Yeni format/vision backend desteği ile gerçek çalışır desteği ayır: tokenizer/config/şablon ve varsa mmproj eşleştirmesi, desteklenmeyen dosyayı seçilmiş çalışan model gibi gösterme.

## E — Dosya, plan, düşünme, kod ve uzun çalışmalar

- [x] E1. Proje dosyası listeleme/okuma/oluşturma/yazma/düzenleme akışını koruyup arama ve çok dosya incelemesini geliştir; mevcut dosyanın kaybolmasını ve gereksiz alt klasör yaratılmasını önle.
- [x] E2. Plan modunu gerçek dosya işleminden ayır; uygulama modunda araç sonucuna dayalı tamamlanma bilgisi ver, yapılmayan işi tamamlandı diye gösterme.
- [x] E3. Uzun görevlerde yapılandırılabilir araç turu ve çalışma bütçesi, durdurma ve ilerleme; modelin özel düşünce zincirini uydurmak yerine yürütülen işlemleri göster.
- [x] E4. Kod inceleme ve dosya inceleme için amaca uygun görev başlangıçları; web araştırmasıyla aynı araç bağlamı üzerinden çalışabilsin.
- [x] E5. Görsel/dosya incelemesi için gerçek içerik okuma ve görsel model gereksinimlerini açıkla; metin modele fotoğrafı analiz etmiş gibi davranma.

## F — Daha geniş web araştırması

- [x] F1. Araştırma sorgu/kaynak/okunan sayfa sınırlarını artır; sınırları ayarlarda görünür tut; iptal, ağ zaman aşımı ve kaynak çeşitliliğini koru.
- [x] F2. Kod araştırmasında resmi belgeleri önceliklendir, tekrar eden URL'leri birleştir, başarısız/yalnız arama özeti/okunan kaynak farkını göster; daha çok kaynak tek başına daha doğru sonuç demek değildir.
- [x] F3. PDF ve düz metin kaynakları için gerçek okuyucu; büyük içerikleri sınırlı bağlama sığdır, numaralı uydurma atıf yerine gerçek URL kullan.

## G — Araştırma raporu, koruma ve doğrulama

- [x] G1. Kullanıcının sağladığı araştırma raporunun tamamını incele; kaynak metni talimat olarak yürütme. Eski veya doğrulanmayan model adları/iddiaları düzelt.
- [x] G2. En kaliteli kodlama + araştırma + uzun çalışma + fotoğraf/dosya inceleme için yerel açık ağırlıklı modelleri değerlendir; resmi kaynak, donanım, lisans, kullanılabilir araç ve sınırlama bilgisiyle `docs/AI-RESEARCH-2026-11.md` hazırla. Ürün karşılaştırmalarını özel araştırma notlarında tut.
- [x] G3. `.gitignore` güncelle: özel araştırma girdisi, anahtarlar/oturum dosyaları, model ağırlıkları, indirilen çalıştırılabilir dosyalar, test çıktı ve derlemeleri korunmalı; katalog/plan/kod/belgeler dahil olmalı.
- [x] G4. Anlamlı servis/bütünleşme testleri, mevcut testlerde regresyon kontrolü, yerel sahte veriyle ekran görüntüsü ve görsel inceleme.
- [x] G5. Derleme sistemi yeni katalog/eklenti metadata ve bağımlılıkları içersin; kaynak sürümünün testleri geçince mevcut tek dosyalı Linux ve Windows Setup çıktısını yenile.

## Tamamlama kanıtları

Bu bölüm ilerledikçe dosya yolları, test sayıları, gerçek ağ/model kontrollerinin sınırları ve kalan işler ile güncellenir. Plan, uygulama durumu kesinleşmeden topluca tamamlandı işaretlenmez.


### Kaynak sürümü 0.2.0 — 2 Kasım kontrolü

- **170 test geçti** (17,7 sn). GGUF/Transformers dosya yolları, tüm katalog kaydı, indirme/resume/SHA, cache atomik güncelleme ve iptal, Windows ZIP çıkarma, GitHub kaynak önizlemesi ve özel varsayılan, MCP, model/ayar/eklenti ekranları, dosya arama/yazma, PDF/Office/görseller ve bellek kontrolleri kapsanıyor.
- Son incelemede plan/kapalı araç durumunda modelin beklenmeyen tool_call üretmesi, çoklu çağrıda durdurma sonrası yazma ve genel tool JSON'unun kesilmesi düzeltildi. Regresyon testleri eklendi. Görsel geçmişi toplam 16 görsel/32 MB taşıma sınırıyla korunur.
- **Hugging Face API kontrolü:** 51/51 katalog dosyası bulundu; boyut, commit ve SHA-256 metadata doğrulandı. Büyük model ağırlıkları bu geliştirmede indirilmedi.
- **Gerçek Windows CPU motoru:** resmi 19 MB ZIP doğrulandı; geçici klasörde Wine/Windows Python üzerinden kuruldu, 29 DLL ve `--version` başarılı (build 11412). CUDA/Vulkan paketlerinin metadata/SHA manifestleri kontrol edildi; büyük GPU paketleri ve fiziksel Windows GPU çıkarımı denenmedi.
- Tasarım mevcut native grafit/lavanta kimliği korunarak yenilendi. 940×640 ve masaüstü boylarında modeller, Genel, yerel model ekleme, eklenti ve GitHub akışları incelendi. Impeccable taraması temiz; source ekranlarının son yerel görüntüleri `/tmp/kayriva-final-*.png`. Bunlar kişisel veri içermeyen test ekranlarıdır.
- Linux tek dosya paketi gerçek açılış, 51 model/9 eklenti metadata, Windows motor manifesti ve ana süreç kapandıktan sonra kalıcı MCP yardımcısı kontrolünden geçti.
- Gerçek GitHub hesabında repo açılmadı/yükleme yapılmadı, üçüncü taraf MCP paketleri otomatik kurulmadı. Bu akışlar gerçek geçici Git ve taklit dış servislerle sınandı. Kurulum/yayın kullanıcı ilgili eylemi seçince gerçekleşir.
- Gerçek görsel model ağırlıklarıyla çıkarım ve bütün model ailelerinin karşılaştırmalı kalite/hız testi bu kapsama dahil değil. Görsel taşıma, eşleşen projektör seçimi, argümanlar ve içerik doğrulamaları test edildi. Büyük bir modeli düşük RAM'de aynı hız/kaliteyle çalıştırma veya sonsuza kadar yaşayan yayıncı bağlantısı garantisi verilmiyor.
- Kaynak dosya/araştırma girdileri ve kişisel runtime korunmuştur. `.gitignore` planı, belgeleri ve küratörlü katalogları hariç tutmaz. Bu klasör gerçek bir Git deposu olarak başlatılmamıştır; otomatik git init/commit/push yapılmadı.

- **Windows Setup 0.2.0 son kontrolü tamam:** geçici klasöre gerçek sessiz kurulum, Modeller/Genel ekranlarının açılışı, 51/9 katalogların kullanıcı verisine taşınması, Qt PDF DLL, MCP yardımcısı, yeniden kurulum ve kaldırma exit 0 ile geçti. Özel test kişisel veri işareti güncelleme/kaldırma sonrasında korundu. Fiziksel Windows makinesi yerine Wine kullanıldı.
- 0.2.0 dağıtımları: `dist/linux/Kayriva` (148.193.016 byte, tek uygulama dosyası); `dist/windows/Kayriva-Setup.exe` (35.408.510 byte, tek kurulum dosyası). Model ağırlıkları ve kişisel veri pakete dahil edilmedi. Derleme günlükleri `build/linux` ve `build/windows` altında; yeniden üretim tek `kayriva.sh` ile yapılır.

## Sürüm 0.3.0 — Model çeşitliliği ve paylaşım görünümü

- [x] NVIDIA dahil geniş katalog: **141 sürüm / 71 aile / 18 marka**. Önceki 51 sürüm korunarak 90 sürüm eklendi. NVIDIA 12 aile / 32 sürüm; ayrıca IBM, Liquid AI, Cohere, Allen AI, OpenBMB, InternLM, 01.AI ve ByteDance seçenekleri.
- [x] Yeni kayıtların gerçek dosya boyutu, SHA-256 ve commit bilgisini yayıncı API'siyle doğrula; tek dosyalı indirmeye eksik shard koyma, Windows'ta aynı dosya adına çakışma yaratma. Mimari kayıtlarını paketlenen llama.cpp b11412 ile karşılaştır. Lisansları tek bir açık kaynak lisansı gibi sunma.
- [x] Sidebar'da projeleri klasör/adet/açılma işaretiyle, iç sohbetleri girintili satırlarla göster. Yenilemede seçili proje sohbetini koru; iki listede aynı anda seçim bırakma. Kalıcı proje eylemleri, etiketli Ayarlar, kompakt Yeni sohbet ve görünür kısayol.
- [x] Buton, açılır liste, hover/odak ve Qt temel paletini aynı grafit/lavanta tasarımda birleştir. 18 marka sekmesini küçük pencereye zorla sığdırmak yerine native kaydırma davranışını koru.
- [x] README'yi kurulum, model, bellek, araçlar, veri konumları ve derleme rehberi olarak yeniden yaz. Kayriva için özgün SVG banner, üç gezinme görseli, yerel çalışma diyagramı ve test verileriyle gerçek arayüz görüntüsü ekle. Model kılavuzundaki eski cihaza özel başlangıç anlatımını genel kullanım rehberiyle değiştir.
- [x] Kişisel disk raporlarını `.gitignore` kapsamına al. Kaynak yayın önizlemesinde kod/katalog/belgeler dahil; sohbetler, araştırma girdisi, modeller ve derlemeler hariç. Hiçbir uzak depoya yükleme yapılmadı.
- [x] **174 test geçti** (32,6 sn). Ek kontroller indirme hedeflerinin çakışmaması, eksik shard, NVIDIA lisans/kapsamı, sidebar seçimi, kompakt yerleşim ve native klavye davranışını kapsıyor. SVG XML, README bağıl bağlantıları, Python derleme ve shell sözdizimi kontrolleri geçti.
- [x] Native arayüz 940×680, 1200×800 ve 1280×850 boylarında gözle incelendi. NVIDIA filtresi kompakt pencerede 12 aile / 32 sürümü gösterdi. Impeccable son taraması temiz. README görüntüsü gerçek uygulamadan, kişisel veri içermeyen örnek çalışma alanından alınmıştır.
- [x] Linux tek dosya paketi 0.3.0 olarak derlendi; ana ekran, Modeller ve Genel açılışı, 141 sürüm / 18 marka metadata, motor/eklenti varlıklarının taşınması ve bağımsız MCP yardımcısının 0.3.0 yanıtı kontrol edildi.
- [x] Windows Setup 0.3.0 derlendi; geçici Wine klasöründe gerçek kurulum, üç ekran açılışı, 141 sürüm / 18 marka katalog, MCP yardımcısının 0.3.0 yanıtı, yeniden kurulum/kaldırma ve kişisel test verisinin korunması kontrolü geçti. Fiziksel Windows GPU çıkarımı bu testin kapsamında değildir.

Model ağırlıkları bu turda indirilmedi; her model/kuantizasyonun fiziksel GPU'da hız ve kalite kıyaslaması yapıldığı iddia edilmez. Proje kaynak kodu lisansı seçilmediği için README bunu açıkça belirtir; üçüncü taraf model/font lisansları ayrıdır.

0.3.0 geliştirme dağıtımları: `dist/linux/Kayriva` (148.207.880 byte) ve `dist/windows/Kayriva-Setup.exe` (35.426.516 byte). SHA-256 özetleri `dist/SHA256SUMS` dosyasında bulunur. Derleme günlükleri `build/linux` ve `build/windows` altında tutulur.


## İlk genel yayın — 1.0.0-beta.1

İç geliştirmedeki 0.x etiketlerinden sonra ilk paylaşım **Kayriva 1.0 Beta 1** olarak hazırlanır. Git etiketi `v1.0.0-beta.1`; GitHub'da ön sürüm (pre-release) olarak işaretlenmelidir. Sonraki beta `1.0.0-beta.2`, yayın adayı `1.0.0-rc.1`, kararlı yayın `1.0.0` düzeninde ilerleyebilir. Bu adlar yayın aşamasını anlatır; uygulamanın yaşı değildir.

- Uygulama ve MCP sürümü: `1.0.0-beta.1`.
- Python paket araçları aynı değeri standart biçim olan `1.0.0b1` olarak normalleştirir.
- Windows kurulum adı/ürün sürümü beta etiketini taşır; sayısal dosya sürümü Windows biçimine uygun `1.0.0.0` olur.
- Kaynak koddan `./kayriva.sh start --version` ile sürüm görülebilir.
- Paylaşıma hazır İngilizce metin: [başlık ve release açıklaması](releases/v1.0.0-beta.1.md).

Kaynaklar: [SemVer ön sürümleri](https://semver.org/lang/tr/), [Python sürüm normalleştirmesi](https://packaging.python.org/en/latest/specifications/version-specifiers/#pre-release-spelling), [Inno Setup dosya sürümü](https://jrsoftware.org/ishelp/topic_setup_versioninfoversion.htm).

## İlk genel beta tamamlaması — Wiki, diller ve güncellemeler

- [x] Kullanıcının seçtiği güncelleme kaynağı `sayrias/Kayriva`. Bağlı GitHub aracıyla kontrolünde 404 döndü; depo/yayın oluşturulmadı. Uygulama yayımlanmamış kaynak durumunu sayfa içinde açıklar.
- [x] Açılışta sürüm kontrolü ve otomatik doğrulanmış hazırlama; kurulum yalnızca görünür **Restart to update / Güncellemek için yeniden başlat** eylemiyle. Taslak, ek, çalışan görev/indirme ve kaydedilmemiş dosya korunur. Kaynak koddan otomatik değiştirme yapılmaz.
- [x] 64 KiB blok farkı, taban/hedef SHA-256 doğrulaması, %85 boyut eşiği, tam pakete dönüş ve iptalde devam indirmesinin engellenmesi. Linux'ta aynı disk üzerinde değiştirme/yedek/erken hata geri alma; Windows'ta kapanış sonrası doğrulanmış Inno Setup. Bağımsız imza varmış gibi gösterilmez.
- [x] `kayriva.sh release`: iki platformun sürüm, boyut ve SHA kayıtlarını kontrol ederek manifest ve uygun fark dosyaları üretir. Önceki yayın dosyası `--previous` ile verilebilir. Yayınlama yapmaz.
- [x] İngilizce varsayılan arayüz, Türkçe seçimi; yeniden açıldığında uygulanır. Kullanıcı sohbeti/model yanıtı değiştirilmez. Katalog notları, eklenti açıklamaları, bilinen motor durumları ve ondalık gösterim de yerelleştirilir. README ve SVG tanıtım metinleri İngilizce; iki dilde sürüm notu vardır.
- [x] Kaynakla doğrulanan **51 sayfalık Türkçe Sayrias wiki paketi** hazır: 141 model sürümü, 71 aile ve 18 marka; bütün indirme kimlikleri ve lisans kaynakları. Anahtarlar, ebeveyn yolları, iç bağlantılar, sayfa/byte sınırları ve UTF-8 JSON doğrulandı. Paket kökteki `wiki-bundle.json` dosyasıdır; yayınlanmamış görsel/depo adresi uydurulmadı. Kaynak paylaşımı ve derlemeden hariçtir.
- [x] Özel notlar ve örnek wiki şeması `.local/notes` / `.local/wiki` altında toplandı, içerikleri korundu. Uygulama kaynak klasörlerinin yolları değiştirilmedi. `.aws`, ajan araçları, özel notlar, kullanıcı verisi ve wiki dışa aktarımları paylaşım önizlemesinden hariç.
- [x] **193 test geçti** (50,6 sn). Güncelleme servisinin 13 testi; gerçek geçici Linux kabuk değiştirme/geri alma, fark yeniden kurma ve bozuk/iptal aktarım senaryolarını içerir. Dil ve About bütünleşmesinin 6 testi varsayılan dil, kalıcı tercih, metadata filtreleri, arka plan kontrolü, otomatik hazırlama, açık yeniden başlatma ve taslak korumasını kapsar.
- [x] İki dilde 940×640 ve 1200×800 arayüz; uzun sürüm notu kaydırma, katalog ve ayarlar görüntülendi. İlk beta Linux paketi; ana ekran/Modeller/Genel/About, 141 kayıt ve bağımsız MCP yardımcısı 1.0.0-beta.1 kontrolünden geçti.
- [x] Son Windows Setup geçici Wine klasöründe kuruldu; ana ekran/Modeller/Genel/About, 141 kayıt / 18 marka ve MCP yardımcısı `1.0.0-beta.1` kontrolünden geçti. Yeniden kurulum, kaldırma ve ayrı test kullanıcı verisinin korunması doğrulandı. Gerçek yayımlanmış GitHub güncellemesi ve fiziksel Windows PowerShell/GPU davranışı bu geliştirmede denenmiş gibi sunulmaz; servis HTTP senaryoları kontrollü taklitlerledir.
- [x] Yeniden derlenen iki dağıtımın açılmış içeriğinde 88 uygulama modülü ve toplam 520.239.957 byte tarandı; bilinen gizli anahtar desenlerinde kişisel token bulunmadı. Ayarlar, sohbetler, özel notlar ve wiki dışa aktarımı paketlere dahil değildir. Denetim sonucu özel `.local/wiki/release-audit.json` dosyasındadır.
- [x] Son yayın manifesti gerçek dağıtım boyutları ve SHA-256 değerleriyle üretildi. Linux tek dosya: 148.313.344 byte; Windows Setup: 35.521.673 byte. `dist/SHA256SUMS` ve `dist/update-manifest.json` yayın dosyalarıyla eşleşir. İlk beta için önceki yayın tabanı olmadığı için fark dosyası üretilmez.

## Yayın metinlerinin sadeleştirilmesi

- [x] README, iki dilde sürüm notları, kullanım belgeleri, wiki paketi ve eklenti açıklamalarındaki harici asistan/hizmet karşılaştırmaları genel ifadelerle değiştirildi. Özgün araştırma notu özel `.local/notes` klasöründe korundu.
- [x] İş bölümünde uygulama adları yerine JSON/TOML bağlantı biçimi seçilir. Tercih dilden bağımsız kimlikle saklanır; eski profillerin TOML çıktısı korunur. İki çıktı biçimi ve profil geçişleri test edildi. Desteklenen model kimlikleri, güvenlik dışlama yolları ve gerçek servis uçları korunur.
- [x] 193 test geçti (47,3 sn); genel metin taraması, README bağlantıları ve 51 sayfalık wiki doğrulaması başarılı. İki platform yeniden derlendi ve güncelleme manifesti yenilendi.

## Linux uygulama kimliği ve ikon

- [x] Paket ilk normal açılışta kullanıcı uygulamalar menüsüne kalıcı masaüstü kaydı ve SVG ikon ekler. `io.github.sayrias.Kayriva` kimliği Qt masaüstü adıyla eşleşir; X11 sınıfı `Kayriva` olur. Kaynak kod ve ekran görüntüsü çalıştırmaları menüye kayıt yapmaz.
- [x] Kısayol geçici çıkarma dizinine değil gerçek çalıştırılabilir dosyaya gider; dosyayı taşıdıktan sonra açmak aynı kaydı günceller. Kullanıcı dizini salt okunursa uygulama açılır ve hata yerel günlüğe kaydedilir. `--install-desktop` pencere açmadan kayıt yapabilir.
- [x] 197 test geçti (48,6 sn). Gerçek masaüstü ayrıştırıcısıyla Türkçe/boşluk/özel karakterli yoldan başlatma, kalıcı ikon, taşınan dosya, tekrar kayıt ve Qt uygulama kimliği doğrulandı.
- [x] Yeniden derlenen Linux tek dosyası geçici X11 ekranında açıldı: ana pencere adı/sınıfı, pencere ikonu, normal açılışta menü kaydı, kalıcı ikon ve masaüstü dosyası doğrulaması geçti. Gerçek kullanıcının menüsüne veya çalışan uygulamasına dokunulmadı. Wayland masaüstünde elle doğrulama yapılmış gibi sunulmaz.
- [x] Linux güncelleme manifesti ve SHA-256 kayıtları yeniden üretildi; Windows paketi bu Linux düzeltmesi sırasında değiştirilmedi.

## Linux dosya yöneticisi ikonu

- [x] Menü/pencere ikonundan bağımsız olarak yayımlanan `Kayriva` dosya adına özel kullanıcı MIME tanımı eklendi: `application/x-kayriva-executable`, yerelleştirilmiş dosya türü ve uygulama ikonu. Dosya içeriği/ELF başlığı değiştirilmez.
- [x] Derleme bitiminde ve paket ilk açıldığında MIME önbelleği sistem aracıyla güncellenir; kaynak metadata değişmediyse önbellek yeniden yazılmaz. Sistem aracında hata veya eksiklik olması menü kaydını ve açılışı engellemez.
- [x] 199 test geçti (49,6 sn). Dosya türü, ikon çözümleme, farklı adlı yürütülebilir dosyanın korunması, önbellek tekrar kullanımı ve yardımcı araç bulunmadığında açılış davranışı kontrol edildi.
- [x] Kullanıcının dosya yöneticisi için mevcut kayıt uygulandı. KDE `kmimetypefinder`, gerçek dağıtım dosyasını özel türle tanıdı; `kiconfinder6` kullanıcıya ait kalıcı SVG ikonunu buldu. Başka bilgisayarda aynı yerel metadata ilk açılışta kurulur; adı değiştirilmeden kullanılan dosya için geçerlidir.
- [x] Linux tek dosya yeniden derlendi; paketin geçici kullanıcı veri alanında MIME tanımını ve kalıcı ikonu kurması, KDE ile tanınması doğrulandı. Güncelleme manifesti ve SHA-256 kayıtları yenilendi.

## Linux arşivi ve dağıtım uyumluluğu

- [x] Mevcut uygulama ve içindeki bağımsız köprü dahil 435 ELF nesnesinin GLIBC sembol gereksinimleri incelendi. Bu x86_64 derlemenin alt sınırı glibc 2.43'tür; bütün dağıtımlarda çalışma veya eski glibc/musl/ARM desteği iddia edilmez. Daha eski hedefler için daha eski tabanda ayrı derleme gerekir.
- [x] `Kayriva-1.0.0-beta.1-linux-x86_64.tar.gz` üretildi: aynı uygulama, ikon, kısa kurulum rehberi, uyumluluk JSON'u, font lisansı, klasör ikonu ve dosya SHA-256 kayıtları. Yedi sabit dosyalık liste kişisel veri, sohbet ve modelleri içermez.
- [x] `kayriva.sh archive-linux` ve menüde 12. seçenek eklendi. Linux derlemesi ve yayın hazırlığı da arşiv üretir; yayın SHA dosyası arşivi kapsar. Otomatik uygulama güncellemesi mevcut tek dosyalı çalıştırılabilir dosyayı kullanır.
- [x] Arşiv çıkarıldı, izinler ve dosya özetleri doğrulandı; içindeki uygulamanın sürüm komutu çalıştı. Tekrar üretim aynı arşiv SHA-256 değerini verdi; eski sürüm derlemesini paketleme isteği reddedildi. README bağlantıları ve shell sözdizimi kontrol edildi.
- [x] Linux gereksinimleri, İngilizce/Türkçe yayın metni ve wiki güncellendi. `.tar.gz` sıkıştırmasının sistem uyumluluğunu değiştirmediği açıkça belirtilir. Başka dağıtımlarda gerçek çalışma testi yapılmış gibi sunulmaz.

## 2 Kasım · Dil ve eklenti kütüphanesi düzeltmeleri

- [x] English/Türkçe kaydedildiği anda mevcut arayüze uygulanır. Sohbet, taslak, özel talimat, dosya içeriği ve filtre kimlikleri korunur. Bilinen varsayılan talimat metni arayüz dilinde gösterilir; özel metinler çevrilmez.
- [x] GPU katmanı için otomatik mod + model sınırına bağlı kaydırıcı/sayı alanı. Markalar için aranabilir, yüksekliği sınırlı seçim listesi. Dar pencerede form satırlarının yatay taşması giderildi.
- [x] 17 MCP bağlantısı: gerçek adlar ve alfabetik liste; Tümü/Yerel/Uzak/Eklenenler sekmeleri; alan filtresi, arama ve korunmuş seçim. Ayrıntılar kaydırılırken kaynak ve kurulum eylemleri görünür kalır.
- [x] Yeni bağlantılar resmî kaynaklarla karşılaştırıldı. API anahtarı isteyen yerel sunucular anahtar eksikken etkin olarak eklenemez. Bu çalışma yeni MCP paketlerini kurmadı veya ücretli araç çağrısı yapmadı.
- [x] 203 test geçti. EN/TR masaüstü ve 940×640 kompakt ekranları geçici verilerle incelendi. Linux ve Wine/Windows derlemeleri, Linux arşivi, güncelleme manifesti ve SHA-256 dosyaları yenilendi.

## 3 Kasım · Devam kaydı, araştırma ve belge akışı

- [x] Durdurulan/sınıra ulaşan son görev için Devam et; aynı proje sınırında kalıcı, 64 KB ile sınırlı checkpoint. Kaynak bağlamı, plan ve gerçek araç sonuçları tutulur; dış işlemin sonucu belirsizse tamamlandı sayılmaz.
- [x] Araştırmada tembel üçlü paralellik, sağlayıcı hata devresi, aşama süre bütçesi ve kısmi kaynak koruma. İlk araştırma için ayrı model planlama turu yok; büyük başarılı yazmalar sonraki istemde tekrar tam metin olarak işlenmez.
- [x] Belge yönergeleri: açıklayıcı bölümler, örnekler, eski/güncel sürüm ayrımı, gerçek kaynakça ve anlamlı create/append parçaları. Yerel Markdown önizlemesi ve iki belge/plan istemi.
- [x] Canlı işlem akışı çalışırken sürekli açık; gerçek araç argüman/sonuç genişletme, sınırlı ve bilinen kimlik bilgileri ayıklanmış ayrıntılar, aynı fazda birleşen bekleme bildirimleri.
- [x] 13 px yazma alanı içerikle büyür; küçük pencerede ekler ve alt düğmeler dahil yükseklik bütçesi, sonra kaydırma. Panodan görsel/dosya, sürükle-bırak ve kaldırılabilir ek önizlemeleri.
- [x] Proje/görsel/model seçicilerinde gerçek Qt dosya listesi ve boş ad alanı. Marka tetikleyicisi salt okunur; arama popup içinde.
- [x] 23 MCP bağlantısı; daha okunabilir kütüphane, çoklu npm binary seçimi ve eşzamanlı kurulum kilidi. Bozuk MCP bağlantısı sağlam bağlantıları engellemez; sınırlı ve iptal edilebilir bekleme.
- [x] Model indirmelerinde süreçler arası kilit, atomik devam metadata'sı, aralık/boş disk/SHA kontrolleri. Başarıda panelin otomatik kapanması, hatada yeniden deneme.

Doğrulama ve sınırlar: durdurma/araştırma/MCP/indirme senaryoları taklit dış servislerle ve gerçek geçici dosyalarla test edilir. İki dilde büyük/küçük Qt ekranları gözle incelenir. Gerçek büyük model/GPU hız kazanımı veya her üretilen belgenin doğruluğu garanti edilmez. Kullanıcının örnek belgesi değiştirilmedi; eski sürüm bilgisi ve yüzeysel kavram listeleri yeni yönergelerin hedefidir. Ayrıntılar: [Task workflows](workflows.md).

Son doğrulama: **233 test geçti** (71,4 sn). Linux AppImage FUSE’siz çıkarma/çalıştırma, iki ekran ve dış AppImage yoluna menü kaydı doğrulandı. Windows Setup Wine’da dört ekran, katalog eşleşmesi, MCP yardımcı sürümü, yeniden kurulum ve kaldırma akışını geçti. Üç dağıtım dosyasının SHA-256 değerleri doğrulandı; tar.gz içindeki AppImage aynı ve çalıştırma izni korunuyor. Paket taramasında bilinen sır biçimi veya kişisel runtime verisi bulunmadı; bu tarama bütün olası sır biçimlerini kapsayan garanti değildir. Wiki paketi 51 sayfa olarak yeniden üretildi ve JSON/bağlantı/üst sayfa kontrollerini geçti.

## Beta 2 · 3 Kasım 2026

- [x] Uygulama sürümü 1.0.0-beta.2; İngilizce yayın metni oluşturuldu. README ve yayın metninde referans uygulama karşılaştırması bulunmaz.
- [x] Yeni mesaj geldiğinde eski Devam et düğmesi kalkar; geçmiş yüklemesi ve tamamlanan yanıt aynı kurala tabidir.
- [x] Taslak ve geçmişte tıklanabilir görsel; sığdırma/1:1/yakınlaştırma. Küçük görseli büyütmeden hazırlama.
- [x] İlk doğal yaklaşım mesajı, gerçek ara bilgilendirmeler, açılır grup ve iç araç/payload ayrıntısı. Özel düşünce zinciri gösterilmez. Açılış kaydı 80 olaylık sınırda korunur.
- [x] MCP/Uygulamalar/Beceriler sekmeleri; 35 MCP bağlantısı, 17 uygulama görünümü, 8 özgün metin kılavuzu. Yerel SKILL.md ve sınırlandırılmış referans içe aktarma; turda en fazla iki ilgili beceri; gerçek okuma sonrası kullanım bildirimi.
- [x] Kurulum onay satırında ayırıcıdan boşluk, dar pencerede satırlara ayrılan eylemler ve iptal edilebilir bağlantı testi. Hesap/ortam anahtarı gereksinimleri doğru gösterilir.
- [x] MCP stdio ve sessiz HTTP beklemelerinde hızlı iptal; sınırlı bağlantı test süresi. Uzak çağrı başladıktan sonra iptal etmek dış işlemi geri almak değildir.

Doğrulama: 258 otomatik test geçti (90,4 sn). İngilizce/Türkçe geniş ve dar arayüzlerde akış, iç ayrıntı, görsel ve kütüphane görüntülendi. Belgelenen sınır: metin becerileri bağımsız bir model, terminal, renderer veya hesap izni sağlamaz; dış hizmetler kişisel yapılandırma gerektirir.

Beta 2 paket doğrulaması tamamlandı: Linux Type 2 AppImage sürüm/üç ekran/katalog/kalıcı menü yolu/MCP yardımcı testi geçti. Windows Setup Wine’da dört ekran, üç katalog eşleşmesi, yardımcı sürümü, yeniden kurulum ve kullanıcı verisini koruyan kaldırma testini geçti. SHA-256 doğrulandı; arşiv AppImage ile aynı ve çalıştırma izni korunuyor. Paket taramasında bilinen sır biçimi veya runtime verisi bulunmadı (106 uygulama modülü; genel sır yokluğu garantisi değildir). Wiki 51 sayfa olarak beta.2 sürümünde yeniden üretildi. Eski beta.1 arşivi dist yerine build/release-bases altında korundu.


## Beta 2 · Model listesi ve proje bağlamı son düzenlemesi

- [x] Model ekranı tek kompakt araç çubuğu, isteğe bağlı ayrıntılı filtreler; 940×640 arayüzde listenin sayfa yüksekliğine oranı %76. Varsayılan Tüm modeller / Varyantlar görünümü 141 kaydı ayrı satırda sunar; 71 aile için isteğe bağlı Aileler görünümü korunur.
- [x] Yazma alanı üzerinde seçili proje ve tam yol ipucu; yeni sohbet mevcut projeyi korur, proje seçicisi taslağı silmeden proje veya projesiz sohbet açar.
- [x] Sabit araştırma açılışı kaldırıldı. Açıklamalar gerçek modelin kullanıcı isteğine özgü ara mesajlarından gelir; anlatım için ek model turu yoktur.
- [x] 43 MCP bağlantısı ve 24 uygulama görünümü; Beceriler için doğrudan giriş. 8 yerleşik kılavuza ek olarak 6 özgün, kaynak commit ve lisansı doğrulanmış beceri paketi kullanıcı eklemesiyle etkinleşir. Uzun kılavuzlar sınırlı sayfalarda devam konumuyla okunabilir; tur başına iki kılavuz ve 16.000 karakter sınırı korunur.

Son kaynak doğrulaması: 269 otomatik test (62,6 sn) ve sıralaması değiştirilmiş 31 odaklı test geçti. Değişen arayüz/işçi/beceri kaynaklarında eksik Türkçe→İngilizce sabit metin anahtarı yok. Linux Type 2 AppImage sürüm, açılış, katalog, menü kaydı ve yardımcı araç kontrolünü geçti. Her iki pakette 77 beceri paketi dosyası kaynakla bayt bayt eşleşti. Üç dağıtım dosyasının SHA-256 değerleri ve arşiv içindeki AppImage/çalıştırma izni doğrulandı. Paket taramasında bilinen sır biçimi veya kişisel runtime verisi bulunmadı. Wiki 51 sayfa olarak yeniden üretildi.

Windows Setup Wine’da dört ekran, katalog eşleşmesi, yardımcı araç sürümü, yeniden kurulum ve kullanıcı verisini koruyan kaldırma kontrolünü geçti. Güncel AppImage, tar.gz, Windows Setup ve iki hedefli güncelleme manifesti yerel `dist/` altında hazırdır.
