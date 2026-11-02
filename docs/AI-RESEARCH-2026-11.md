# Kodlama, araştırma ve dosya/görsel analizi için model seçimi

**Kontrol tarihi: 2 Kasım 2026.** Kaynaklar yayıncıların model kartları ve resmi ürün belgeleridir. Bu bir satın alma yönlendirmesi veya modellerin bu bilgisayarda karşılaştırmalı performans ölçümü değildir. Model sürümleri, planlar ve kotalar değişebilir. Aşağıdaki öneriler iş yükü ve donanım kısıtlarından yapılan değerlendirmelerdir; bütün modeller için ortak bir “en iyi” sıralaması değildir.

## Senin kullanımına uygun başlangıç

Yaklaşık 16 GB RAM / 6 GB VRAM sınıfında tek modelle kodlama, araştırma ve ekran görüntüsü incelemek için **Qwen3.5 4B'nin dengeli bir GGUF kuantizasyonu**, eşleşen görsel projektörle birlikte, ilk denenebilir aday. 9B sürümü daha fazla bellek ve zaman karşılığında alternatif; gerçek hız ve doğruluk projelerinde ölçülmeli. **27B IQ2** dosyasının küçük olması 27B'yi tamamen GPU'ya sığdırmaz; ağırlık, KV cache, projektör ve çalışma alanı birlikte değerlendirilir. Çok düşük bit kaliteli kod üretimini bozabilir. Bu yüzden 27B'yi tek günlük model yapmak yerine küçük, daha az sıkıştırılmış adayla aynı görevlerde karşılaştırmak daha anlamlıdır. [Qwen3.5 4B model kartı](https://huggingface.co/Qwen/Qwen3.5-4B), [GGUF yayıncısının dosyaları](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF).

Kayriva'da web araması, dosya düzenleme ve görev yürütme modele araç olarak sağlanır. Bir modelin ağırlıklarını indirmek bu yetenekleri kendiliğinden vermez. Uzun süre çalışması da tek başına daha doğru sonuç verdiğini göstermez: ara sonuç, gerçek dosya değişikliği, test ve kaynak doğrulaması gerekir.

## Yerel / açık ağırlıklı kısa liste

| Aday | Uygun iş | Dikkat edilecek nokta |
|---|---|---|
| Qwen3.5 4B / 9B | Genel kullanım, kod, görsel ve belge metniyle çalışma | GGUF görsel analizinde modelle eşleşen mmproj gerekir; bağlam arttıkça bellek tüketimi artar. |
| Qwen3.8 27B | Daha büyük, çok amaçlı kod/görsel adayı | 6 GB VRAM'de hibrit çalışma gerektirebilir; düşük bit sürümün kalite/hız kaybını ölç. Apache 2.0 olarak yayımlanıyor. [Kart](https://huggingface.co/Qwen/Qwen3.8-27B). |
| Qwen3-Coder-Next | Uzun araç akışları ve yazılım geliştirme | 80B toplam / 3B aktif parametre. “3B aktif” bütün ağırlıkların 3B kadar bellek istediği anlamına gelmez. Metin odaklı; model kartı ayrı düşünme modu olmadığını belirtiyor. [Kart](https://huggingface.co/Qwen/Qwen3-Coder-Next). |
| DeepSeek-R1-0528-Qwen3-8B | Mantık, matematik ve zor problem denemeleri | Metin modeli; görsel inceleme için ayrı görsel model gerekir. Araç uyumu ayrıca denenmeli. MIT lisansıyla yayımlanmış. [Kart](https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B). |
| Devstral Small 2 24B | Kod tabanı keşfi, çok dosya düzenleme ve yazılım ajanı | Küçük 4B ile aynı donanım sınıfında değerlendirilmemeli; quant ve motor desteği kontrol edilmeli. Apache 2.0. [Kart](https://huggingface.co/mistralai/Devstral-Small-2-24B-Instruct-2512). |
| Gemma 3 4B | Görsel/metin ve belge inceleme için alternatif | Gemma lisansı Apache/MIT değildir; şartları ayrı okunmalı. Eşleşen projektör ve motor gerektirir. [Kart](https://huggingface.co/google/gemma-3-4b-it). |
| GLM-5.3 | Büyük sunucu sınıfında uzun araç/kod çalışmaları için araştırılabilir | Resmi kartın lisansı `glm-5.3`; verilen rapordaki genel “MIT” iddiasını bu sürüme taşımamak gerekir. 6 GB GPU'ya uygun günlük aday olarak sunulmuyor. [Kart](https://huggingface.co/zai-org/GLM-5.3). |
| Kimi K3 | Büyük multimodal ve araç iş yükleri için araştırılabilir | Resmi kart özel `kimi-k3` lisansını ve özel kod gereksinimini gösteriyor. Kayriva uzak model kodunu çalıştırmaz; karttaki örneği körlemesine kopyalamak destek anlamına gelmez. [Kart](https://huggingface.co/moonshotai/Kimi-K3). |

“Açık ağırlıklı” ile tüm eğitim verisi/kodu açık kaynak olan ürün aynı şey değildir. Her model ve topluluk kuantizasyonunun lisansını ayrı kontrol et. Katalogda listelenmek, bu cihazda o mimarinin gerçek ağırlıklarıyla test edildiği anlamına gelmez.

## Bulut seçenekleri

**OpenAI:** Resmi belgeler zor kodlama ve profesyonel işler için GPT-6 Astra'yı, maliyet/hız dengesi için GPT-6.1 Sol'u; görsel muhakeme ve ekran işleri için GPT-6.1 Terra'yı öne çıkarıyor. Kod ajanı için Codex, araştırma için uygun araçlar gerekir. API modeli ile ChatGPT/Codex aboneliği aynı fiyat/kota veya aynı özellik seti değildir. Düşünme seviyesi yükseltilebilir, fakat uzun çalışma için araç sonuçları ve bağlam yönetimi de gerekir. [Güncel model rehberi](https://developers.openai.com/api/docs/guides/latest-model), [görsel giriş belgeleri](https://developers.openai.com/api/docs/guides/images-vision).

**Anthropic:** Güncel resmi tabloda Claude Opus 5.5 uzun kod/ajan işleri, Sonnet 5.5 hız/zeka dengesi, Fable 5.1 zor muhakeme ve uzun ufuklu işler için konumlandırılıyor. Güncel aile metin ve görsel girişini, araç kullanımını destekliyor. Bir üreticinin konumlandırmasını bağımsız başarı garantisi olarak yorumlamamak gerekir; aynı repo görevlerinde karşılaştır. [Resmi model tablosu](https://platform.claude.com/docs/en/models/overview).

**Google:** Güncel listede Gemini 4 Argon muhakeme, Gemini 3.8 Flash uzun yazılım/ajan iş akışları için yer alıyor. Argon için belgelenen bağlam **1M**; verilen rapordaki tüm Gemini'lere genellenmiş “2 milyon+” iddiası doğru bir ürün seçme ölçütü değil. Uygulamadaki Deep Research deneyimi, API'deki temel model çağrısından ayrı ürün/araç akışıdır. [Modeller](https://ai.google.dev/gemini-api/docs/models), [düşünme ayarları](https://ai.google.dev/gemini-api/docs/thinking).

Maksimum kalite aranıyorsa bu üç sağlayıcının üst sınıf kod ajanlarını aynı küçük değerlendirme setinde denemek, yalnızca bir benchmark tablosuna bakmaktan daha faydalı. Burada bulut modellerini Kayriva'ya gizlice bağlamadık: uygulamanın model üretimi yerel kalır. Bulut sağlayıcıları bu raporda alternatif ürünler olarak karşılaştırılıyor.

## Düşük bellekle daha büyük iş: gerçekçi yöntemler

llama.cpp'de kuantize GGUF, CPU/GPU katman bölüşümü, mmap, daha küçük mikro batch, kısa çalışma bağlamı ve Q8/Q4 KV cache birlikte kullanılabilir. Kayriva'nın **Düşük bellek** profili F16 seçili cache'i Q8'e geçirir, prompt batch/mikro batch'i küçültür ve otomatik bağlamı daha küçük başlatır. Kullanıcının açık sayısal bağlam tercihi korunur. Motorun mevcut modele ait bütçesi tekrar azaltılmaz; yeni yüklemede gerçek boş alan ölçülür. Q8 KV her mimari/motor kombinasyonunda garanti değildir; desteklenmezse dengeli/F16'ya dönmek gerekir. [llama.cpp argümanları](https://github.com/ggml-org/llama.cpp/blob/master/common/arg.cpp).

Görsel projektörü CPU'da tutmak GPU'daki metin ağırlıklarına yer bırakır, fakat RAM ve zaman ister. Kayriva bunu bütçeye ekler. Modelle yanlış projektör seçilirse çalışır kabul etmek yerine motor hatası gösterilir. [Resmi multimodal rehberi](https://github.com/ggml-org/llama.cpp/blob/master/docs/multimodal.md).

KTransformers gibi heterojen yürütme sistemleri bazı büyük MoE modellerinde CPU/GPU iş dağılımını geliştirir; belirli donanım, RAM, kernel ve model desteği gerektirir. Bu nedenle tüketici cihazına “yoksa biz yaparız, her büyük model çalışır” şeklinde bir çözüm sunulamaz. Kayriva'nın llama.cpp çalışmasını değiştirmeden bu ayrı backend'i otomatik kurmadık. [KTransformers projesi](https://github.com/kvcache-ai/ktransformers).

Disk/swap kullanımı çökme riskini azaltabilecek bir işletim sistemi mekanizmasıdır; fiziksel RAM veya VRAM yaratmaz. Çok büyük modelin ağırlıklarını sürekli diskten okumak ciddi yavaşlama yaratabilir. Uzun projede bütün dosyaları bağlama doldurmak yerine dosya araması, satır aralığı okuma ve ihtiyaca göre belge metni kullanmak da bellek tüketimini azaltır.

## Verilen Gemini raporunun denetimi

`gemini deepresearch.txt` tamamı (31.508 karakter) okundu; içindeki çalıştırma örnekleri talimat sayılmadı. Raporun model + araç sistemi ayrımı, kuantizasyon, bağlam/cache maliyeti ve büyük belgede seçici okuma yaklaşımı faydalı. Ancak:

- Claude 3.7/o3-mini gibi eski örneklerle yeni nesil ürün adları aynı “en iyi” değerlendirmesinde karıştırılmış. Yukarıdaki liste resmi güncel sayfalardan yeniden çıkarıldı.
- “Hatasız”, “kusursuz”, “rakipsiz” ve donanım/ayar/test verilmeden 50–90+ token/sn iddiaları doğrulanmış sonuç kabul edilemez.
- Gemini için genel 2M bağlam, GLM-5.3 için genel MIT lisansı ve bütün sistemlerin saatlerce bağlam kaybetmeden çalışacağı iddiası düzeltilmeli.
- o3-mini'nin dahili yöntemini MCTS olarak açıklamak veya Deep Research'ü otomatik olarak o modele bağlamak için raporda yeterli birincil kanıt yok.
- Çok düşük bit ile küçültülmüş dosya, aynı büyüklükteki tam hassasiyetli modelin kalitesini ve hızını korumaz. Görsel model/projektör belleği tabloda ayrıca hesaba katılmalı.

## Seçim için aynı görevlerle deneme

Beş gerçek görev seç: mevcut projedeki bir hatayı düzeltme, birkaç dosyayı etkileyen özellik, ekran görüntüsünden hata bulma, resmi belgelerle kaynaklı rapor, yeni dosya oluşturup sonucu yeniden okuma. Her adayda aynı girdiyle test başarısı, doğru dosyalar, doğrulanabilir kaynaklar, ilk çıktı/toplam süre, bellek ve toplam maliyeti kaydet. Araç çıktısı ve test kanıtı olmayan “tamamladım” mesajını başarı sayma. Bu, model adı veya uzun düşünme süresinden daha sağlam bir seçim ölçütüdür.
