# Uygulamanın model motoru

Ollama, LM Studio, bulut inference veya üçüncü taraf bir masaüstü uygulaması gerekmez. Native Qt arayüzü Python ile; ağır hesaplama uygulamanın kendi `engine/bin/llama-server` C/C++ süreciyle yapılır. Süreç uygulama tarafından başlatılır/kapatılır; yalnızca loopback adresine bağlanır. Her açılışta rastgele port ve API anahtarı kullanılır. Motor `--offline --no-webui` ile açılır. Yerel HTTP, süreçler arası iletişimdir; herhangi bir bulut API çağrısı değildir.

## Kurulum

Genel → Yerel motor listesinden **CPU**, **Vulkan GPU** veya **CUDA NVIDIA** seç; paket eksikse **Kur** düğmesine bas. Özel bir motor için listenin en altındaki **Dosya seç…** ile çalıştırılabilir `llama-server` (Windows'ta `llama-server.exe`) seçilir. Hazır paketler [resmi llama.cpp b11412 sürümünden](https://github.com/ggml-org/llama.cpp/releases/tag/b11412) alınır, SHA-256 ve çalışabilirlik doğrulanır. Sürüm/özetler `releases.json` içindedir. Hazır paketler Linux ve Windows x64/ARM64 içindir; Linux ARM64 için CPU/Vulkan, Windows ARM64 için CPU/Vulkan ve uygun NVIDIA donanımında CUDA seçeneği bulunur.

**2 Kasım 2026 kontrolü:** Windows paketlerinin tam adları, byte boyutları ve SHA-256 özetleri resmi [GitHub release API'sinden](https://api.github.com/repos/ggml-org/llama.cpp/releases/tags/b11412) doğrulandı. Windows x64 CUDA 12.4, ARM64 CUDA 13.4 paketi ve eşleşen cudart arşivi sabitlenmiştir; mevcut Linux sürümü değiştirilmedi. Windows ZIP kurulumu yalnızca sunucu `.exe` ve gerekli `.dll` dosyalarını özel geçici klasöre çıkarır. Dışarı yönelen yollar, bağlantılar, yinelenen adlar ve boyut sınırı aşımı reddedilir. İki arşiv doğrulanıp motor `--version` kontrolünden geçmeden kurulum yayınlanmaz. ZIP güvenlik ve kurulum testlerine ek olarak resmi 19.390.552 byte Windows x64 CPU paketi gerçek SHA-256 ile doğrulandı. Wine içindeki Windows Python ile geçici klasöre gerçek kurulum, 29 DLL ve `--version` kontrolü başarılı: build 11412 / commit c173a53bd. Büyük GPU paketleri indirilmedi; fiziksel Windows donanımında GPU çıkarımı sınanmadı.

Özel bir motor derlemek isteyenler [resmi llama.cpp kaynak derleme rehberini](https://github.com/ggml-org/llama.cpp/blob/master/docs/build.md) izleyebilir; üretilen `llama-server`/`llama-server.exe` uygulamadaki **Dosya seç…** ile eklenir. Git, CMake, C++ derleyicisi ve seçilen backend'in geliştirme bağımlılıkları kaynak derlemesine aittir. Uygulamadaki SHA-256 doğrulamalı hazır motor kurulumu CMake veya CUDA toolkit istemez; uygun GPU sürücüsü yine gerekir. Kayriva uygulamasını paketlemek ve başlatmak için proje kökündeki tek `kayriva.sh` kullanılır.

## GGUF desteği

Model mimarisi upstream tarafından desteklendiği sürece IQ1/IQ2, Q2, Q3, Q4, Q5, Q6, Q8, FP16/BF16 gibi motorun tanıdığı GGUF kuantizasyonları çalıştırılabilir. "Bütün modeller/veri türleri her cihazda desteklenir" garantisi verilmez. Kuantizasyon ailesi ve GPU kernel desteği mimariye/backend’e göre değişir. Kuantize modelin ağırlık türüyle KV cache türü ayrı ayarlardır.

CPU: GPU’ya 0 katman. Hibrit: seçtiğin sayıda katman GPU’da, kalan ağırlıklar RAM’de. GPU: tüm katmanların aktarımı denenir; bellek yetmezse motor hata verebilir. Bellek hatasında katman veya bağlam sayısını azalt. Model diskten memory-map edilir; dosya boyutu toplam VRAM/RAM gereksinimi değildir. GPU + RAM varsayılandır. Otomatik katman seçimi, model için RAM/VRAM kullanım bütçeleri ve yükleme öncesi tahmini bellek kontrolü vardır. Güncel motor otomatik GPU paylaşımında `--fit-target` kullanır. Bunlar işletim sistemi seviyesinde kesin bellek kotaları değildir.

## İsteğe bağlı Safetensors motoru

Python 3.11/3.12 ile ayrı ortam önerilir; PyTorch wheel desteği Python sürümüne bağlıdır:

```bash
python3.11 -m venv .venv
.venv/bin/python -m pip install -e '.[transformers]'
```

Bu komut bağımlılıkları internetten indirir. Ayarlar’dan Transformers’ı seç, CPU, GPU veya GPU + RAM modunu kaydet; ardından `config.json`, tokenizer ve ağırlıkları içeren **yerel model klasörünü** seç. Yükleyici `local_files_only=True`, `trust_remote_code=False` kullanır. Model çalışırken internetten kod veya ağırlık indirilmez.

FP32/FP16/BF16 ve CUDA’da bitsandbytes INT8/NF4 yolu hazırlandı. Önceden GPTQ/AWQ ile kuantize edilmiş checkpoint’ler ayrıca uyumlu quantizer paketi ister; otomatik kurulum yok. Bu isteğe bağlı backend bu ortamda PyTorch/Transformers kurulmadığı için gerçek modelle test edilmedi. Yalnızca metin üretimi desteklenir; MCP araçları ve elle katman sayısı ayarı için GGUF kullan. Transformers hibrit yolu Accelerate device_map=auto ile RAM/GPU bütçelerini max_memory üzerinden uygular; CUDA yoksa CPU kullanır. Bu yolun doğru yükleyici ayarları taklit PyTorch ile test edildi; gerçek çıkarım kanıtı değildir. Yeni modeller güncel Transformers isteyebilir.

## Model indirme

Uygulama içindeki İndir düğmesi Hugging Face API’sinden boyut/SHA-256 bilgisini doğrular, indirmeyi bir commit’e sabitler ve `.part` dosyasından devam eder. SHA-256 ve GGUF başlığı doğrulanmadan dosya kullanılabilir modele dönüştürülmez. Kısmi indirme başarısızlıkta korunur; bozuk tamamlanmış indirme silinir. Katalog boyutları doğrulanmış baytlardan ondalık GB'ye yuvarlanır; gerçek boyut indirmede tekrar alınır. Kullanıcı sohbeti veya dosyaları bu isteklere eklenmez. Kayıp eski commit ve harf/alt klasör değişiklikleri aynı dosya kimliği korunarak yeniden çözülür; farklı kuantizasyon sessizce seçilmez. [Katalog ve yerel model ekleme ayrıntıları](../docs/model-catalog-research.md).


## Uygulamadan kurulum

Genel → Yerel motor listesinden CPU, Vulkan veya NVIDIA CUDA seçip **Kur** düğmesine bas. Hazır resmi paketler SHA-256 ile doğrulanır; `engine/bin/cpu/`, `engine/bin/vulkan/` ve `engine/bin/cuda/` içinde saklanır. Özel motor için listenin sonundaki **Dosya seç…** kullanılır. İşletim sistemi ve işlemci mimarisine göre sunulan paketlerin sürüm/özet bilgileri `releases.json` içindedir. [Resmi sürüm](https://github.com/ggml-org/llama.cpp/releases/tag/b11412).


Motor bir sohbet yuvası kullanır (`--parallel 1`). GGUF’de sınırsız bağlam tüm model kapasitesini baştan ayırmaz: mesajlar, araç şemaları ve yanıt payına göre küçük başlar, gerektiğinde büyür. Açık sayısal kapasite sabittir. Aynı yükleme ayarlarıyla yeterli çalışma bağlamı hazırsa süreç ve prompt cache yeniden kullanılır. Büyük bağlama geçişte bellek yeniden kontrol edilir; yetersiz bütçe aşılmaz. RAM/VRAM seçicileri modelin kullanabileceği miktarın üst sınırıdır; yükseltmek modele daha fazla alan sağlar. Bellek önceden ayrılmaz. Otomatik modda sistem için boş pay bırakılır. Her durumda anlık boş bellek üst sınırdır; VRAM bütçesi motorun GPU yerleşimine aktarılır.

CUDA hazır paketine eşleşen cudart kitaplıkları da resmi sürümden alınır; iki arşiv boyut ve SHA-256 doğrulamasından geçmeden kurulum yayımlanmaz. Toolkit hazır paket çalıştırmak için gerekmez, NVIDIA sürücüsü gerekir. Bu klasörde CUDA ile Qwen3.5 4B tam GPU üretimi ve akış durdurma doğrulandı.
