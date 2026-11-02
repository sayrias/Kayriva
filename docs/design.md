# Arayüz tasarım notları

5 Ekim 2026 güncellemesi. Native Qt uygulaması korunur; internetten alınan tasarım rehberleri için bir web arayüzüne geçilmedi.

## Araştırılan kaynaklar

[Lovable — Prompting best practices](https://docs.lovable.dev/prompting/prompting-one), [v0 — Text Prompting](https://v0.app/docs/text-prompting) ve [Vercel — Web Interface Guidelines](https://vercel.com/design/guidelines) yeniden incelendi. Bileşenleri tek tek tarif etme, gerçek içerikle çalışma, tutarlı yerleşim ve klavyeden erişim yaklaşımı Qt arayüzüne uyarlandı. Superdesign ve Refero istem örnekleriyle birlikte değerlendirildi; buradaki web teknolojisi önerileri kurulmadı.

Bu turdaki tasarım yönü: grafit zemin `#1b1d23`, sidebar `#15171c`, kart `#24272f`, yazma alanı `#282b34`, yazı `#ececf1`, soluk lavanta vurgu `#c9bcec`. Kartlarda tek düz yüzey, yazma alanında 20 px köşe, seçili satırlarda nötr kontrast kullanılır. Uzun Markdown yanıtlarında gerçek Qt metin bloklarına satır/paragraph aralığı uygulanır. Küçük pencerede karşılama alanının dikey boşlukları azalır.

İşlevsel eklemeler: başlık/mesaj araması, proje içindeki eşleşmeleri açma, sohbet sabitleme, tüm sohbeti Markdown kaydetme; yerelde saklanan, düzenlenebilen ve silme sonrası geri alınabilen istem kütüphanesi. Kütüphane mevcut taslağı korur; eklediği istemi kendiliğinden göndermez. `Ctrl+K` kütüphaneyi, `Ctrl+Shift+F` sohbet aramasını açar. Sohbet adı ve istem düzenleyicisi aynı pencerenin içinde açılır.

[Superdesign — UI Design Prompts](https://superdesign.dev/blog/ui-design-prompts): tasarım isteminde hedef, yerleşim, görsel sistem ve durumların belirlenmesi; tutarlı bir tasarım bağlamının korunması. Buradaki istem örnekleri masaüstü uygulamasının ihtiyaçlarına uyarlandı.

[Refero — Design Prompts](https://styles.refero.design/ai-agents/v0-design-prompts): ekranın, içeriğin ve etkileşim durumlarının tarif edilmesi; oluşturulan görünümün mevcut bileşenler ve erişilebilirlikle birlikte değerlendirilmesi.

[Microsoft HAX](https://www.microsoft.com/en-us/haxtoolkit/ai-guidelines/): insan-AI etkileşimi için rehberler. Bu projede önerileri ölçülmüş sonuç gibi sunmamak, kullanıcıya seçim ve kontrol vermek ilkeleri benimsendi.

[UI Prompt Library — Settings Pages](https://uipromptlibrary.com/resources/app-ui-prompts-for-settings-pages/) ve [AI Workflow Builder](https://uipromptlibrary.com/ai-workflow-builder-prompts/): belirli ekran görevlerini, kontrol hiyerarşisini ve boş/hata durumlarını tarif eden örnekler incelendi. Bu uygulamada ayar sayfaları beş başlık altında düzenlendi, MCP satırları küçük eylemlerle düzenlendi ve görev ekranına boş durum eklendi.

[UIPrompt](https://uiprompt.app/): renk, yazı, boşluk ve bileşen bağlamını birlikte tarif etme yaklaşımı incelendi. Native Qt’ye uyarlamada nötr yüzeyler, 12–13 px ayar yazıları, 28–32 px küçük kontroller, 16–18 px SVG ikonlar ve tek soluk mor vurgu kullanıldı. Bu kaynak web framework’ü kurma talimatı olarak uygulanmadı.

[Refactoring UI](https://refactoringui.com/): arayüz hiyerarşisi ve tasarım örnekleri incelendi; kitap içeriği satın alınmadı. Birincil Kaydet eylemi sağ alta alındı, ikincil eylemler küçültüldü ve açıklamalar kısa tutuldu.

## Uygulanan düzen

- Ana ekranın vurgu rengi soluk mor; yüzeyler nötr koyu. Yoğun renk ve gereksiz çerçeve azaltılır.
- Yazma kutusunun ekleme menüsü kompakt liste satırlarıdır: küçük SVG, kısa ad, ikincil açıklama, varsa durum ve yön oku. Web ayrıntıları ikinci listede açılır.
- Ayarlar ana pencerenin içinde, karartılmış arka plan üzerinde açılır; ayrı işletim sistemi penceresi yoktur. Solda küçük navigasyon, sağda içerik kullanır. Ana sohbet sidebar’ına ayar sayfaları eklenmez.
- Model kartları aileye göre gruplanır; kuantizasyon/boyut aynı karttaki seçicide değişir. Tek bir İndir/Kullan eylemi seçili sürüme bağlıdır.
- Donanım profili üstte görünür. GPU adayı, RAM + GPU, CPU + RAM veya bellek sınırında etiketleri tahmin olarak sunulur. Ayrıntı ve kalite uyarısı tooltip’te bulunur; düşük bit uyarısı kartta da görünür.
- Boş, yüklü, seçili ve indirme durumları açıkça ayrılır. İndirilmeyen varsayılan modele “Seçili” etiketi verilmez.

## Sonraki tasarım değişiklikleri için istem

```text
Kayriva için native PySide6 masaüstü arayüzünü geliştir.
Kullanıcı yerel modellerle sohbet eder, proje dosyaları ve MCP araçlarıyla çalışır.
Koyu nötr yüzeyler, tek soluk mor vurgu, küçük tutarlı SVG ikonlar kullan.
Ana sidebar yalnızca sohbetler ve açılır projeler içerir.
Ayarlar ana pencerenin içinde, soldan gezinilen beş bölümlü bir modaldır.
Başlık çubuğu olan ayrı pencere oluşturma; Esc ve dış alanla kapanmayı koru.
Sayfalar: Genel, Modeller, Bağlantılar, İş bölümü, Kullanım.
Kullanımda Anlık hız grafiği ve ölçülen/tahmini ayrımı; geçmişte dönem seçicileri, günlük grafik ve model tablosu kullan.
Model seçicisinde arama ve kısa model satırları sun; yüklü model yoksa bir model etkinmiş gibi gösterme.
Donanım ve işlem onayı modalını aynı native pencerenin içinde aç.
CPU seçeneklerini algılanan sınırla, katman ve bağlamı yerel model metadata’sıyla sınırla.
İş bölümünde asistan adı, rol ve talimatlar kullanıcı tarafından ayarlansın.
Ekleme menüsünde büyük buton kutuları yerine kısa liste satırları kullan.
İleri seçenekleri kullanıcı ilgili satıra bastığında göster.
Model ailesini bir kartta tut; kuantizasyon ve boyutu seçicide sun.
Donanım önerilerini tahmin olarak etiketle; ölçülmemiş hız veya kesin uyum yazma.
Mevcut gerçek işlevleri koru; çalışmayan özellikleri menüye ekleme.
Boş/yüklü/seçili/indirme/hata durumlarını ve klavye odaklarını değerlendir.
Kısa Türkçe metinler, 8–10 px küçük kontrol ve 14–16 px panel köşeleri kullan.
Sohbet başlamadan görünen animasyonu yanıt üretimi sırasında durdur.
```

## Proje, bellek ve araştırma düzeltmeleri

Proje satırları özel Qt delegate ile çizilir: klasör simgesi, sağda açılma işareti, 20 px sohbet girintisi, 36 px satır, 7 px yuvarlak seçim alanı. Native branch seçiminin sol kenarda renk şeridi oluşturması engellendi. Kaydırma çubukları 11 px genişliğinde, iç marjı sıfır; görünen tutamağın merkezi tıklanabilir alana denk gelir.

Bellekteki modelin otomatik yükleme bütçesi korunur, anlık boş alan ayrı görünür. Araştırma kapsamı ana pencere içinde üç küçük seçiciyle ayarlanır. Kaynaklar modalı başlık/site araması, okunan sayfa ile arama özeti ayrımı, önizleme ve Kaynağı aç eylemi sunar. Aynı bağlantılar birleştirilir; site çeşitliliği önceliklidir.

## 2 Kasım 2026 · Kütüphane ve araç akışları

Yüzey modu Operate: yerleşik koyu grafit/lavanta düzen korunur. Model sayfasında düz `#242832` yüzey, 14 px köşe, 15 px model adı, 12 px özellik satırı ve küçük eylemler kullanılır. Seçim ve arama aynı yerde kalır; başlıktaki yinelenen üç nokta menüsü kaldırılır. Ayarlara sol alt köşedeki SVG simgesinden ulaşılır. Karşılama ekranındaki başlık öncesi küçük slogan satırı kaldırılmıştır.

Model kütüphanesi yayıncı sekmeleri, ad/kuantizasyon araması, yüklü/önerilen durum seçicisi ve kullanım amacıyla süzülür. Boyut ve kapasite kontrolleri istendiğinde açılan iki slider'dır. Düşük/orta/yüksek/çok yüksek/ultra sınıfları sırasıyla ≤2/≤5/≤10/≤20/>20 GB model dosyası içindir; kalite puanı veya ölçülmüş çalışma hızı değildir. Dosya boyutu filtresi bağımsızdır. Özellik filtreleri katalog metadata'sını kullanır; isimden görsel yeteneği uydurulmaz. Web araştırma ve metin dosyası incelemenin Kayriva araçlarıyla sağlandığı açıklanır.

Görsel mimari etiketi tek başına çalışan görsel destek iddiası değildir. Eşleşen mmproj gerekliliği görünürdür; projektör için ayrı, isteğe bağlı indirme eylemi sunulur. Projektör indirildiğinde etkin sohbet modeli değişmez. Genel ayarlarda eşleşen projektör dosyası, bellek yaklaşımı ve uzun çalışmanın tur/süre sınırları bulunur. Sınıra ulaşan görev tamamlandı diye gösterilmez.

Yerel model ekleme, ana pencerenin içindeki odaklı bir diyalogdur. Dosya, klasör ve yapıştırılan yol aynı doğrulamaya gider; motor dosyaya göre belirlenir. Büyük/küçük harf GGUF uzantıları ve Tüm dosyalar seçimi korunur. Hatalı yol diyalogu kapatmaz, düzeltilebilir açıklama gösterir. İçe aktarılan modeller kopyalanmaz; yolları hatırlanır ve hızlı model seçicisinden yeniden seçilebilir.

Katalog yenilemesi arayüzü bloke etmeyen ve durdurulabilen bir işlemdir. Mevcut kütüphane bağlantı hatasında korunur. Model indirme kontrolü, indirildi/seçili durumu ve güncel bağlantı metadata'sı birbirinden ayrılır; hiçbir bağlantı için “hiç bozulmaz” sözü verilmez.

Bağlantılar sayfasındaki Eklenti kütüphanesi, bağımsız MCP araçlarını erişim ve gereksinimleriyle sunar. Başka uygulamalara özel eklentilerin doğrudan taşınabildiği iddia edilmez. GitHub proje başlığından, proje menüsünden ve dosya alanından açılır; proje menüsü tıklanan klasörü geçirir. Her iki akış da aynı pencerenin içindeki diyalog desenini kullanır.

## 2 Kasım 2026 · Sidebar ve seçim kontrolleri

Ana sidebar'da grafik dünya korunur; gezinme artık üç açık gruptur: yeni sohbet ve arama, projeler, sohbet geçmişi. Yeni sohbet 36 px yüksekliğinde tek bir satırdır; `Ctrl+N` kısayolu sağda görünür. Proje ekleme, aç/kapat ve GitHub eylemleri sürekli görünür; fareyle üzerine gelme zorunluluğu yoktur. Ayarlar sol altta adı ve simgesiyle bulunur.

Proje ve sohbet satırları aynı native delegate ile 36 px ritimde çizilir. Projelerin klasör simgesi, sohbet adedi ve sağda açılma işareti vardır. İç sohbetler 20 px girinti ve küçük konuşma simgesiyle ayrılır; sabitlenmiş sohbetlerde iğne simgesi korunur. Seçim `#303542`, hover `#22262f`; odak 1 px lavanta çizgidir. Eski native seçim şeridi kullanılmaz. Bir konuşma açıldığında seçim yalnızca onun satırında kalır; liste yenilendiğinde proje içindeki seçili sohbet kaybolmaz.

Açılır seçenekler, native klavye davranışını koruyan `ChoiceBox` üzerinden okunur satırlar ve en fazla on görünür seçenekle açılır. Girdi yüzeyleri nötr grafittir; odak ve seçim lavanta ailesindedir. Ana `QPalette` de aynı renklere taşındığından işletim sisteminin varsayılan yeşil seçimi arada görünmez. Model markaları, yatay kaydırma okları yerine aranabilir ve yüksekliği sınırlı bir seçim listesinde gösterilir. 940 px pencere genişliğinde arama ve amaç filtresi kullanılabilir kalır; karşılama alanı dikeyde daha sıkı yerleşir.

[Prompts.chat](https://prompts.chat/) ve [Get Prompt Library](https://getpromptlibrary.com/) için incelenen görev gruplama, arama ve doğrudan eylem yaklaşımı burada masaüstü gezinmesine uyarlandı. Site görünümü veya web kart ızgarası kopyalanmadı. Kayriva'nın koyu grafit/lavanta yüzeyleri ve kendi çizgi ikonları korundu.

Doğrulama: kişisel veri içermeyen geçici bir çalışma alanında 1200×800 ve 1280×850 masaüstü, 940×680 kompakt pencere; karşılama, proje içi sohbet, model kütüphanesi ve genel ayarlar gözle incelendi. Proje seçimlerinin yenilemede korunması, iki listenin aynı anda seçili görünmemesi, kalıcı proje eylemleri ve native açılır listelerin ok tuşları ayrıca test edilir.

## İlk genel beta · Dil ve güncellemeler

Varsayılan arayüz İngilizcedir; Genel sayfasındaki English/Türkçe seçimi Kaydet ile hemen uygulanır; açık arayüz nesneleri korunur. Çeviri, yalnızca uygulamanın bildiği sabit metinleri ve sınırlı runtime şablonlarını kapsar. Kullanıcı mesajı, model çıktısı, dosya yolu ve özel MCP adı çevrilmez. İngilizce ve Türkçe ondalık bellek gösterimi kendi nokta/virgül biçimini kullanır.

Altıncı ayar sekmesi kısa **About / Hakkında** adını taşır; sayfa başlığı **About & updates / Hakkında ve güncellemeler** olur. Sürüm, platform, yapılandırılmış GitHub kaynağı ve iki tercih görünür: başlangıç kontrolü ve otomatik indirme. Kontrol ikincil eylemdir; doğrulanmış güncellemenin indirilmesi/yeniden başlatılması lavanta birincil düğmeyle yapılır. Ağ ve 404 hataları aynı sayfada açıklanır; açılışta hata modalı çıkmaz. Uzun sürüm notlarında sayfanın kaydırılabilirliği korunur.

Otomatik indirme, kurulum için otomatik kapanma anlamına gelmez. Görünür yeniden başlatma eylemi; görev, indirme, taslak, eklenmiş dosya ve kaydedilmemiş editör değişikliği varken bekler. Kaynak koddan çalışmada başlangıç kontrolü ve otomatik kurulum kapalıdır. Arayüz 940×640 ve 1200×800 boylarında iki dilde, uzun sürüm notu ve boş/yayınlanmamış kaynak durumlarıyla incelendi. Native Python dosyaları için tasarım taraması yalnız regex kurallarını çalıştırabilir; kontrast ve taşma incelemesi ekran görüntülerinde ayrıca yapılır.


## Dil, kapasite seçimi ve eklenti kütüphanesi · 2 Kasım 2026

Çevrilecek arayüz metinleri kaynak anahtarlarına bağlıdır. Dil değişimi açık sohbeti, taslağı, özel talimatları, dosya içeriğini veya filtre kimliklerini yeniden oluşturmaz. Form satırları dar pencerede sarılır; alanlar yatay taşmaz. GPU katmanları Otomatik onayı, kaydırıcı ve sayı alanıyla ayarlanır; üst sınır seçili modelden okunur. Genel açılır listeler sınırlı yükseklikte kaydırılır.

Eklenti listesi alfabetik gerçek adları gösterir: Filesystem, Playwright, MarkItDown ve diğer MCP adları çevrilmez. İkinci satır kısa alan etiketidir. Tümü / Yerel / Uzak / Eklenenler sekmeleri bağlantı kapsamını, alan seçimi kullanım alanını filtreler. Arama, yayıncı ve açıklamaları da kapsar. Sağ tarafta yayıncı, bağlantı türü, açıklama, erişim kapsamı ve gereksinimler bulunur. Ayrıntılar kaydırılabilir; kaynak ve kurulum eylemleri sabit alt sırada kalır. Boş arama sonuçları kurulum başlatamaz. Katalog 17 bağlantı içerir.
