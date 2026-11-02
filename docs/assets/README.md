# README görselleri

Bu klasördeki SVG'ler Kayriva için çizilmiştir. Uygulamanın kendi geometrik amblemi, grafit yüzeyleri ve lavanta vurgusu kullanılır. Üçüncü taraf README'sinden görsel veya yerleşim kopyalanmaz. Çalışma akışı bir mimari diyagramdır; uygulama ekran görüntüsü olarak sunulmaz.

Metinler, GitHub ve farklı işletim sistemlerinde aynı görünmeleri için projeyle gelen **Noto Sans** yazı tipinden SVG yollarına dönüştürülür. Okuyucular için her dosyada başlık/açıklama ve README'de alternatif metin vardır. Font lisansı: [SIL OFL](../../src/ai_studio/ui/assets/NotoSans-LICENSE.txt).

Görselleri güncellemek için proje ortamında:

```bash
python3 docs/assets/generate.py
```

Bu komut PySide6 gerektirir; hiçbir ağ isteği yapmaz. Metin ve vektör geometrisi `generate.py` içindedir. Çıktılar:

- `kayriva-banner.svg`: proje kimliği, 1120 × 360.
- `nav-start.svg`, `nav-models.svg`, `nav-projects.svg`: README içi gezinme, 352 × 88.
- `local-workflow.svg`: yerel çalışma akışı, 1120 × 180.

`kayriva-desktop.png`, örnek projeler ve yerel test verileriyle alınmış gerçek 1200 × 800 uygulama görüntüsüdür; seçilmiş/yüklü model göstermez. PNG değiştirilmeden eklenmiştir; köken bilgisi yanındaki `.json` dosyasında bulunur. `generate.py` bu ekran görüntüsünü üretmez veya değiştirmez.
