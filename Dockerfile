# Mulai dari image resmi Python yang ringan
FROM python:3.11-slim

# Install system dependency yang dibutuhkan oleh Celery Beat
RUN apt-get update && apt-get install -y libgdbm-dev && rm -rf /var/lib/apt/lists/*

# Buat user dan grup non-root untuk keamanan
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Atur direktori kerja di dalam kontainer
WORKDIR /app

# Salin file requirements.txt terlebih dahulu untuk caching dependensi
COPY requirements.txt .

# Install semua dependensi
RUN pip install --no-cache-dir -r requirements.txt

# Salin sisa kode aplikasi ke dalam direktori kerja
# dan ubah kepemilikan ke user non-root
COPY . .
RUN chown -R appuser:appuser /app

# Ganti ke user non-root
USER appuser

# Perintah default (bisa di-override oleh docker-compose)
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]