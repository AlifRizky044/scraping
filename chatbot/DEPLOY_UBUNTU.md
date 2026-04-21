# Deploy Chatbot ke Ubuntu (Docker)

Dokumen ini untuk:
- train ulang model di server memakai Docker
- menjalankan API FastAPI dari image Docker

## 1) Prasyarat

- Ubuntu server dengan akses sudo
- Port `8005` dibuka di firewall/security group
- Domain (opsional) jika ingin via Nginx

Install Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

## 2) Upload project ke server

Contoh:

```bash
cd /opt
sudo git clone https://github.com/AlifRizky044/scraping.git
sudo chown -R $USER:$USER /opt/scraping
cd /opt/scraping/chatbot
```

## 3) Siapkan environment

File `.env` ada di folder `chatbot/`. Sesuaikan nilainya:

- `APP_PORT=8005`
- `API_KEY` dengan secret yang kuat (minimal 32 karakter)
- `AUTH_REQUIRED=true`
- `ALLOW_INMEMORY_CONTEXT_FALLBACK=false` (disarankan untuk production)
- Redis server jalan di host Ubuntu (bukan Docker), jadi set:
  - `REDIS_HOST=host.docker.internal`
  - `REDIS_PORT=6379`

Contoh cek cepat:

```bash
cat .env
```

## 4) Build image

Pastikan command dijalankan dari folder `chatbot`:

```bash
sudo docker build -t chatbot-pajak:latest .
```

## 5) Train ulang model dengan Docker (wajib saat dataset/model berubah)

Jalankan training script dalam container one-off, mount source code host ke `/app` supaya output model tersimpan ke folder `models/` di server:

```bash
cd /opt/scraping/chatbot
sudo docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$(pwd):/app" \
  -w /app \
  chatbot-pajak:latest \
  python train_faq.py

sudo docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$(pwd):/app" \
  -w /app \
  chatbot-pajak:latest \
  python train_intent.py
```

Opsional verifikasi model:

```bash
sudo docker run --rm \
  -u "$(id -u):$(id -g)" \
  -v "$(pwd):/app" \
  -w /app \
  chatbot-pajak:latest \
  python verify_models.py
```

## 6) Jalankan container chatbot

Redis dipakai dari host Ubuntu (bukan container), jadi gunakan `--add-host=host.docker.internal:host-gateway`.

```bash
sudo docker run -d \
  --name chatbot-pajak \
  -p 8005:8005 \
  --restart unless-stopped \
  --env-file .env \
  --add-host=host.docker.internal:host-gateway \
  chatbot-pajak:latest
```

## 7) Verifikasi API

```bash
curl -X POST http://127.0.0.1:8005/chat \
  -H "Content-Type: application/json" \
  -H "x-api-key: <API_KEY>" \
  -d '{"user_id":"u1","message":"cara bayar pbb"}'
```

Readiness check:

```bash
curl http://127.0.0.1:8005/healthz
curl -i http://127.0.0.1:8005/readyz
```

Cek log:

```bash
sudo docker logs -f chatbot-pajak
```

## 8) Update aplikasi (dengan retrain)

```bash
cd /opt/scraping
git pull
cd chatbot
sudo docker build -t chatbot-pajak:latest .

# retrain model agar kompatibel dengan dependency di image terbaru
sudo docker run --rm -u "$(id -u):$(id -g)" -v "$(pwd):/app" -w /app chatbot-pajak:latest python train_faq.py
sudo docker run --rm -u "$(id -u):$(id -g)" -v "$(pwd):/app" -w /app chatbot-pajak:latest python train_intent.py

sudo docker rm -f chatbot-pajak
sudo docker run -d \
  --name chatbot-pajak \
  -p 8005:8005 \
  --restart unless-stopped \
  --env-file .env \
  chatbot-pajak:latest
```

## 9) (Opsional) Reverse proxy Nginx

Jika ingin expose via domain `chatbot.domainkamu.com`, proxy ke `127.0.0.1:8005`.

Contoh minimal:

```nginx
server {
    listen 80;
    server_name chatbot.domainkamu.com;

    location / {
        proxy_pass http://127.0.0.1:8005;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
