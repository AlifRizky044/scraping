import os
import time
import hmac

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.responses import JSONResponse
from dotenv import load_dotenv

# Load environment variables from local .env for local/dev runs.
load_dotenv()

from config.redis import redis_client
from main import chat as process_chat
from main import get_runtime_status

AUTH_REQUIRED = os.getenv("AUTH_REQUIRED", "true").lower() == "true"
API_KEY = os.getenv("API_KEY", "")
RATE_LIMIT_PER_MINUTE = int(os.getenv("RATE_LIMIT_PER_MINUTE", "60"))
MAX_REQUEST_BYTES = int(os.getenv("MAX_REQUEST_BYTES", str(16 * 1024)))
CORS_ALLOW_ORIGINS = [o.strip() for o in os.getenv("CORS_ALLOW_ORIGINS", "*").split(",") if o.strip()]
CORS_ALLOW_METHODS = [m.strip().upper() for m in os.getenv("CORS_ALLOW_METHODS", "*").split(",") if m.strip()]
CORS_ALLOW_HEADERS = [h.strip() for h in os.getenv("CORS_ALLOW_HEADERS", "*").split(",") if h.strip()]
CORS_ALLOW_CREDENTIALS = os.getenv("CORS_ALLOW_CREDENTIALS", "false").lower() == "true"

if AUTH_REQUIRED and not API_KEY:
    raise RuntimeError("AUTH_REQUIRED=true but API_KEY is not set")


app = FastAPI(
    title="Chatbot Pajak API",
    version="1.1.0",
    description="API Chatbot Pembayaran Pajak Daerah",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOW_ORIGINS or ["*"],
    allow_methods=CORS_ALLOW_METHODS or ["*"],
    allow_headers=CORS_ALLOW_HEADERS or ["*"],
    allow_credentials=CORS_ALLOW_CREDENTIALS,
)


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=1000)


class ChatResponse(BaseModel):
    reply: str


def _get_client_id(request: Request) -> str:
    key = request.headers.get("x-api-key")
    if key:
        return f"key:{key[:12]}"
    client_host = request.client.host if request.client else "unknown"
    return f"ip:{client_host}"


def _rate_limit_exceeded(client_id: str, limit_per_minute: int) -> bool:
    now_window = int(time.time() // 60)
    key = f"chatbot:ratelimit:{client_id}:{now_window}"

    try:
        count = redis_client.incr(key)
        if count == 1:
            redis_client.expire(key, 65)
        return count > limit_per_minute
    except Exception:
        # Fail-open for temporary Redis issues on rate-limit path to avoid full outage.
        return False


@app.middleware("http")
async def security_middleware(request: Request, call_next):
    path = request.url.path

    if path in {"/healthz", "/readyz"}:
        return await call_next(request)
    if request.method == "OPTIONS":
        return await call_next(request)

    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request body too large"})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid Content-Length header"})

    if AUTH_REQUIRED:
        incoming = request.headers.get("x-api-key")
        if not incoming or not hmac.compare_digest(incoming, API_KEY):
            return JSONResponse(status_code=401, content={"detail": "Unauthorized"})

    client_id = _get_client_id(request)
    if _rate_limit_exceeded(client_id, RATE_LIMIT_PER_MINUTE):
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})

    return await call_next(request)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/readyz")
def readyz():
    status = get_runtime_status()
    ready = status["model_ready"] and (status["redis_ok"] or status["allow_inmemory_fallback"])
    if not ready:
        raise HTTPException(status_code=503, detail=status)
    return {"status": "ready", **status}


@app.post("/chat", response_model=ChatResponse)
def chat_api(payload: ChatRequest):
    try:
        reply = process_chat(payload.user_id, payload.message)
        return {"reply": reply}
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal server error") from exc
