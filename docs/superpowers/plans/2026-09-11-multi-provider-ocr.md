# Çoklu sağlayıcı ve OCR uygulama planı

> Uygulayıcılar: superpowers:subagent-driven-development ile görevleri uygula; her görevde önce başarısız davranış testi, sonra kod ve doğrulama.

**Hedef:** Kullanıcı başına çoklu API bağlantısı ve tam görselden kişi/tarih/vardiya çıkarımı; güvenli abonelik adaptör sınırı.
**Mimari:** FastAPI + SQLite oturum/şifreli bağlantı deposu; sabit sağlayıcı endpoint'leri; şemalı OCR; mevcut JS arayüzüne modüler hesaplar ve inceleme paneli.
**Teknoloji:** Python 3.10+, FastAPI, httpx, cryptography Fernet, stdlib scrypt/SQLite, vanilla JS.
**Tasarım:** ../../2026-09-11-inceleme.md (kullanıcı 11 Eylül'de uygulamayı onayladı).

## Genel sınırlar
- Deploy/push yok. Çalışma dalı codex/multi-provider-ocr.
- Görsel/model çıktısı güvenilmez; kullanıcılar arasında sır ve iş paylaşımı yok.
- Abonelik girişinin doğrulanmadığı sağlayıcıya çalışıyor süsü verilmez. API yolu abonelik hedefini tamamlamaz.
- Kalıcı DB ve şifreleme anahtarı yapılandırılmadığında hesap uçları 503; sessiz geçici sır üretimi yok.
- Ücretli otomatik fallback yok; kullanıcı ayrı bağlantı seçerek tekrar deneyebilir.

## Görev 1 — Plan doğruluğu
Dosyalar: services/ai_planner.py, yeni services/shift_validation.py, tests/test_plan_limits.py.
Arayüz: ShiftEvent Pydantic (start/end ISO string olarak dışarıda korunur), validate_shifts(events, week_start, timezone).
- [x] Hedef 1 saat/model 12 saat ve tekrarlı gün satırları için başarısız test.
- [x] AI yerleştirmesini kalan hedefe, iki saat bloğa, gün hedefinde bir saat/tek oturuma sınırla.
- [x] Tarih/süre/sıra/hafta/adet ve çakışma doğrulaması; main entegrasyonu root'a ait.
- [x] Odak testleri: `.venv/bin/python -m pytest tests/test_plan_limits.py -q`.

## Görev 2 — Kullanıcı ve bağlantı deposu
Dosyalar: services/accounts.py, services/account_routes.py, tests/test_accounts.py.
Arayüz: get_store() -> AccountStore; current_user(request) -> dict{id,username}; require_csrf(request); store.list_connections(user_id), get_connection(user_id,id) (sır dahil yalnız içeride), add_connection(user_id, provider,label,model,api_key), delete_connection(user_id,id).
- [x] Gerçek SQLite ile iki kullanıcı arasında erişim, şifreli disk, login/logout/CSRF testlerini yaz ve RED doğrula.
- [x] Username/password kayıt, scrypt, hash'lenmiş session, expiry, HttpOnly/SameSite cookie, login hız sınırı.
- [x] GET /api/session; POST /api/auth/register, login, logout; kullanıcı yönetimi /api/connections root/provider görevi.
- [x] Odak testleri: `.venv/bin/python -m pytest tests/test_accounts.py -q`.

## Görev 3 — Sağlayıcı adaptörleri
Dosyalar: services/providers.py, services/provider_routes.py, tests/test_providers.py.
Arayüz: async generate_json(connection,prompt,image=None)->dict|list; image={mime_type,data}; ProviderError(code,message,status_code); connection={provider,model,api_key}. SUPPORTED_PROVIDERS sabit Gemini/OpenAI/Anthropic/OpenRouter metaverisi.
- [x] HTTP MockTransport ile istek şekli, 401/429/deadline/bozuk çıktı, key redaksiyonu testlerini önce yaz.
- [x] Sabit HTTPS hedefleri, görsel payload, JSON çıkarımı, timeout/yanıt boyutu sınırı. Keyfi base URL yok.
- [x] GET/POST /api/connections; DELETE /api/connections/{id}; GET /api/providers; kayıt yanıtlarında secret yok, CSRF ve sahiplik zorunlu.
- [x] Odak testleri: `.venv/bin/python -m pytest tests/test_providers.py -q`.

## Görev 4 — Yapılandırılmış OCR ve entegrasyon
Dosyalar: services/schedule_extraction.py, main.py, static/js/accounts.js, static/js/schedule-review.js, static/js/app.js, templates/index.html, templates/sw.js, static/css/style.css; tests/test_extraction.py, tests/test_multiuser_api.py, tests/js/schedule-review.test.js.
- [x] Şema: people[{id,name,days[{date,day_index,status,shifts[{start,end}],source_text,issue}]}], warnings. Bilinmeyen hücre OFF'a dönüşmez; tarih/hafta uyuşmazlığı işaretlenir.
- [x] POST /api/ocr/extract: oturum, CSRF, bağlantı sahipliği, görüntü byte/pixel sınırı, şema doğrulama, per-user iş sınırı.
- [x] generate-plan seçili connection_id kullanır; seçilmediyse kural tabanlı. Legacy demo AI yalnız açık env izniyle.
- [x] Arayüz: hesap oluştur/giriş/çıkış; çoklu bağlantı ekle/sil; OCR ve plan için ayrı seçim; tam görsel/kırpılmış görsel; yerel veya seçili sağlayıcı; kişi seçimi ve düzenlenebilir hücreler; inceleme onayı.
- [x] Service worker hesap/iş API'lerini cache'lemez. Server validation hataları hassas input echo etmez. Toast kullanıcı metnini HTML olarak işlemez.
- [x] Tam test, syntax kontrolü, yerel HTTP/browser testi. Sağlayıcı credentials olmadan canlı doğrulama yapılamadığını raporla.

## Görev 5 — Dağıtım hazırlığı ve inceleme
Dosyalar: requirements.txt, .env.example, .gitignore, .dockerignore, README_TR.md, docs/2026-09-11-inceleme.md.
- [x] DB/şifreleme anahtarı/secure cookie/persistent volume gereksinimini belgeleyip örnek yapılandırma ekle.
- [x] Bağımsız bütünleşik kod incelemesi; bulguları düzelt ve hedef testleri tekrarla.
- [x] Yalnız görev dosyalarını commit; canlıya yayınlama yok. Vault kanonik kaydı güncelle.

Son durum: İlk aşama tamamlandı; abonelik OAuth açık kapsamdır. Gerçek sağlayıcı anahtarıyla canlı test yapılmadı. Ayrıntı ve sınırlar inceleme belgesinin son bölümünde.
