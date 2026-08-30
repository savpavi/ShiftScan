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

1. Python 3.8+ gerekli

2. Bağımlılıkları yükleyin:
```bash
pip install -r requirements.txt
```

3. (Opsiyonel) Gemini API için `.env` dosyası oluşturun:
```
GOOGLE_API_KEY=your_api_key_here
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
saklanır ve asla cihazınızdan çıkmaz; sadece plan isteğinin parçası olarak backend'e
gönderilir. Aynı anda 1 ile 20 arasında aktivite etkinleştirebilirsiniz.

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
pytest                        # backend (80 test)
node --test tests/js/*.test.js  # tarayici testleri (28 test)
```

Her push ve pull request'te GitHub Actions bu iki paketi ve bir Docker build'i
calistirir (`.github/workflows/ci.yml`).

## Lisans

MIT License
