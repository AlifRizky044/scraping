from fastapi import FastAPI, HTTPException
from main import chat as process_chat
from pydantic import BaseModel

# ======================================================
# INIT APP
# ======================================================
app = FastAPI(
    title="Chatbot Pajak API",
    version="1.0.0",
    description="API Chatbot Pembayaran Pajak Daerah"
)

# ======================================================
# API SCHEMA
# ======================================================
class ChatRequest(BaseModel):
    user_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str

# ======================================================
# API ENDPOINT
# ======================================================
@app.post("/chat", response_model=ChatResponse)
def chat_api(payload: ChatRequest):
    reply = process_chat(payload.user_id, payload.message)
    return {"reply": reply}


#uvicorn api:app --reload
