# Model kütüphanesi

Kayriva modelleri marka, görev, dosya boyutu ve bellek sınıfına göre gösterir. Katalogdaki her sürümün yayıncı deposu, gerçek dosya boyutu, kuantizasyonu, SHA-256 özeti ve doğrulanan commit kimliği bulunur. Tam liste ve doğrulama kaynakları [katalog araştırmasında](model-catalog-research.md) yer alır.

## Model seçme

1. **Ayarlar → Modeller** sayfasını aç. Marka sekmesi ve aramayla aileyi bul; kod, akıl yürütme, görsel veya araç kullanımı filtresiyle daralt.
2. Boyut ve bellek sınıfını ayarla. Bu sınıflar kalite puanı değildir; daha büyük bir dosya daha iyi veya daha hızlı sonuç garantisi vermez.
3. Aynı modelin kuantizasyonunu kart içinden seç. Dosya boyutu, lisans ve cihazına uygunluk açıklamasını oku; ardından indir.
4. Kurulu modeli üst çubuktan seç. Genel ayarlardaki yerel motor hazırsa ilk mesajda model yüklenir.

**NVIDIA marka filtresi modelin üreticisini gösterir.** CUDA/Vulkan/CPU seçimi ise Genel sayfasındaki yerel motorla ilgilidir. Bir NVIDIA modelini listelemek, bütün NVIDIA ekran kartlarında aynı performansı vaat etmek anlamına gelmez. Mimari ve motor desteği model notlarında belirtilir.

## Bellek ve hız

Dosyanın disk boyutu, çıkarım sırasındaki toplam bellek tüketimi değildir. Ağırlıklara KV cache, çalışma tamponları ve varsa görsel projektör eklenir. MoE modellerinde yalnızca aktif parametre sayısına bakarak bellek hesabı yapılmaz; bütün ağırlıkların depolanması gerekir.

**GPU + RAM** ağırlıkları GPU ile sistem belleği arasında paylaştırır. Model VRAM'e tamamen sığmıyorsa çalışması mümkün olabilir; hız bellek aktarımı ve işlemciye bağlıdır. Kullanım üst sınırları Genel sayfasından ayarlanır. Otomatik bütçe, uygulamanın bellekte tuttuğu modelin alanını yeniden düşerek kendini küçültmez; diğer uygulamaların bellek ihtiyacı yine hesaba katılır.

Daha az bellekte denemek için daha küçük aile/kuantizasyon, daha kısa bağlam ve **Düşük bellek** profili kullanılabilir. Aşırı düşük bitli sıkıştırma kaliteyi bozabilir. Bellek yetersizse Kayriva hesaplanan sınırı ve düzeltilebilecek ayarları açıklar; sistem kapasitesini aşma garantisi vermez.

Model hazırlığı seçenekleri:

| Seçim | Davranış |
| --- | --- |
| İlk mesajda hazırla | İlk istekte yükler; aynı model ve çalışma ayarlarıyla sonraki mesajlarda bellekte korur. |
| Uygulamayla birlikte hazırla | Seçili model ve motor hazırsa uygulama açılışında yüklemeye başlar. |
| Yanıt sonrası belleği boşalt | Her yanıtın ardından motoru kapatır; sonraki istekte yükleme süresi tekrar oluşur. |

Bir modelin yeniden yüklenmesi, büyük bağlamın işlenmesi ve token üretimi farklı maliyetlerdir. Yanıtı tamamlanınca gösterme seçeneği ekranda yazı yazma etkisini kaldırır; motorun gerçek üretim hızını değiştirmez.

## Yerel dosya ekleme

**Yerel model ekle** ile dosya seçebilir veya yol yapıştırabilirsin. `.gguf` ve `.GGUF`, tırnaklı yollar ve `file://` adresleri tanınır. Dosya başka konumdaysa ağırlık kopyalanmaz; o konuma erişimin korunması gerekir.

- **GGUF:** Gerçek GGUF başlığı doğrulanır. Bölünmüş ağırlıklarda bütün parçalar aynı klasörde bulunmalıdır. Eksik parçayla model hazır gösterilmez.
- **Transformers:** Tek bir ağırlık shard'ı yerine `config.json`, tokenizer ve ağırlıkların bulunduğu tam klasörü seç. Bu motorun ek bağımlılıkları ayrıca kurulur; standart dağıtımın GGUF motoruyla aynı şey değildir.
- **Görsel modeller:** Uyumlu metin ağırlığı ve eşleşen `mmproj` dosyası gerekir. Kütüphane uygun projektörü ayrıca indirtebilir. Metin modeli yalnızca dosya adını görerek fotoğrafı inceleyemez. Transformers görsel çıkarımı bu sürümde desteklenmez.

## İndirme ve güncelleme

**Kataloğu yenile** yayıncıdan dosya kimliğini kontrol eder; model ağırlığı indirmez ve sohbet içeriği göndermez. İndirme sırasında geçici CDN adresi saklamak yerine depo, dosya ve sürüm yeniden çözülür. Aktarım tamamlandığında SHA-256 ve GGUF başlığı kontrol edilir; yarım kalan aktarım ancak içerik kimliği eşleşirse sürdürülür.

Yayıncılar depo veya dosyaları kaldırabilir; hiçbir dış bağlantının sonsuza kadar çalışacağı vaat edilmez. Ağ/erişim hatasında son doğrulanmış kayıtlar ve mevcut yerel dosyalar korunur. Model kartı, lisans koşulları ve kullanım alanları yayıncının bağlantısından açılır. Katalogda yer almak, her modelin gerçek donanımda hız/kalite testinden geçtiği anlamına gelmez.
