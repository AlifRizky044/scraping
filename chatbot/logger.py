import csv
import hashlib
import os
import re
from datetime import datetime, timezone
from pathlib import Path

LOG_FILE = os.getenv("CHATBOT_LOG_FILE", "logs/conversation_logs.csv")
MAX_LOG_BYTES = int(os.getenv("CHATBOT_LOG_MAX_BYTES", str(5 * 1024 * 1024)))
BACKUP_COUNT = int(os.getenv("CHATBOT_LOG_BACKUP_COUNT", "10"))
RETENTION_DAYS = int(os.getenv("CHATBOT_LOG_RETENTION_DAYS", "30"))
HASH_SALT = os.getenv("CHATBOT_LOG_HASH_SALT", "replace-this-salt-in-production")

_NIK_NPWPD_RE = re.compile(r"\b\d{16}\b")
_NOP_RE = re.compile(r"\b\d{18}\b")
_NIB_RE = re.compile(r"\b\d{13}\b")


def _redact_pii(text: str) -> str:
    if not text:
        return text
    text = _NOP_RE.sub("[REDACTED_NOP]", text)
    text = _NIK_NPWPD_RE.sub("[REDACTED_ID16]", text)
    text = _NIB_RE.sub("[REDACTED_NIB]", text)
    return text


def _hash_user_id(user_id: str) -> str:
    value = f"{HASH_SALT}:{user_id}".encode("utf-8")
    return hashlib.sha256(value).hexdigest()[:16]


def _rotate_if_needed(path: Path) -> None:
    if not path.exists() or path.stat().st_size < MAX_LOG_BYTES:
        return
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rotated_path = path.with_name(f"{path.name}.{ts}")
    path.rename(rotated_path)

    rotated = sorted(path.parent.glob(f"{path.name}.*"), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in rotated[BACKUP_COUNT:]:
        old.unlink(missing_ok=True)

    cutoff = datetime.now(timezone.utc).timestamp() - (RETENTION_DAYS * 86400)
    for old in path.parent.glob(f"{path.name}.*"):
        if old.stat().st_mtime < cutoff:
            old.unlink(missing_ok=True)


def init_logger():
    log_path = Path(LOG_FILE)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    _rotate_if_needed(log_path)

    if not log_path.exists():
        with log_path.open(mode="a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["timestamp", "user_id", "message", "intent", "score", "response"])


def log_conversation(user_id, message, intent, score, response):
    init_logger()
    log_path = Path(LOG_FILE)
    with log_path.open(mode="a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(
            [
                datetime.now(timezone.utc).isoformat(),
                _hash_user_id(str(user_id)),
                _redact_pii(str(message)),
                intent,
                score,
                _redact_pii(str(response)),
            ]
        )
