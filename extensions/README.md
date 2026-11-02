# MCP ve eklentiler

Kayriva’nun eklenti sınırı MCP’dir. Blender dahil araç sunan stdio / Streamable HTTP sunucuları eklenebilir. Bu, tüm eklenti ekosistemleriyle doğrudan uyumluluk anlamına gelmez: VS Code uzantıları, tarayıcı eklentileri ve özel API’ler MCP adaptörü gerektirir.

Uygulamada **Bağlantılar → JSON / eklenti içe aktar** ile bir yapılandırma seç. İçe aktarılan sunucular kapalı gelir. Test et, sonra etkinleştir. Model araç istediğinde seçili İşlem onayı politikası uygulanır; Sormadan uygula modunda tekrar pencere açılmaz.

```json
{
  "mcpServers": {
    "my-tool": {
      "command": "python3",
      "args": ["/absolute/path/server.py"],
      "env": {}
    },
    "remote-tool": {
      "url": "https://your-server.example/mcp",
      "header_env": {"Authorization": "MY_MCP_AUTH_HEADER"}
    }
  }
}
```

`header_env` örneğinde ortam değişkeninin değeri `Bearer ...` dahil tam başlık değeridir. Anahtarları paylaşılan JSON’a koyma. stdio sunucusu çalışacağı dizini `cwd` ile belirtebilir. Komutlar shell üzerinden çalıştırılmaz; argümanlar JSON dizisidir.

## Blender

[MCP for Blender](https://github.com/ahujasid/mcp-for-blender) topluluk eklentisidir. Örnek JSON güncel `uvx mcp-for-blender` komutunu kullanır ve sunucu telemetrisini `DISABLE_TELEMETRY=true` ile kapatır. Blender’ın içinde eklentinin ayrıca kurulmuş, etkinleştirilmiş ve bağlantısının açık olması gerekir. Bu proje Blender eklentisini otomatik kurmaz. Model ve eklenti gereklilikleri tamamlanmadan gerçek Blender işlemi test edilmemiştir.

Başka eklentiler kendi ağ erişimini yapabilir. Kayriva’nun çevrimdışı modu bu nedenle tüm MCP süreçlerinin başlatılmasını engeller. Etkin sunucular işletim sistemindeki kullanıcı yetkileriyle çalışır; MCP bir sandbox değildir.

Desteklenen kısım: initialize, initialized, ping, tools/list (sayfalı), tools/call, JSON / POST SSE yanıtları, HTTP oturum kimliği ve kapatma. OAuth, legacy HTTP+SSE, sampling, elicitation, resource/prompt arayüzleri ve HTTP bağlantısı kaldığı yerden devam etme henüz yok. Bu özellikleri zorunlu tutan sunucular desteklenmez.
