# Chatbot Runbook

## 1) Setup environment (sekali saja)
Jalankan dari root project:

```bash
cd /Users/nevv/Documents/scraping
python3 -m venv venv
source venv/bin/activate
pip install -U pip
pip install pandas joblib scikit-learn Sastrawi rapidfuzz fastapi uvicorn redis pydantic
```

## 2) Training model
Jalankan dari folder `chatbot`:

```bash
cd /Users/nevv/Documents/scraping/chatbot
/Users/nevv/Documents/scraping/venv/bin/python train_faq.py
/Users/nevv/Documents/scraping/venv/bin/python train_intent.py
```

Output model akan update di folder `models/`.

## 3) Verifikasi cepat model
```bash
/Users/nevv/Documents/scraping/venv/bin/python verify_models.py
/Users/nevv/Documents/scraping/venv/bin/python test_all_intents.py
```

## 4) Jalankan chatbot (CLI)
```bash
/Users/nevv/Documents/scraping/venv/bin/python main.py
```

Ketik `exit` atau `quit` untuk berhenti.

## 5) Jalankan API chatbot
```bash
cd /Users/nevv/Documents/scraping/chatbot
/Users/nevv/Documents/scraping/venv/bin/python -m uvicorn api:app --reload --host 0.0.0.0 --port 8000
```

Endpoint: `POST /chat`

Contoh body:
```json
{
  "user_id": "u1",
  "message": "mau bayar pbb"
}
```

## 6) Test flow utama
```bash
/Users/nevv/Documents/scraping/venv/bin/python -m unittest -q test_normalization.py
/Users/nevv/Documents/scraping/venv/bin/python -m unittest -q test_pbb_flow.py
/Users/nevv/Documents/scraping/venv/bin/python -m unittest -q test_non_pbb_flow.py
/Users/nevv/Documents/scraping/venv/bin/python test_logging.py
```
