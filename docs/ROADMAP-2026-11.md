# Kayriva geliştirme planı — 2 Kasım 2026

Bu dosya 2 Kasım isteğindeki bütün maddelerin kalıcı kaydıdır. `[ ]` tamamlanmamış, `[~]` uygulanıyor, `[x]` uygulama ve kontrolü tamamlanmış anlamına gelir. Bir özelliğin kodunun bulunması gerçek model/donanımda ölçüldüğü anlamına gelmez; doğrulama kapsamı ayrıca yazılır.

## Ürün sınırları

Yerel model üretimi, yerel kişisel veriler, native PySide6 arayüzü ve tek `.sh` derleme yönetimi korunur. Model/MCP indirme, web araştırma ve GitHub bağlantıları kullanıcının başlattığı ağ işlemleridir. ChatGPT'ye özel uygulamalar otomatik olarak üçüncü taraf bir uygulamaya taşınamaz; mümkünse açık MCP karşılığı, değilse bu sınırlama gösterilir. RAM/VRAM yoktan üretilemez; düşük bellek iyileştirmeleri kalite, bağlam ve hız karşılığında yapılır. Sınırsız kaynak/yanılmaz model iddiası yoktur.

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
- [x] C2. Dosyalar, web/tarayıcı, GitHub ve belge/PDF/tablo/sunum işlerine uygun açık MCP karşılıkları; ChatGPT'ye özel hizmetlerle uyumluluk sınırları açıkça gösterilsin.
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

- [x] G1. `gemini deepresearch.txt` tamamını incele; kaynak metni talimat olarak yürütme. Eski veya doğrulanmayan model adları/iddiaları düzelt.
- [x] G2. En kaliteli kodlama + araştırma + uzun çalışma + fotoğraf/dosya inceleme için yerel açık ağırlıklı modeller ve bulut ürünlerini ayrı değerlendir; resmi kaynak, donanım, lisans, kullanılabilir araç ve sınırlama bilgisiyle `docs/AI-RESEARCH-2026-11.md` hazırla.
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
- [x] Yeniden derlenen iki dağıtımın açılmış içeriğinde 88 uygulama modülü ve toplam 520.239.320 byte tarandı; bilinen gizli anahtar desenlerinde kişisel token bulunmadı. Ayarlar, sohbetler, özel notlar ve wiki dışa aktarımı paketlere dahil değildir. Denetim sonucu özel `.local/wiki/release-audit.json` dosyasındadır.
- [x] Son yayın manifesti gerçek dağıtım boyutları ve SHA-256 değerleriyle üretildi. Linux tek dosya: 148.308.984 byte; Windows Setup: 35.521.907 byte. `dist/SHA256SUMS` ve `dist/update-manifest.json` yayın dosyalarıyla eşleşir. İlk beta için önceki yayın tabanı olmadığı için fark dosyası üretilmez.
