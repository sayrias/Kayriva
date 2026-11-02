# Model kataloğu araştırması ve indirme dayanıklılığı

Kontrol tarihi: **2 Kasım 2026**. Bu belge katalog bakımının kapsamını ve sınırlarını kaydeder.

## Doğrulanan durum

Önceki 23 kaydın tamamının deposu ve tam GGUF dosya adı Hugging Face model API'sinde bulundu. Silinmiş bir eski katalog bağlantısı bu kontrolde doğrulanmadı. Bu nedenle kullanıcıya yaşadığı sorunun kesin olarak “silinmiş link” olduğu söylenmez. Ağ/proxy/TLS kesintisi, eski devam manifesti, seçici filtresi veya dosyanın henüz tamamen indirilmemiş olması ayrı olasılıklardır.

Katalog **141 sürüm, 71 model ailesi, 18 marka** içeriyor. Önceki 51 kayıt korunarak 32 yeni aileden 90 sürüm eklendi; NVIDIA için 12 aile ve 32 sürüm bulunuyor. Bütün kayıtların dosya bayt boyutu, LFS SHA-256 değeri ve depo commit kimliği API yanıtından alındı; boyutlar tahmin değildir. Bu, modelin cihazda çalışmasının veya araç/görsel kalitesinin ölçüldüğü anlamına gelmez. Model ağırlıkları indirilmedi. Kullanıcının mevcut dosyaları değiştirilmedi.

## Bir bağlantının ömür boyu bozulmaması mümkün mü?

Yayıncı depoyu silebilir, erişimi sınırlayabilir veya aynı dosyayı kaldırabilir. Bunu uygulama garanti edemez. Kullanılan yaklaşım sabit, süresi dolan CDN bağlantısını saklamak yerine `repo + istenen revision + remote_filename` kimliğini saklar:

1. Kütüphane yenilemesi her depo/sürüm için dosya listesini bir kez alır, çalışma başına en fazla dört isteği eşzamanlı yürütür. Yalnızca yayıncı metadata'sı sorgulanır.
2. Büyük/küçük harf farkı ve aynı dosyanın yeni alt klasöre taşınması, sadece tek ve aynı dosya kimliği çözülebiliyorsa düzeltilir. Birden fazla eşleşme veya kayıp kuantizasyon otomatik olarak başka bir modelle değiştirilmez.
3. `main`, indirme başlangıcında değişmez commit kimliğine çözülür. Ağırlıklar bu commit üzerinden alınır; SHA-256 ve GGUF başlığı doğrulanmadan yayınlanmaz.
4. Kesintide kısmi dosya ve doğrulama manifesti korunur. Kaydedilen eski commit 404 verirse kimlik yeniden çözülür. İçerik özeti veya boyut değiştiyse eski kısmi baytlar yeni dosyayla karıştırılmaz.
5. Önceden doğrulanmış dosya yerel metadata'sıyla çevrimdışı yeniden doğrulanabilir. Sunucuya ulaşılamaması, yüklü modeli kaldırmaz.
6. Güncel metadata `runtime/catalog-cache.json` dosyasına atomik yazılır. Ağ hatasında son bilinen boyut/commit korunur; “ulaşılamadı” ile “bulunamadı/erişim gerekiyor” ayrıdır. Sistem proxy/sertifika ayarları desteklenir.

Bu davranış [HF model_info metadata sözleşmesi](https://github.com/huggingface/huggingface_hub/blob/main/src/huggingface_hub/hf_api.py) ve [değişmez commit / cache açıklaması](https://huggingface.co/docs/huggingface_hub/guides/manage-cache) ile uyumludur. Yeni bir uzak modelin yetenek etiketi veya komutu kendiliğinden güvenilir hale getirilmez; küratörlü kimlikler korunur.

## Seçim ve donanım beklentisi

- **Hafif kod ve günlük çalışma:** Qwen3.5 2B/4B, Qwen2.5 Coder 1.5B/3B/7B; alternatif Phi 4 Mini. Küçük dosya tek başına kod kalitesi veya Türkçe yeterliliği garantisi değildir.
- **Daha uzun akıl yürütme:** Qwen3 4B/8B veya DeepSeek R1 0528 8B. Düşünme süresi ve bağlam büyüdükçe KV cache de büyüyebilir.
- **Daha yüksek bellekli kod ajanı:** Qwen3 Coder 30B-A3B, GLM 4.7 Flash, Qwen3.5 35B-A3B. MoE etkin parametre sayısı toplam ağırlık belleğini ortadan kaldırmaz; 3B etkin parametre “3B dosya” demek değildir.
- **Görsel inceleme:** Qwen2.5 VL 3B/7B, Qwen3.5 ailesi, Gemma 3 4B/12B/27B, Mistral Small 3.1. GGUF görsel çalışması için doğru aileye ait `mmproj` dosyası ve uyumlu motor ayrıca gerekir. Her kayıtta benzersiz yerel projektör adı ve gerçek uzak dosya kimliği bulunur; farklı modellerin genel `mmproj-F16.gguf` dosyaları birbirinin üstüne yazılmaz.
- **En küçük sistemler:** SmolLM2 1.7B, Llama 3.2 1B, Qwen3.5 0.8B. Çok küçük modeller, karmaşık araç zincirleri ve derin kod değişikliklerinde büyük modellerle aynı güvenilirliği vaat etmez.

`tier` (düşük/orta/yüksek/çok yüksek/ultra) **yaklaşık dosya boyutu ve donanım gereksinimi filtresidir**, kıyaslama kalite puanı değildir. Sınırlar sırasıyla 2, 5, 10 ve 20 ondalık GB'dır. Model ağırlıklarının üstüne bağlam, KV cache, motor tamponları, görsel projektör ve işletim sistemi belleği gerekir. `web` modeli tek başına internete bağlayan bir nitelik değildir; arama ve dosya işlemleri uygulamanın araçlarıdır.

Asıl model kartları: [Qwen3.5](https://huggingface.co/Qwen/Qwen3.5-4B), [Qwen3 Coder](https://huggingface.co/Qwen/Qwen3-Coder-30B-A3B-Instruct), [DeepSeek R1](https://huggingface.co/deepseek-ai/DeepSeek-R1-0528-Qwen3-8B), [Phi 4 Mini](https://huggingface.co/microsoft/Phi-4-mini-instruct), [Gemma 3](https://huggingface.co/google/gemma-3-4b-it), [Llama 3.2](https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct), [SmolLM2](https://huggingface.co/HuggingFaceTB/SmolLM2-1.7B-Instruct), [Mistral Small](https://huggingface.co/mistralai/Mistral-Small-3.1-24B-Instruct-2503), [gpt-oss](https://huggingface.co/openai/gpt-oss-20b), [GLM](https://huggingface.co/zai-org/GLM-4.7-Flash). Lisanslar aynı değildir; Gemma, Llama Community ve Qwen Research koşulları Apache/MIT sayılmaz.

## NVIDIA ve yeni ailelerin seçimi

NVIDIA adı bir GPU şartı değildir: bunlar NVIDIA tarafından yayımlanan model aileleridir. Uyumlu GGUF motoru ile CPU, CUDA veya desteklenen diğer GPU arka uçlarında çalışabilirler; gerçek hız ve desteklenen işlemler cihazın arka ucuna bağlıdır. CUDA kullanmak için NVIDIA kartı gerekir.

- **Küçük bellek:** OpenReasoning Nemotron 1.5B, Nemotron Mini 4B ve Nemotron 3 Nano 4B. İlk ikisi sırasıyla kod/akıl yürütme ve araç kullanımı için farklı seçeneklerdir. Nano 4B hibrit Mamba-Transformer mimarisidir; dosya boyutu parametre etiketi üzerinden tahmin edilmedi.
- **Orta sistem:** OpenReasoning 7B, Llama Nemotron Nano 8B ve Nemotron Nano 9B v2. İngilizce/kod odağı Türkçe kalite garantisi değildir.
- **Daha yüksek bellek:** AceReason 14B, OpenReasoning 14B/32B, Nemotron 3 Nano 30B-A3B ve Super 49B v1/v1.5. MoE modelinde etkin parametre sayısı toplam ağırlık belleği sayılmaz. Super 49B sürümleri küçük GPU için başlangıç önerisi değildir.
- **Diğer üreticiler:** IBM Granite 3.2, Liquid LFM2, Cohere Aya Expanse, Allen AI OLMo 2, OpenBMB MiniCPM 4, InternLM 2.5, 01.AI Yi/Yi Coder, Mistral Devstral, Hugging Face SmolLM3 ve ByteDance Seed OSS eklendi. Q4_K_M, Q5_K_M ve varsa tek parçalı Q8_0 seçenekleri farklı dosya/bellek bütçeleri sunar.

Yeni kayıtlar için Hugging Face `api/models/{repo}?blobs=true` yanıtındaki gerçek GGUF mimari anahtarı, paketlenen [llama.cpp b11412 mimari kaydı](https://github.com/ggml-org/llama.cpp/blob/b11412/src/llama-arch.cpp) ile karşılaştırıldı: `llama`, `qwen2`, `nemotron`, `nemotron_h`, `nemotron_h_moe`, `deci`, `granite`, `lfm2`, `command-r`, `olmo2`, `minicpm`, `internlm2`, `smollm3`, `seed_oss`. Mimari kaydında bulunmak, her kuantizasyonun her GPU arka ucunda sorunsuz çalıştığı anlamına gelmez. Büyük ağırlıklar indirilmedi; katalog metadata doğrulaması çıkarım kıyaslaması değildir.

Her yeni sürüm indiricinin tek hedef dosya sözleşmesine uyması için **tek parçalı** GGUF olarak seçildi. Parçalı Q8/BF16 dosyaları kataloğa ilk parça şeklinde eklenmedi. Platformlar arası büyük/küçük harf duyarsız yerel dosya adı çakışmaları kontrol edildi. Özel HIP yeniden paketleri taşınabilir standart kuantizasyonlarla karıştırılmadı. Görsel/ses/embedding veya ayrı MCP sürümünün yetenekleri metin modeline aktarılmadı.

Lisans bilgisi asıl model kartına bağlanır: NVIDIA Open/Nemotron/Community koşulları aileye göre değişir, OpenReasoning CC BY 4.0, Aya Expanse CC BY-NC 4.0, Liquid LFM Open License 1.0, InternLM özel ağırlık lisansı kullanır. Bunların hepsi Apache 2.0 olarak sunulmaz. Aya'nın asıl ağırlık deposu erişim onayı isteyebilir; doğrulanan topluluk GGUF deposunun erişimi ve dosyaları ayrı kontrol edildi. Ticari kullanımda ilgili kartın güncel koşulları izlenmelidir.

Asıl yayıncı örnekleri: [NVIDIA Nano 4B](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-BF16), [NVIDIA OpenReasoning 1.5B](https://huggingface.co/nvidia/OpenReasoning-Nemotron-1.5B), [NVIDIA Mini](https://huggingface.co/nvidia/Nemotron-Mini-4B-Instruct), [IBM Granite](https://huggingface.co/ibm-granite/granite-3.2-2b-instruct), [Liquid LFM2 Tool](https://huggingface.co/LiquidAI/LFM2-1.2B-Tool), [Aya Expanse](https://huggingface.co/CohereForAI/aya-expanse-8b), [OLMo 2](https://huggingface.co/allenai/OLMo-2-1124-7B-Instruct), [MiniCPM 4](https://huggingface.co/openbmb/MiniCPM4-8B), [InternLM 2.5](https://huggingface.co/internlm/internlm2_5-1_8b-chat), [Yi Coder](https://huggingface.co/01-ai/Yi-Coder-1.5B-Chat), [Devstral](https://huggingface.co/mistralai/Devstral-Small-2507), [SmolLM3](https://huggingface.co/HuggingFaceTB/SmolLM3-3B), [Seed OSS](https://huggingface.co/ByteDance-Seed/Seed-OSS-36B-Instruct).

### Marka kapsamı

| Üretici | Model ailesi | Sürüm |
| --- | ---: | ---: |
| 01.AI | 3 | 9 |
| Allen AI | 2 | 6 |
| ByteDance | 1 | 3 |
| Cohere | 2 | 6 |
| DeepSeek | 3 | 3 |
| Google | 3 | 4 |
| Hugging Face | 2 | 4 |
| IBM | 2 | 6 |
| InternLM | 2 | 6 |
| Liquid AI | 5 | 15 |
| Meta | 2 | 2 |
| Microsoft | 1 | 1 |
| Mistral | 2 | 4 |
| NVIDIA | 12 | 32 |
| OpenAI | 1 | 1 |
| OpenBMB | 1 | 1 |
| Qwen | 26 | 37 |
| Z.ai | 1 | 1 |

## Doğrulanmış dosyalar

Baytlar yayıncının metadata yanıtındaki kesin boyuttur; tabloda ondalık GB'ye yuvarlandı. Ayrıntılı SHA-256 ve commit kimlikleri `models/catalog.json` içindedir.

| Model | Kuantizasyon | Boyut (GB) | Yayıncı dosyası |
| --- | --- | ---: | --- |
| Qwen3.5 · 9B | IQ4_XS | 5.169 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/blob/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-IQ4_XS.gguf) |
| Qwen3.8 · 27B | UD-IQ2_S | 8.372 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/blob/4ca720788d1e01f1bff70c033e0d0028fd02e502/Qwen3.8-27B-UD-IQ2_S.gguf) |
| Qwen3.8 · 27B | UD-IQ3_XXS | 10.935 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/blob/4ca720788d1e01f1bff70c033e0d0028fd02e502/Qwen3.8-27B-UD-IQ3_XXS.gguf) |
| Qwen3.5 · 27B | UD-IQ2_XXS | 8.574 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-27B-GGUF/blob/3221f178a6b842d04f1fb42f1c413534adcc0a6a/Qwen3.5-27B-UD-IQ2_XXS.gguf) |
| Qwen3.5 · 27B | Q4_K_M | 16.741 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-27B-GGUF/blob/3221f178a6b842d04f1fb42f1c413534adcc0a6a/Qwen3.5-27B-Q4_K_M.gguf) |
| Qwen3.5 · 4B | Q4_K_M | 2.741 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-4B-GGUF/blob/e87f176479d0855a907a41277aca2f8ee7a09523/Qwen3.5-4B-Q4_K_M.gguf) |
| Qwen3.5 · 9B Uncensored | Q4_K_M | 5.627 | [Doğrulanan dosya](https://huggingface.co/HauhauCS/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive/blob/0a41c68809d375475f954be12ba7c40efa56c2a9/Qwen3.5-9B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf) |
| Qwen3.5 · 4B Uncensored | Q4_K_M | 2.708 | [Doğrulanan dosya](https://huggingface.co/HauhauCS/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive/blob/c09cdbcdb1fefad6d335809d445621b5f5ba0c6e/Qwen3.5-4B-Uncensored-HauhauCS-Aggressive-Q4_K_M.gguf) |
| Qwen3 · 8B Jailbroken | Q4_K_M | 5.028 | [Doğrulanan dosya](https://huggingface.co/mradermacher/Qwen3-8B-Jailbroken-GGUF/blob/121226819fd3136c582334659ea0571187e67147/Qwen3-8B-Jailbroken.Q4_K_M.gguf) |
| Qwen3 · 8B Jailbroken | IQ2_M | 3.052 | [Doğrulanan dosya](https://huggingface.co/mradermacher/Qwen3-8B-Jailbroken-i1-GGUF/blob/b759f5bb75d857c904902d0aae3cd8bd2accf74b/Qwen3-8B-Jailbroken.i1-IQ2_M.gguf) |
| Qwen3.8 · 27B Uncensored | IQ2_M | 10.173 | [Doğrulanan dosya](https://huggingface.co/JonathanColetti/Qwen3.8-27B-Uncensored-GGUF/blob/45d0fc0ad6cfcf9eeee6008ddaea925536409b18/Qwen3.8-27B-Uncensored-noMTP-IQ2_M.gguf) |
| Qwen3.8 · 27B Uncensored | Q4_K_M | 16.547 | [Doğrulanan dosya](https://huggingface.co/JonathanColetti/Qwen3.8-27B-Uncensored-GGUF/blob/45d0fc0ad6cfcf9eeee6008ddaea925536409b18/Qwen3.8-27B-Uncensored-noMTP-Q4_K_M.gguf) |
| Qwen3.8 · 27B | UD-IQ2_XXS | 7.266 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/blob/4ca720788d1e01f1bff70c033e0d0028fd02e502/Qwen3.8-27B-UD-IQ2_XXS.gguf) |
| Qwen3.8 · 27B | UD-IQ1_M | 6.729 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/blob/4ca720788d1e01f1bff70c033e0d0028fd02e502/Qwen3.8-27B-UD-IQ1_M.gguf) |
| Qwen3.8 · 27B | UD-IQ1_S | 6.192 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.8-27B-GGUF/blob/4ca720788d1e01f1bff70c033e0d0028fd02e502/Qwen3.8-27B-UD-IQ1_S.gguf) |
| Qwen3.5 · 9B | Q3_K_M | 4.674 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/blob/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q3_K_M.gguf) |
| Qwen3.5 · 9B | Q4_K_M | 5.681 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/blob/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q4_K_M.gguf) |
| Qwen3.5 · 9B | Q8_0 | 9.528 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-9B-GGUF/blob/3885219b6810b007914f3a7950a8d1b469d598a5/Qwen3.5-9B-Q8_0.gguf) |
| Gemma 3 · 27B | UD-IQ2_XXS | 7.850 | [Doğrulanan dosya](https://huggingface.co/unsloth/gemma-3-27b-it-GGUF/blob/7cd0121f2530b00e42c4df952d4cad4418c0b3c1/gemma-3-27b-it-UD-IQ2_XXS.gguf) |
| Gemma 3 · 27B | UD-IQ3_XXS | 10.810 | [Doğrulanan dosya](https://huggingface.co/unsloth/gemma-3-27b-it-GGUF/blob/7cd0121f2530b00e42c4df952d4cad4418c0b3c1/gemma-3-27b-it-UD-IQ3_XXS.gguf) |
| Gemma 3 · 4B | Q4_K_M | 2.490 | [Doğrulanan dosya](https://huggingface.co/unsloth/gemma-3-4b-it-GGUF/blob/5a3566e716d80f709ed7b79817eaf7733d2a1fce/gemma-3-4b-it-Q4_K_M.gguf) |
| Gemma 3 · 12B | Q4_K_M | 7.301 | [Doğrulanan dosya](https://huggingface.co/unsloth/gemma-3-12b-it-GGUF/blob/d15e4c7dc21dc55d56bf8549db57a71ad8a2a35d/gemma-3-12b-it-Q4_K_M.gguf) |
| Qwen2.5 Coder · 7B | Q4_K_M | 4.683 | [Doğrulanan dosya](https://huggingface.co/bartowski/Qwen2.5-Coder-7B-Instruct-GGUF/blob/1f629da0c8bed16b9e50cee91c70693650e66c35/Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf) |
| Qwen2.5 Coder · 0.5B | q4_k_m | 0.491 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen2.5-Coder-0.5B-Instruct-GGUF/blob/ebb2015119c907b064c512bf053e945850b5875f/qwen2.5-coder-0.5b-instruct-q4_k_m.gguf) |
| Qwen2.5 Coder · 1.5B | q4_k_m | 1.117 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen2.5-Coder-1.5B-Instruct-GGUF/blob/f86cb2c1fa58255f8052cc32aeede1b7482d4361/qwen2.5-coder-1.5b-instruct-q4_k_m.gguf) |
| Qwen2.5 Coder · 3B | q4_k_m | 2.105 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen2.5-Coder-3B-Instruct-GGUF/blob/f74adce6aa16316c625447af059dbebe4983757c/qwen2.5-coder-3b-instruct-q4_k_m.gguf) |
| Qwen2.5 Coder · 14B | q4_k_m | 8.988 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen2.5-Coder-14B-Instruct-GGUF/blob/d0a692ef765eefbf2fabb130b3cb2e8917e3d225/qwen2.5-coder-14b-instruct-q4_k_m.gguf) |
| Qwen2.5 Coder · 32B | q4_k_m | 19.851 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen2.5-Coder-32B-Instruct-GGUF/blob/9d3053fce650fe1cdbdb75998c2a87add9d178ef/qwen2.5-coder-32b-instruct-q4_k_m.gguf) |
| Qwen3 · 0.6B | Q8_0 | 0.639 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen3-0.6B-GGUF/blob/23749fefcc72300e3a2ad315e1317431b06b590a/Qwen3-0.6B-Q8_0.gguf) |
| Qwen3 · 1.7B | Q8_0 | 1.834 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen3-1.7B-GGUF/blob/90862c4b9d2787eaed51d12237eafdfe7c5f6077/Qwen3-1.7B-Q8_0.gguf) |
| Qwen3 · 4B | Q4_K_M | 2.497 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen3-4B-GGUF/blob/bc640142c66e1fdd12af0bd68f40445458f3869b/Qwen3-4B-Q4_K_M.gguf) |
| Qwen3 · 8B | Q4_K_M | 5.028 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen3-8B-GGUF/blob/7c41481f57cb95916b40956ab2f0b139b296d974/Qwen3-8B-Q4_K_M.gguf) |
| Qwen3 · 14B | Q4_K_M | 9.002 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen3-14B-GGUF/blob/530227a7d994db8eca5ab5ced2fb692b614357fd/Qwen3-14B-Q4_K_M.gguf) |
| Qwen3 · 32B | Q4_K_M | 19.762 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen3-32B-GGUF/blob/938a7432affaec9157f883a87164e2646ae17555/Qwen3-32B-Q4_K_M.gguf) |
| Qwen3 · 32B | Q8_0 | 34.818 | [Doğrulanan dosya](https://huggingface.co/Qwen/Qwen3-32B-GGUF/blob/938a7432affaec9157f883a87164e2646ae17555/Qwen3-32B-Q8_0.gguf) |
| Qwen3.5 · 0.8B | Q4_K_M | 0.533 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-0.8B-GGUF/blob/6ab461498e2023f6e3c1baea90a8f0fe38ab64d0/Qwen3.5-0.8B-Q4_K_M.gguf) |
| Qwen3.5 · 2B | Q4_K_M | 1.281 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-2B-GGUF/blob/f6d5376be1edb4d416d56da11e5397a961aca8ae/Qwen3.5-2B-Q4_K_M.gguf) |
| Qwen3.5 · 35B-A3B | Q4_K_M | 22.016 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3.5-35B-A3B-GGUF/blob/bc014a17be43adabd7066b7a86075ff935c6a4e2/Qwen3.5-35B-A3B-Q4_K_M.gguf) |
| Qwen3 Coder · 30B-A3B | Q4_K_M | 18.557 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF/blob/b17cb02dd882d5b6ab62fc777ad2995f19668350/Qwen3-Coder-30B-A3B-Instruct-Q4_K_M.gguf) |
| DeepSeek R1 Distill · 7B | Q4_K_M | 4.683 | [Doğrulanan dosya](https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-7B-GGUF/blob/097680e4eed7a83b3df6b0bb5e5134099cadf1b0/DeepSeek-R1-Distill-Qwen-7B-Q4_K_M.gguf) |
| DeepSeek R1 Distill · 14B | Q4_K_M | 8.988 | [Doğrulanan dosya](https://huggingface.co/unsloth/DeepSeek-R1-Distill-Qwen-14B-GGUF/blob/7b05b58b41f623e66fc74cd27b35475267b2f3e3/DeepSeek-R1-Distill-Qwen-14B-Q4_K_M.gguf) |
| DeepSeek R1 0528 · 8B | Q4_K_M | 5.028 | [Doğrulanan dosya](https://huggingface.co/unsloth/DeepSeek-R1-0528-Qwen3-8B-GGUF/blob/eb48357c179d34dbf515983f798dfb8752a0f261/DeepSeek-R1-0528-Qwen3-8B-Q4_K_M.gguf) |
| Phi 4 Mini · 3.8B | Q4_K_M | 2.492 | [Doğrulanan dosya](https://huggingface.co/bartowski/microsoft_Phi-4-mini-instruct-GGUF/blob/7ff82c2aaa4dde30121698a973765f39be5288c0/microsoft_Phi-4-mini-instruct-Q4_K_M.gguf) |
| SmolLM2 · 1.7B | Q4_K_M | 1.056 | [Doğrulanan dosya](https://huggingface.co/bartowski/SmolLM2-1.7B-Instruct-GGUF/blob/1f03464768bfcc0319fc50da8ff5fb20b6417ba2/SmolLM2-1.7B-Instruct-Q4_K_M.gguf) |
| Llama 3.2 · 1B | Q4_K_M | 0.808 | [Doğrulanan dosya](https://huggingface.co/unsloth/Llama-3.2-1B-Instruct-GGUF/blob/b69aef112e9f895e6f98d7ae0949f72ff09aa401/Llama-3.2-1B-Instruct-Q4_K_M.gguf) |
| Llama 3.2 · 3B | Q4_K_M | 2.019 | [Doğrulanan dosya](https://huggingface.co/unsloth/Llama-3.2-3B-Instruct-GGUF/blob/e7d0997e49c9cb00d88b4c1a6a16aa894b0bbc31/Llama-3.2-3B-Instruct-Q4_K_M.gguf) |
| Qwen2.5 VL · 3B | Q4_K_M | 1.930 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen2.5-VL-3B-Instruct-GGUF/blob/20ce64893974f3faa729fe3dbdd70f8cabc2523c/Qwen2.5-VL-3B-Instruct-Q4_K_M.gguf) |
| Qwen2.5 VL · 7B | Q4_K_M | 4.683 | [Doğrulanan dosya](https://huggingface.co/unsloth/Qwen2.5-VL-7B-Instruct-GGUF/blob/68bb8bc4b7df5289c143aaec0ab477a7d4051aab/Qwen2.5-VL-7B-Instruct-Q4_K_M.gguf) |
| Mistral Small 3.1 · 24B | Q4_K_M | 14.334 | [Doğrulanan dosya](https://huggingface.co/unsloth/Mistral-Small-3.1-24B-Instruct-2503-GGUF/blob/d63ca9416f5db4f54a78145fb9a025317a57289f/Mistral-Small-3.1-24B-Instruct-2503-Q4_K_M.gguf) |
| gpt-oss · 20B | Q4_K_M | 11.625 | [Doğrulanan dosya](https://huggingface.co/unsloth/gpt-oss-20b-GGUF/blob/d449b42d93e1c2c7bda5312f5c25c8fb91dfa9b4/gpt-oss-20b-Q4_K_M.gguf) |
| GLM 4.7 Flash · 30B-A3B | Q4_K_M | 18.312 | [Doğrulanan dosya](https://huggingface.co/unsloth/GLM-4.7-Flash-GGUF/blob/0d32489ecb9db6d2a4fc93bd27ef01519f95474d/GLM-4.7-Flash-Q4_K_M.gguf) |
| OpenReasoning Nemotron · 1.5B | Q4_K_M | 0.986 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-1.5B-GGUF/blob/9b6c802caafdc99c2924ddb374c5a5995f0bb2f1/nvidia_OpenReasoning-Nemotron-1.5B-Q4_K_M.gguf) |
| OpenReasoning Nemotron · 1.5B | Q5_K_M | 1.125 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-1.5B-GGUF/blob/9b6c802caafdc99c2924ddb374c5a5995f0bb2f1/nvidia_OpenReasoning-Nemotron-1.5B-Q5_K_M.gguf) |
| OpenReasoning Nemotron · 1.5B | Q8_0 | 1.647 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-1.5B-GGUF/blob/9b6c802caafdc99c2924ddb374c5a5995f0bb2f1/nvidia_OpenReasoning-Nemotron-1.5B-Q8_0.gguf) |
| OpenReasoning Nemotron · 7B | Q4_K_M | 4.683 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-7B-GGUF/blob/fdb4acbdfddbd5a52a010e1909007e75d75c637f/nvidia_OpenReasoning-Nemotron-7B-Q4_K_M.gguf) |
| OpenReasoning Nemotron · 7B | Q5_K_M | 5.445 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-7B-GGUF/blob/fdb4acbdfddbd5a52a010e1909007e75d75c637f/nvidia_OpenReasoning-Nemotron-7B-Q5_K_M.gguf) |
| OpenReasoning Nemotron · 7B | Q8_0 | 8.099 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-7B-GGUF/blob/fdb4acbdfddbd5a52a010e1909007e75d75c637f/nvidia_OpenReasoning-Nemotron-7B-Q8_0.gguf) |
| OpenReasoning Nemotron · 14B | Q4_K_M | 8.988 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-14B-GGUF/blob/00e97b904f1fec95bc9ab33c8f5b9af4f455ef19/nvidia_OpenReasoning-Nemotron-14B-Q4_K_M.gguf) |
| OpenReasoning Nemotron · 14B | Q5_K_M | 10.509 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-14B-GGUF/blob/00e97b904f1fec95bc9ab33c8f5b9af4f455ef19/nvidia_OpenReasoning-Nemotron-14B-Q5_K_M.gguf) |
| OpenReasoning Nemotron · 14B | Q8_0 | 15.702 | [Doğrulanan dosya](https://huggingface.co/bartowski/nvidia_OpenReasoning-Nemotron-14B-GGUF/blob/00e97b904f1fec95bc9ab33c8f5b9af4f455ef19/nvidia_OpenReasoning-Nemotron-14B-Q8_0.gguf) |
| Nemotron Nano v2 · 9B | Q4_K_M | 6.526 | [Doğrulanan dosya](https://huggingface.co/second-state/NVIDIA-Nemotron-Nano-9B-v2-GGUF/blob/6d856b6689a6d32ec38dd666344be42a203c6e23/NVIDIA-Nemotron-Nano-9B-v2-Q4_K_M.gguf) |
| Nemotron Nano v2 · 9B | Q5_K_M | 7.070 | [Doğrulanan dosya](https://huggingface.co/second-state/NVIDIA-Nemotron-Nano-9B-v2-GGUF/blob/6d856b6689a6d32ec38dd666344be42a203c6e23/NVIDIA-Nemotron-Nano-9B-v2-Q5_K_M.gguf) |
| Nemotron Nano v2 · 9B | Q8_0 | 9.458 | [Doğrulanan dosya](https://huggingface.co/second-state/NVIDIA-Nemotron-Nano-9B-v2-GGUF/blob/6d856b6689a6d32ec38dd666344be42a203c6e23/NVIDIA-Nemotron-Nano-9B-v2-Q8_0.gguf) |
| Nemotron 3 Nano · 30B-A3B | Q4_K_M | 24.574 | [Doğrulanan dosya](https://huggingface.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF/blob/9ad8b366c308f931b2a96b9306f0b41aef9cd405/Nemotron-3-Nano-30B-A3B-Q4_K_M.gguf) |
| Nemotron 3 Nano · 30B-A3B | Q5_K_M | 26.149 | [Doğrulanan dosya](https://huggingface.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF/blob/9ad8b366c308f931b2a96b9306f0b41aef9cd405/Nemotron-3-Nano-30B-A3B-Q5_K_M.gguf) |
| Nemotron 3 Nano · 30B-A3B | Q8_0 | 33.585 | [Doğrulanan dosya](https://huggingface.co/unsloth/Nemotron-3-Nano-30B-A3B-GGUF/blob/9ad8b366c308f931b2a96b9306f0b41aef9cd405/Nemotron-3-Nano-30B-A3B-Q8_0.gguf) |
| Llama Nemotron Nano v1 · 8B | Q4_K_M | 4.921 | [Doğrulanan dosya](https://huggingface.co/unsloth/Llama-3.1-Nemotron-Nano-8B-v1-GGUF/blob/d4b185dad118067300efd1b12498dad3a3358496/Llama-3.1-Nemotron-Nano-8B-v1-Q4_K_M.gguf) |
| Llama Nemotron Nano v1 · 8B | Q5_K_M | 5.733 | [Doğrulanan dosya](https://huggingface.co/unsloth/Llama-3.1-Nemotron-Nano-8B-v1-GGUF/blob/d4b185dad118067300efd1b12498dad3a3358496/Llama-3.1-Nemotron-Nano-8B-v1-Q5_K_M.gguf) |
| Llama Nemotron Super v1 · 49B | Q4_K_M | 30.216 | [Doğrulanan dosya](https://huggingface.co/unsloth/Llama-3_3-Nemotron-Super-49B-v1-GGUF/blob/6c679d12e88815cf6c66cf627b46ea66acfdeb4d/Llama-3_3-Nemotron-Super-49B-v1-Q4_K_M.gguf) |
| Llama Nemotron Super v1 · 49B | Q5_K_M | 35.392 | [Doğrulanan dosya](https://huggingface.co/unsloth/Llama-3_3-Nemotron-Super-49B-v1-GGUF/blob/6c679d12e88815cf6c66cf627b46ea66acfdeb4d/Llama-3_3-Nemotron-Super-49B-v1-Q5_K_M.gguf) |
| AceReason Nemotron · 14B | Q4_K_M | 8.988 | [Doğrulanan dosya](https://huggingface.co/unsloth/AceReason-Nemotron-14B-GGUF/blob/e18a69a3f24d2800b7eac2ee8dcda3db3e7375ba/AceReason-Nemotron-14B-Q4_K_M.gguf) |
| AceReason Nemotron · 14B | Q5_K_M | 10.509 | [Doğrulanan dosya](https://huggingface.co/unsloth/AceReason-Nemotron-14B-GGUF/blob/e18a69a3f24d2800b7eac2ee8dcda3db3e7375ba/AceReason-Nemotron-14B-Q5_K_M.gguf) |
| OpenReasoning Nemotron · 32B | Q4_K_M | 19.851 | [Doğrulanan dosya](https://huggingface.co/unsloth/OpenReasoning-Nemotron-32B-GGUF/blob/6584ca5c003218998246b11b02b7918fc446e175/OpenReasoning-Nemotron-32B-Q4_K_M.gguf) |
| OpenReasoning Nemotron · 32B | Q5_K_M | 23.262 | [Doğrulanan dosya](https://huggingface.co/unsloth/OpenReasoning-Nemotron-32B-GGUF/blob/6584ca5c003218998246b11b02b7918fc446e175/OpenReasoning-Nemotron-32B-Q5_K_M.gguf) |
| OpenReasoning Nemotron · 32B | Q8_0 | 34.821 | [Doğrulanan dosya](https://huggingface.co/unsloth/OpenReasoning-Nemotron-32B-GGUF/blob/6584ca5c003218998246b11b02b7918fc446e175/OpenReasoning-Nemotron-32B-Q8_0.gguf) |
| Llama Nemotron Super v1.5 · 49B | Q4_K_M | 30.216 | [Doğrulanan dosya](https://huggingface.co/unsloth/Llama-3_3-Nemotron-Super-49B-v1_5-GGUF/blob/cae8fb480126298d35cac575f77d68e3d4fc26a8/Llama-3_3-Nemotron-Super-49B-v1_5-Q4_K_M.gguf) |
| Llama Nemotron Super v1.5 · 49B | Q5_K_M | 35.392 | [Doğrulanan dosya](https://huggingface.co/unsloth/Llama-3_3-Nemotron-Super-49B-v1_5-GGUF/blob/cae8fb480126298d35cac575f77d68e3d4fc26a8/Llama-3_3-Nemotron-Super-49B-v1_5-Q5_K_M.gguf) |
| Nemotron 3 Nano · 4B | Q4_K_M | 2.900 | [Doğrulanan dosya](https://huggingface.co/unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF/blob/8e81be55c5aa3d63bb82b6ceec62d50805d9e1bb/NVIDIA-Nemotron-3-Nano-4B-Q4_K_M.gguf) |
| Nemotron 3 Nano · 4B | Q5_K_M | 3.160 | [Doğrulanan dosya](https://huggingface.co/unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF/blob/8e81be55c5aa3d63bb82b6ceec62d50805d9e1bb/NVIDIA-Nemotron-3-Nano-4B-Q5_K_M.gguf) |
| Nemotron 3 Nano · 4B | Q8_0 | 4.234 | [Doğrulanan dosya](https://huggingface.co/unsloth/NVIDIA-Nemotron-3-Nano-4B-GGUF/blob/8e81be55c5aa3d63bb82b6ceec62d50805d9e1bb/NVIDIA-Nemotron-3-Nano-4B-Q8_0.gguf) |
| Nemotron Mini · 4B | Q4_K_M | 2.697 | [Doğrulanan dosya](https://huggingface.co/bartowski/Nemotron-Mini-4B-Instruct-GGUF/blob/fb49cde090c86092d89905bea2ffc41c23c2615e/Nemotron-Mini-4B-Instruct-Q4_K_M.gguf) |
| Nemotron Mini · 4B | Q5_K_M | 3.060 | [Doğrulanan dosya](https://huggingface.co/bartowski/Nemotron-Mini-4B-Instruct-GGUF/blob/fb49cde090c86092d89905bea2ffc41c23c2615e/Nemotron-Mini-4B-Instruct-Q5_K_M.gguf) |
| Nemotron Mini · 4B | Q8_0 | 4.460 | [Doğrulanan dosya](https://huggingface.co/bartowski/Nemotron-Mini-4B-Instruct-GGUF/blob/fb49cde090c86092d89905bea2ffc41c23c2615e/Nemotron-Mini-4B-Instruct-Q8_0.gguf) |
| Granite 3.2 · 8B | Q4_K_M | 4.943 | [Doğrulanan dosya](https://huggingface.co/bartowski/ibm-granite_granite-3.2-8b-instruct-GGUF/blob/cee2771c00c6d6fa0cee25faeb68e55fcca0b387/ibm-granite_granite-3.2-8b-instruct-Q4_K_M.gguf) |
| Granite 3.2 · 8B | Q5_K_M | 5.797 | [Doğrulanan dosya](https://huggingface.co/bartowski/ibm-granite_granite-3.2-8b-instruct-GGUF/blob/cee2771c00c6d6fa0cee25faeb68e55fcca0b387/ibm-granite_granite-3.2-8b-instruct-Q5_K_M.gguf) |
| Granite 3.2 · 8B | Q8_0 | 8.684 | [Doğrulanan dosya](https://huggingface.co/bartowski/ibm-granite_granite-3.2-8b-instruct-GGUF/blob/cee2771c00c6d6fa0cee25faeb68e55fcca0b387/ibm-granite_granite-3.2-8b-instruct-Q8_0.gguf) |
| Granite 3.2 · 2B | Q4_K_M | 1.545 | [Doğrulanan dosya](https://huggingface.co/bartowski/ibm-granite_granite-3.2-2b-instruct-GGUF/blob/9be2c106c8c073f5a140ec03c8c7a6a6e72d097b/ibm-granite_granite-3.2-2b-instruct-Q4_K_M.gguf) |
| Granite 3.2 · 2B | Q5_K_M | 1.805 | [Doğrulanan dosya](https://huggingface.co/bartowski/ibm-granite_granite-3.2-2b-instruct-GGUF/blob/9be2c106c8c073f5a140ec03c8c7a6a6e72d097b/ibm-granite_granite-3.2-2b-instruct-Q5_K_M.gguf) |
| Granite 3.2 · 2B | Q8_0 | 2.694 | [Doğrulanan dosya](https://huggingface.co/bartowski/ibm-granite_granite-3.2-2b-instruct-GGUF/blob/9be2c106c8c073f5a140ec03c8c7a6a6e72d097b/ibm-granite_granite-3.2-2b-instruct-Q8_0.gguf) |
| LFM2 · 1.2B | Q4_K_M | 0.731 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-1.2B-GGUF/blob/5399e76c648f4eb8c053feb1ab747277dea5bf8b/LFM2-1.2B-Q4_K_M.gguf) |
| LFM2 · 1.2B | Q5_K_M | 0.843 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-1.2B-GGUF/blob/5399e76c648f4eb8c053feb1ab747277dea5bf8b/LFM2-1.2B-Q5_K_M.gguf) |
| LFM2 · 1.2B | Q8_0 | 1.246 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-1.2B-GGUF/blob/5399e76c648f4eb8c053feb1ab747277dea5bf8b/LFM2-1.2B-Q8_0.gguf) |
| LFM2 · 350M | Q4_K_M | 0.229 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-350M-GGUF/blob/8fdc9d526b7ed346b19257551b05816c7912ecc2/LFM2-350M-Q4_K_M.gguf) |
| LFM2 · 350M | Q5_K_M | 0.260 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-350M-GGUF/blob/8fdc9d526b7ed346b19257551b05816c7912ecc2/LFM2-350M-Q5_K_M.gguf) |
| LFM2 · 350M | Q8_0 | 0.379 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-350M-GGUF/blob/8fdc9d526b7ed346b19257551b05816c7912ecc2/LFM2-350M-Q8_0.gguf) |
| LFM2 · 700M | Q4_K_M | 0.469 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-700M-GGUF/blob/fd39e80d7a5ac61494ffff577e61bbbfddbd0d02/LFM2-700M-Q4_K_M.gguf) |
| LFM2 · 700M | Q5_K_M | 0.538 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-700M-GGUF/blob/fd39e80d7a5ac61494ffff577e61bbbfddbd0d02/LFM2-700M-Q5_K_M.gguf) |
| LFM2 · 700M | Q8_0 | 0.792 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-700M-GGUF/blob/fd39e80d7a5ac61494ffff577e61bbbfddbd0d02/LFM2-700M-Q8_0.gguf) |
| LFM2 · 2.6B | Q4_K_M | 1.564 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-2.6B-GGUF/blob/a759abdc5955d4ca97763e5cb7ff3940589ba898/LFM2-2.6B-Q4_K_M.gguf) |
| LFM2 · 2.6B | Q5_K_M | 1.829 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-2.6B-GGUF/blob/a759abdc5955d4ca97763e5cb7ff3940589ba898/LFM2-2.6B-Q5_K_M.gguf) |
| LFM2 · 2.6B | Q8_0 | 2.733 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-2.6B-GGUF/blob/a759abdc5955d4ca97763e5cb7ff3940589ba898/LFM2-2.6B-Q8_0.gguf) |
| LFM2 Tool · 1.2B | Q4_K_M | 0.731 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-1.2B-Tool-GGUF/blob/e7ec4149433c75d4bb53a0742ee1ebde7fcbd183/LFM2-1.2B-Tool-Q4_K_M.gguf) |
| LFM2 Tool · 1.2B | Q5_K_M | 0.843 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-1.2B-Tool-GGUF/blob/e7ec4149433c75d4bb53a0742ee1ebde7fcbd183/LFM2-1.2B-Tool-Q5_K_M.gguf) |
| LFM2 Tool · 1.2B | Q8_0 | 1.246 | [Doğrulanan dosya](https://huggingface.co/LiquidAI/LFM2-1.2B-Tool-GGUF/blob/e7ec4149433c75d4bb53a0742ee1ebde7fcbd183/LFM2-1.2B-Tool-Q8_0.gguf) |
| Aya Expanse · 8B | Q4_K_M | 5.057 | [Doğrulanan dosya](https://huggingface.co/bartowski/aya-expanse-8b-GGUF/blob/f9d62ed0c58e6f2ae17975df990b1b8a4013b596/aya-expanse-8b-Q4_K_M.gguf) |
| Aya Expanse · 8B | Q5_K_M | 5.804 | [Doğrulanan dosya](https://huggingface.co/bartowski/aya-expanse-8b-GGUF/blob/f9d62ed0c58e6f2ae17975df990b1b8a4013b596/aya-expanse-8b-Q5_K_M.gguf) |
| Aya Expanse · 8B | Q8_0 | 8.541 | [Doğrulanan dosya](https://huggingface.co/bartowski/aya-expanse-8b-GGUF/blob/f9d62ed0c58e6f2ae17975df990b1b8a4013b596/aya-expanse-8b-Q8_0.gguf) |
| Aya Expanse · 32B | Q4_K_M | 19.801 | [Doğrulanan dosya](https://huggingface.co/bartowski/aya-expanse-32b-GGUF/blob/3acdc2838db0bc64d2371f6b7d0eafab50fdbb0f/aya-expanse-32b-Q4_K_M.gguf) |
| Aya Expanse · 32B | Q5_K_M | 23.051 | [Doğrulanan dosya](https://huggingface.co/bartowski/aya-expanse-32b-GGUF/blob/3acdc2838db0bc64d2371f6b7d0eafab50fdbb0f/aya-expanse-32b-Q5_K_M.gguf) |
| Aya Expanse · 32B | Q8_0 | 34.327 | [Doğrulanan dosya](https://huggingface.co/bartowski/aya-expanse-32b-GGUF/blob/3acdc2838db0bc64d2371f6b7d0eafab50fdbb0f/aya-expanse-32b-Q8_0.gguf) |
| OLMo 2 · 7B Instruct | Q4_K_M | 4.472 | [Doğrulanan dosya](https://huggingface.co/bartowski/OLMo-2-1124-7B-Instruct-GGUF/blob/01a56cca7da47f11851889af56ec36a9e75ceac8/OLMo-2-1124-7B-Instruct-Q4_K_M.gguf) |
| OLMo 2 · 7B Instruct | Q5_K_M | 5.209 | [Doğrulanan dosya](https://huggingface.co/bartowski/OLMo-2-1124-7B-Instruct-GGUF/blob/01a56cca7da47f11851889af56ec36a9e75ceac8/OLMo-2-1124-7B-Instruct-Q5_K_M.gguf) |
| OLMo 2 · 7B Instruct | Q8_0 | 7.760 | [Doğrulanan dosya](https://huggingface.co/bartowski/OLMo-2-1124-7B-Instruct-GGUF/blob/01a56cca7da47f11851889af56ec36a9e75ceac8/OLMo-2-1124-7B-Instruct-Q8_0.gguf) |
| OLMo 2 · 13B Instruct | Q4_K_M | 8.354 | [Doğrulanan dosya](https://huggingface.co/bartowski/OLMo-2-1124-13B-Instruct-GGUF/blob/00f2e4aed2fdcac064c1b9613ce2d520f54369e2/OLMo-2-1124-13B-Instruct-Q4_K_M.gguf) |
| OLMo 2 · 13B Instruct | Q5_K_M | 9.762 | [Doğrulanan dosya](https://huggingface.co/bartowski/OLMo-2-1124-13B-Instruct-GGUF/blob/00f2e4aed2fdcac064c1b9613ce2d520f54369e2/OLMo-2-1124-13B-Instruct-Q5_K_M.gguf) |
| OLMo 2 · 13B Instruct | Q8_0 | 14.579 | [Doğrulanan dosya](https://huggingface.co/bartowski/OLMo-2-1124-13B-Instruct-GGUF/blob/00f2e4aed2fdcac064c1b9613ce2d520f54369e2/OLMo-2-1124-13B-Instruct-Q8_0.gguf) |
| MiniCPM 4 · 8B | Q4_K_M | 4.966 | [Doğrulanan dosya](https://huggingface.co/openbmb/MiniCPM4-8B-GGUF/blob/5e4751f57b110a0318cee65ec82109bad89c12b8/MiniCPM4-8B-Q4_K_M.gguf) |
| InternLM 2.5 · 1.8B | Q4_K_M | 1.172 | [Doğrulanan dosya](https://huggingface.co/bartowski/internlm2_5-1_8b-chat-GGUF/blob/782e438fc68523d786a8ecfee887536db4a8987b/internlm2_5-1_8b-chat-Q4_K_M.gguf) |
| InternLM 2.5 · 1.8B | Q5_K_M | 1.356 | [Doğrulanan dosya](https://huggingface.co/bartowski/internlm2_5-1_8b-chat-GGUF/blob/782e438fc68523d786a8ecfee887536db4a8987b/internlm2_5-1_8b-chat-Q5_K_M.gguf) |
| InternLM 2.5 · 1.8B | Q8_0 | 2.010 | [Doğrulanan dosya](https://huggingface.co/bartowski/internlm2_5-1_8b-chat-GGUF/blob/782e438fc68523d786a8ecfee887536db4a8987b/internlm2_5-1_8b-chat-Q8_0.gguf) |
| InternLM 2.5 · 7B | Q4_K_M | 4.713 | [Doğrulanan dosya](https://huggingface.co/bartowski/internlm2_5-7b-chat-GGUF/blob/34fdc9783472bb1fd7d1d04a412d1f2ae029459a/internlm2_5-7b-chat-Q4_K_M.gguf) |
| InternLM 2.5 · 7B | Q5_K_M | 5.507 | [Doğrulanan dosya](https://huggingface.co/bartowski/internlm2_5-7b-chat-GGUF/blob/34fdc9783472bb1fd7d1d04a412d1f2ae029459a/internlm2_5-7b-chat-Q5_K_M.gguf) |
| InternLM 2.5 · 7B | Q8_0 | 8.224 | [Doğrulanan dosya](https://huggingface.co/bartowski/internlm2_5-7b-chat-GGUF/blob/34fdc9783472bb1fd7d1d04a412d1f2ae029459a/internlm2_5-7b-chat-Q8_0.gguf) |
| Yi 1.5 · 6B Chat | Q4_K_M | 3.674 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-1.5-6B-Chat-GGUF/blob/d91a0cede594cb9f627e4601b8660b55d09dd3c2/Yi-1.5-6B-Chat-Q4_K_M.gguf) |
| Yi 1.5 · 6B Chat | Q5_K_M | 4.304 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-1.5-6B-Chat-GGUF/blob/d91a0cede594cb9f627e4601b8660b55d09dd3c2/Yi-1.5-6B-Chat-Q5_K_M.gguf) |
| Yi 1.5 · 6B Chat | Q8_0 | 6.442 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-1.5-6B-Chat-GGUF/blob/d91a0cede594cb9f627e4601b8660b55d09dd3c2/Yi-1.5-6B-Chat-Q8_0.gguf) |
| Yi 1.5 · 9B Chat | Q4_K_M | 5.329 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-1.5-9B-Chat-GGUF/blob/818987823fe7567eb636bd17c49e9a17567e25d8/Yi-1.5-9B-Chat-Q4_K_M.gguf) |
| Yi 1.5 · 9B Chat | Q5_K_M | 6.258 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-1.5-9B-Chat-GGUF/blob/818987823fe7567eb636bd17c49e9a17567e25d8/Yi-1.5-9B-Chat-Q5_K_M.gguf) |
| Yi 1.5 · 9B Chat | Q8_0 | 9.384 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-1.5-9B-Chat-GGUF/blob/818987823fe7567eb636bd17c49e9a17567e25d8/Yi-1.5-9B-Chat-Q8_0.gguf) |
| Yi Coder · 1.5B Chat | Q4_K_M | 0.964 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-Coder-1.5B-Chat-GGUF/blob/442545c4f577cfdab9a70b38fec719c47d393b8b/Yi-Coder-1.5B-Chat-Q4_K_M.gguf) |
| Yi Coder · 1.5B Chat | Q5_K_M | 1.100 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-Coder-1.5B-Chat-GGUF/blob/442545c4f577cfdab9a70b38fec719c47d393b8b/Yi-Coder-1.5B-Chat-Q5_K_M.gguf) |
| Yi Coder · 1.5B Chat | Q8_0 | 1.571 | [Doğrulanan dosya](https://huggingface.co/bartowski/Yi-Coder-1.5B-Chat-GGUF/blob/442545c4f577cfdab9a70b38fec719c47d393b8b/Yi-Coder-1.5B-Chat-Q8_0.gguf) |
| Devstral Small 2507 · 24B | Q4_K_M | 14.334 | [Doğrulanan dosya](https://huggingface.co/unsloth/Devstral-Small-2507-GGUF/blob/8d0c7eb7bf0142cc3b94c88450eddcc7720e4488/Devstral-Small-2507-Q4_K_M.gguf) |
| Devstral Small 2507 · 24B | Q5_K_M | 16.764 | [Doğrulanan dosya](https://huggingface.co/unsloth/Devstral-Small-2507-GGUF/blob/8d0c7eb7bf0142cc3b94c88450eddcc7720e4488/Devstral-Small-2507-Q5_K_M.gguf) |
| Devstral Small 2507 · 24B | Q8_0 | 25.055 | [Doğrulanan dosya](https://huggingface.co/unsloth/Devstral-Small-2507-GGUF/blob/8d0c7eb7bf0142cc3b94c88450eddcc7720e4488/Devstral-Small-2507-Q8_0.gguf) |
| SmolLM3 · 3B | Q4_K_M | 1.915 | [Doğrulanan dosya](https://huggingface.co/unsloth/SmolLM3-3B-GGUF/blob/a7bc17204c8a326d6bd6e466e076959eddae2025/SmolLM3-3B-Q4_K_M.gguf) |
| SmolLM3 · 3B | Q5_K_M | 2.214 | [Doğrulanan dosya](https://huggingface.co/unsloth/SmolLM3-3B-GGUF/blob/a7bc17204c8a326d6bd6e466e076959eddae2025/SmolLM3-3B-Q5_K_M.gguf) |
| SmolLM3 · 3B | Q8_0 | 3.276 | [Doğrulanan dosya](https://huggingface.co/unsloth/SmolLM3-3B-GGUF/blob/a7bc17204c8a326d6bd6e466e076959eddae2025/SmolLM3-3B-Q8_0.gguf) |
| Seed OSS · 36B | Q4_K_M | 21.762 | [Doğrulanan dosya](https://huggingface.co/unsloth/Seed-OSS-36B-Instruct-GGUF/blob/6403aa019fffb2d698433e3aed271d8962e28a58/Seed-OSS-36B-Instruct-Q4_K_M.gguf) |
| Seed OSS · 36B | Q5_K_M | 25.594 | [Doğrulanan dosya](https://huggingface.co/unsloth/Seed-OSS-36B-Instruct-GGUF/blob/6403aa019fffb2d698433e3aed271d8962e28a58/Seed-OSS-36B-Instruct-Q5_K_M.gguf) |
| Seed OSS · 36B | Q8_0 | 38.421 | [Doğrulanan dosya](https://huggingface.co/unsloth/Seed-OSS-36B-Instruct-GGUF/blob/6403aa019fffb2d698433e3aed271d8962e28a58/Seed-OSS-36B-Instruct-Q8_0.gguf) |

## Yerel dosya ekleme

Model seçimi motor ayarından bağımsız algılanır: `.gguf`, `.GGUF`, dosya uzantısı bulunmayan gerçek GGUF, `file://` URI, tırnak içindeki yol, `~` ve model klasörü kabul edilir. Safetensors veya `config.json` seçilirse dosyanın ait olduğu yerel model klasörü seçilir; ağırlık parçaları ve tokenizer yoksa eksik dosya açıklanır. Arşiv doğrudan model sayılmaz. Yalnızca yardımcı `mmproj` veya MTP dosyası sohbet modeli olarak seçilmez. Bölünmüş GGUF dosyaları aynı klasörde tam olmalı; ilk parça kullanılır. Seçim kullanıcı dosyasını taşımaz veya kopyalamaz.

## Test kapsamı

Ağdan bağımsız testler: harf duyarlı dosya filtresi, URI/tırnak/Unicode yol normalizasyonu, eksik model parçası, yardımcı projektör, çok parçalı GGUF, kayıp kuantizasyonun yanlış varyantla değiştirilmemesi, eski commit 404 kurtarması, resume/SHA bozulması, cache kimlik yalıtımı, iptal ve çevrimdışı doğrulama. Gerçek ağ kontrolü yalnızca küçük metadata yanıtlarıyla yapıldı; gerçek büyük dosya transferi ve her ailenin cihazda çıkarımı bu çalışmanın doğrulama kanıtı değildir.
