# Python 3.10-slim tabanlı image
FROM python:3.10-slim

# Çalışma dizinini ayarla
WORKDIR /app

# Sistem paketleri (yalnizca health check icin curl)
# OCR sunucuda calismiyor: birincil OCR uzak HuggingFace Space'te,
# fallback ise tarayicida tesseract.js ile calisiyor.
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Port expose
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Python bağımlılıklarını kopyala ve kur
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Uygulama dosyalarını kopyala
COPY . .

# Root olmayan kullanıcı
RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

# Uygulamayı başlat
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
