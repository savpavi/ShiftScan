# Vardiya Takvim Oluşturucusu

Vardiya programını saniyeler içinde takvime dönüştüren web uygulaması.

## Özellikler

- OCR ile görsellerden vardiya metni çıkarma
- Metin formatında vardiya girişi
- ICS takvim dosyası oluşturma
- Modern ve responsive arayüz
- FastAPI backend ile sunucu

## Kurulum

1. Python'un kurulu olduğundan emin olun ( Python 3.8+ önerilir)

2. Gerekli paketleri yükleyin:
```bash
pip install -r requirements.txt
```

## Çalıştırma

Geliştirme modunda başlatmak için:
```bash
python main.py
```

Veya uvicorn kullanarak:
```bash
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

Uygulama http://localhost:8000 adresinde çalışacaktır.

## Proje Yapısı

```
vardiya-takvim-olu-turucusu/
├── main.py              # FastAPI uygulama dosyası
├── requirements.txt     # Python bağımlılıkları
├── templates/           # HTML şablonları
│   └── index.html      # Ana sayfa
├── static/              # Statik dosyalar
│   ├── css/
│   │   └── style.css    # Özel stiller
│   └── js/
│       └── app.js       # Frontend JavaScript
└── README.md            # Bu dosya
```

## Kullanım

1. **Tarih Seçimi**: Haftanın başlangıç tarihini ( Pazartesi) seçin
2. **Görsel Yükleme**: Vardiya programının görselini yükleyin ve kırpın
3. **OCR Taraması**: "Seçili Alanı Tara" butonuyla metni çıkarın
4. **Manuel Giriş**: Veya metin alanına vardiya bilgilerini manuel girin
5. **Dönüştür**: "Önizle ve Dönüştür" butonuyla ICS dosyasını oluşturun
6. **İndir**: Oluşturulan takvim dosyasını indirin

## Desteklenen Formatlar

### Metin Formatı
```
Pzt 08:00 - 17:00
Salı OFF
Çarşamba 14:00 - 22:00
Perşembe 08:00 - 17:00
Cuma OFF
Cmt 10:00 - 18:00
Paz 10:00 - 18:00
```

### Gün Kısaltmaları
- Pzt / Pazartesi / Mon
- Sal / Salı / Sali / Tue  
- Çar / Çarşamba / Carsamba / Wed
- Per / Perşembe / Persembe / Thu
- Cum / Cuma / Fri
- Cmt / Cumartesi / Sat
- Paz / Pazar / Sun

### İzin Tatil Anahtar Kelimeleri
- OFF, İZİN, IZIN, BOŞ, BOS, TATİL, RAPOR

## Gelecek Özellikler

- Google Gemini API entegrasyonu ile akıllı planlama
- Çoklu hafta desteği
- Excel/CSV dosya import/export
- Veritabanı kayıt sistemi
- Kullanıcı profilleri

## Lisans

MIT License
