# Başka bir asistanla iş bölümü

Başka bir asistan Kayriva’ya araştırma veya analiz işi bırakabilir. Yerel model bu işi yürütüp sonucu geri verir. Bağlantı, kullandığın asistanın MCP ayarlarına eklenir.

1. Uygulamayı aç, model ve motor kurulumunu tamamla.
2. Ayarlar → İş bölümü içinde **Yeni profil** ile istediğin kadar profil ekle. **Asistan adı**, **Rol**, **Yerel model**, **Bağlantı biçimi** ve **Talimatlar** alanlarını doldurup **Profili kaydet** düğmesine bas. Araştırmacı, editör, danışman gibi istediğin rolü kullanabilirsin.
3. **MCP ile görev kabul et** seçeneğini aç.
4. **Bağlantıyı kopyala** düğmesine bas; istemcinin desteklediği TOML veya `mcpServers` JSON yapılandırmasını diğer asistanın stdio MCP yapılandırmasına ekle ve o istemcinin yöntemine göre etkinleştir.
5. Asistana devredilecek görevi belirt. Örneğin araştırmayı yerel asistana bırakıp yazma/düzenleme görevini diğer asistanda tutabilirsin.

Uygulama seçimi bağlantıyı otomatik kurmaz ve dış asistanın kimliğini doğrulamaz. **i** düğmesi kurulum adımlarını açıklar. Her bağlantı `--profile` kimliği taşır; gelen işler bu profilin rolü, talimatları ve model seçimiyle kuyruklanır. Başka profilin işleri listelenemez, okunamaz veya iptal edilemez. Yerel SQLite’a erişebilen süreçler için bu bir güvenlik sınırı değildir.

Bu profil yalnızca devredilen görevlerde uygulanır. Normal sohbetin genel sistem talimatını değiştirmez. Kuyruğa alınan görev profilin o andaki kopyasını kullanır; profil değişikliği sonraki görevlerde geçerlidir.

Aynı sayfadan **Yerel analiz** veya **Web araştırması** seçerek görev oluşturabilirsin. Araştırmada Hızlı, Detaylı ve Uzun seçenekleri vardır. Listeden görev seçildiğinde sonucu görünür; durdurma ikonu seçili görevi iptal eder.

Kopyalanan yapılandırma gerçek Python yolu, proje kökü ve `PYTHONPATH` içerir; elle yol değiştirmene gerek yok. Köprü bulut sunucusu açmaz.

Araçlar:

| Araç | İş |
| --- | --- |
| `delegate_research` | Hızlı, detaylı veya uzun araştırma işini kuyruğa koyar |
| `ask_local_model` | Web araması olmadan yerel analiz işi bırakır |
| `get_task_result` | Kimliğiyle iş durumu ve sonucunu döndürür |
| `list_tasks` | Bu profile ait yakın işleri listeler |
| `cancel_task` | İşi durdurur |

İş oluşturma hemen kimlik döndürür. İstemci sonuç için en az beş saniye arayla kontrol edebilir; ana asistan bu sırada bağımsız iş yapabilir. Kayriva kapalı veya dış görev kabulü kapalıysa dışarıdan yeni işler reddedilir. Uygulama kapanınca heartbeat kapanır; profile ait kabul tercihi saklanır ve bir sonraki açılışta yeniden etkin olur. Çevrimdışı mod bütün dış görev kabulünü kapatır. Köprü ile oluşturulan işler MCP araç çağrısı yapmaz; analiz/arama ve model üretimi yapar.

İş bölümü iki asistanın otomatik olarak aynı sohbeti paylaştığı anlamına gelmez. Dış asistan yalnızca görev metnini gönderir ve sonucu alır. Bütün sohbet geçmişinin paylaşılması gerekmez.

Devredilen Web araştırması görevleri, görev türü ve MCP görev kabulüyle yetkilendirilen aramayı yürütür; ayrıca sohbet onay penceresinde beklemez. Bu görevler harici MCP araçlarını çalıştırmaz. Normal sohbetin web ve MCP işlemleri İşlem onayı menüsüne göre onay ister; proje okumaları Okumaları onayla modunda otomatik yapılabilir.

TOML çıktısı `mcp_servers`, JSON çıktısı `mcpServers` alanını kullanır. Kullandığın istemcinin MCP belgelerinden beklenen biçimi kontrol et; gerekirse yapılandırmayı onun ayar şemasına uyarla.
