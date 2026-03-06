import csv
import os
from datetime import datetime

LOG_FILE = "logs/conversation_logs.csv"

def init_logger():
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # Create header if file doesn't exist
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "user_id", "message", "intent", "score", "response"])

def log_conversation(user_id, message, intent, score, response):
    init_logger()
    
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            datetime.now().isoformat(),
            user_id,
            message,
            intent,
            score,
            response
        ])
