# ShiftScan

Vardiya fotoğrafını saniyeler içinde ICS takvim dosyasına dönüştüren web uygulaması.

**Demo:** [vardiya.egebostanci.me](https://vardiya.egebostanci.me)

## Özellikler

- OCR ile görsellerden vardiya metni çıkarma
- Metin formatında vardiya girişi
- ICS takvim dosyası oluşturma
- Modern ve responsive arayüz
- FastAPI backend

## Kurulum

1. Python 3.10+ gerekli

2. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

3. Eski tek anahtarlı demo planlaması için (isteğe bağlı; kullanıcı bağlantıları için aşağıya bakın):
```
SHIFTSCAN_DEMO_AI=true
GOOGLE_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-3.6-flash   # istege bagli, varsayilan bu
```

## Çalıştırma

```bash
python main.py
```

Uygulama http://localhost:8000 adresinde çalışacaktır.

## Kullanım

1. Haftanın başlangıç tarihini seçin
2. Vardiya programı görselini yükleyin ve kırpın
3. "Seçili Alanı Tara" ile OCR yapın (veya manuel girin)
4. "Önizle ve Dönüştür" ile ICS oluşturun
5. Takvim dosyasını indirin

## Desteklenen Formatlar

```
Pzt 08:00 - 17:00
Salı OFF
Çarşamba 14:00 - 22:00
```

### Gün Kısaltmaları
Pzt, Sal, Çar, Per, Cum, Cmt, Paz (TR)
Mon, Tue, Wed, Thu, Fri, Sat, Sun (EN)

### İzin/Tatil
OFF, İZİN, BOŞ, TATİL, RAPOR

## Aktiviteler

Aktiviteler **Gelişmiş Mod** kaldırması arkasında opsiyonel bir özelliktir. Etkinleştirildiğinde,
ShiftScan boş zamanınızı tanımladığınız aktivitelerin etrafına planlayabilir. Varsayılan
aktiviteler sağlanır (İçerik Üretimi, Spor, Kitap Okuma, Sosyal Yaşam, Oyun / Dinlenme)
ancak bunları yeniden adlandırabilir, silebilir veya yeni olanlar ekleyebilirsiniz.

Her aktivitenin:
- **Adı**: onu nasıl çağırdığınız
- **Miktarı**: haftada ne kadar zaman istediğiniz (bir sayı)
- **Birimi**: bunun saat mi yoksa gün mü olduğu
- **Tercih edilen zaman**: bunu yapmak istediğiniz zaman (sabah, öğleden sonra, akşam veya herhangi bir zaman)

Aktivite listeniz tarayıcınızın `localStorage` alanında `shiftscan-activities-v1` adıyla
saklanır. Plan isteğinin parçası olarak backend'e; bir AI bağlantısı seçildiğinde
aktivite hedefleri ve boş zaman bilgileri seçilen sağlayıcıya gönderilir. Aynı anda 1 ile 20 arasında aktivite etkinleştirebilirsiniz.

## Gizlilik

**Taradığınız görseller üçüncü tarafa gönderilir.** OCR, bu projeye ait olmayan,
bağımsız bir kişi tarafından işletilen `prithivMLmods/Multimodal-OCR` adlı public
HuggingFace Space üzerinde çalışır. Bir vardiya çizelgesi fotoğrafı işvereninizi,
adınızı ve çalışma saatlerinizi açık edebilir.

Bu sizin için uygun değilse:

- görsel tarama yerine manuel metin girişini kullanın, veya
- OCR modelini kendiniz barındırıp `services/ocr_service.py` içindeki
  `MULTIMODAL_OCR_SPACE` değerini kendi sunucunuza yönlendirin.

Uygulama yüklenen görselleri saklamaz. Görsel, istek süresince geçici bir dosyaya
yazılır ve hemen ardından silinir.

AI planlayıcı açıkken boş zaman özetiniz ve aktivite hedefleriniz Google Gemini'ye
gönderilir. Görsel Gemini'ye hiçbir zaman gönderilmez. `GOOGLE_API_KEY` yoksa
uygulama kural tabanlı planlayıcıya düşer ve çalışmaya devam eder.

## Testler

```bash
pip install -r requirements-dev.txt
pytest                        # backend (102 test)
node --test tests/js/*.test.js  # tarayici testleri (41 test)
```

Her push ve pull request'te GitHub Actions bu iki paketi ve bir Docker build'i
calistirir (`.github/workflows/ci.yml`).

## Lisans

MIT License


## Kullanıcı hesapları ve çoklu sağlayıcı (11 Eylül 2026)

Hesaplarım panelinde kullanıcı adı/parola ile kayıt olun, ardından bir veya birden
fazla Gemini, OpenAI, Anthropic ya da OpenRouter API bağlantısı ekleyin. Aynı
sağlayıcıya birden fazla anahtar/model kaydedilebilir. Model kimliği sağlayıcının
belgelerinden alınır; her model görsel veya JSON çıktısını desteklemez. Bağlantı
eklemek API çağrısı yapmaz. İlk tarama/plan isteğinde anahtar ve model denenir.

- OCR ve aktivite planlama bağlantıları ayrı seçilir. Seçim yapılmadığında yerel
  OCR/kural tabanlı plan kullanılır; sunucunun Google anahtarına sessiz geçiş yoktur.
- Sağlayıcı hatasında planlama ücretsiz kural tabanlı plana düşer ve uyarı gösterir.
  Başka ücretli bağlantıya otomatik geçiş yoktur. Başka bağlantıyı seçip yeniden
  denemek mümkündür. Her kullanıcıda en fazla 20 bağlantı, 2 eşzamanlı sağlayıcı işi
  ve 15 dakikada 30 sağlayıcı isteği sınırı vardır; servis sağlayıcının kendi kotası ayrıdır.
- Anahtarlar Fernet ile şifreli, oturumlar sunucuda token hash'iyle saklanır.
  Cookie HttpOnly/SameSite; canlıda Secure olmalıdır. Parola sıfırlama/e-posta
  doğrulaması bu sürümde yoktur. Kullanıcı verileri `.local-preview` veya `data`
  diziniyle beraber Git ve container image'ından dışlanır.

### Hesap hizmetini yapılandırma

`.env.example` dosyasını temel alın. `SHIFTSCAN_DB_PATH` kalıcı yazılabilir bir
SQLite dosyasını göstermeli; `SHIFTSCAN_ENCRYPTION_KEY` geçerli Fernet anahtarı
olmalıdır. Bu ikisi olmadan hesap rotaları kullanılamaz; manuel kullanım sürer.
Anahtarı bir kere üretin, secret olarak saklayın; yeniden başlatmada değiştirmeyin.
Anahtar kaybolursa şifreli sağlayıcı bağlantıları kurtarılamaz. DB ve anahtarın
yedeklerini ayrı, erişimi sınırlı konumlarda tutun.

Yerel HTTP geliştirmesinde `SHIFTSCAN_SECURE_COOKIES=false` kullanılır; HTTPS canlı
kurulumda varsayılan `true` kalmalıdır. Reverse proxy arkasında doğru HTTPS scheme
bilgisinin uygulamaya ulaşması gerekir; yalnız bilinen proxy adreslerini uvicorn
`--forwarded-allow-ips`/`FORWARDED_ALLOW_IPS` ile güvenilir olarak tanımlayın. Login
rotaları `Origin` ile uygulama origin'ini karşılaştırır; yanlış proxy ayarı 403 doğurur.

SQLite tek hostta kalıcı diskle çalışır. Mevcut Render free/stateless dağıtımına
kullanıcı DB'sini geçici dosya sisteminde açmayın. Kalıcı diskli dağıtım veya başka
bir kalıcı veri deposu kararı verilmeden canlı kullanıcı kaydı açılmamalıdır.
Mevcut Blueprint otomatik olarak bu kaynakları sağlamaz. Yayın ayrı işlemdir.

### Yeni OCR akışı

1. Hafta ve OCR bağlantısını seçin. Bulut seçildiğinde hangi sağlayıcıya
   gönderileceği gösterilir; yalnız PNG/JPEG/WebP, en fazla 8 MB ve sunucuda 24 MP.
2. Tam görseli veya isteğe bağlı kırpılmış alanı tarayın. Tam tablo başka
   çalışanların bilgilerini içerebilir; yalnız kendi satırınızı kırpabilirsiniz.
3. Bulut çıktısında kişiyi seçin, gün/tarih ve saatleri inceleyin. Okunamayan gün
   izin sayılmaz. Bir günde birden fazla vardiya virgülle girilebilir.
4. Yerel OCR ham metni çıkarır; kişi/gün ilişkisini otomatik tahmin etmez.
   İnceleme ekranında yedi günü tamamlayın. Görsel seçilen sağlayıcı haricinde
   başka bir buluta otomatik gönderilmez.
5. İnceleme kutusunu işaretleyip vardiyaları aktarın, önizleyin ve takvimi indirin.

Görseller/ham OCR metni yeni akışta sunucuda kalıcı saklanmaz veya loglanmaz.
Yerel OCR motoru/dil dosyaları ilk kullanımda CDN'den indirilebilir; tamamen
çevrimdışı ilk açılış garanti edilmez. İptal tarayıcının beklemesini keser; başlamış
bir sağlayıcı isteğinin ücretini geri almaz. API modellerinin gerçek başarımı ve
maliyeti anonimleştirilmiş vardiya örnekleriyle ayrıca kıyaslanmalıdır.

### Abonelikle giriş durumu

Claude/Gemini abonelik OAuth bağlantıları **henüz etkin değil**. ChatGPT için aşağıdaki deneysel cihaz kodu akışı eklendi. Adaptör
ve hesap sınırları hazır, ancak Zed'in masaüstü loopback akışını genel web sitesi
OAuth'u olarak kullanmak doğrulanmış değil. Claude üçüncü taraf ürün girişi için
sağlayıcı onayı gerektiriyor. API anahtarıyla kullanım abonelik kotası kullanmaz.
Bu sınırlama arayüzde de gösterilir; çalışmayan giriş butonu veya token yapıştırma
geçici çözümü yoktur. Araştırma: `docs/2026-09-11-inceleme.md`.

Eski HuggingFace `/ocr` yolu varsayılan kapalıdır (`SHIFTSCAN_LEGACY_OCR=false`).
Yeni arayüz onu kullanmaz. Eski endpoint'in çalışması güncel olarak doğrulanmadı;
sentetik boş görsel kontrolünde uzak Space API adı bulunamadı. Demo için açılırsa
eski servis ayrı bir dış veri aktarımıdır; canlı çok kullanıcılı kullanım için açmayın.

Takvim dosyaları mevcut floating yerel saat davranışını korur. Başka saat
dilimindeki takvime aktarımda aynı UTC anını korumaz.

### ChatGPT aboneliği — deneysel, tek worker

`SHIFTSCAN_CHATGPT_ENABLED=true` ve sunucuda Codex CLI gerektirir. Protokol Codex 0.153.4 ile sınandı; `SHIFTSCAN_CODEX_BIN` mutlak binary yolu olabilir. Mevcut Docker image CLI içermez; üretim yayınına hazır kabul etmeyin. Bu aşamada yalnız tek Uvicorn worker/tek uygulama örneği desteklenir; login görevleri ve bağlantı kilitleri süreç belleğindedir. Yeniden başlatmada bekleyen girişler yeniden başlatılmalıdır.

1. ShiftScan'e giriş yapın, hesap bölümünde **ChatGPT ile bağlan** seçin.
2. Gösterilen OpenAI sayfasında tek kullanımlık kodu onaylayın. OpenAI hesabının güvenlik ayarlarında cihaz kodu izni gerekebilir.
3. Hesabın model listesinden seçim yapıp **Bağlantıyı kaydet** seçin. Aynı kullanıcı ardışık olarak birden fazla hesap bağlayabilir.
4. Gelişmiş modda planlama bağlantısını seçin. ChatGPT bağlantısı OCR listesinde gösterilmez; görsel çağrısı bu sürümde desteklenmez.

Giriş 10 dakika içinde tamamlanır veya iptal edilir. OpenAI şifresi uygulamaya gelmez. Tokenlar mevcut Fernet deposunda kullanıcı ve bağlantı kimliğine bağlı şifrelenir; yenileme sonrası kayıt güncellenir. İşlem sırasında 0700 geçici home içinde 0600 auth.json kullanılır, işlem bitince silinir. Sunucu yöneticisinin Codex home'u, API anahtarları ve eklenti ayarları devralınmaz. Uygulama aniden öldürülürse geçici dizin kalabilir; üretimde kullanıcı başına kapsayıcı/tmpfs ve yaşam döngüsü temizliği gerekir.

Codex araçları kapatılır, read-only/never politikası uygulanır ve araç çağrısı görülürse süreç sonlandırılır. Bu kontroller işletim sistemi seviyesinde kullanıcı başına izolasyon yerine geçmez. Herkese açık çok kullanıcılı yayın öncesi izole worker tasarımı ve kaynak sınırları ayrıca tamamlanmalıdır. API fallback yalnız ücretsiz kural tabanlı yoldur. Başarılı login tek başına model çağrısının doğrulandığı anlamına gelmez.

Kaynak: [Codex App Server](https://developers.openai.com/codex/app-server), [Codex authentication](https://developers.openai.com/codex/auth/).
