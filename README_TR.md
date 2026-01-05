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

## Lisans

MIT License
