import os

try:
    import redis
except Exception:  # pragma: no cover - fallback for local test envs without redis package
    redis = None


class _FallbackRedisClient:
    def __init__(self):
        self._data = {}

    def get(self, key):
        return self._data.get(key)

    def set(self, key, value, ex=None):
        self._data[key] = value
        return True

    def delete(self, key):
        self._data.pop(key, None)
        return 1

    def incr(self, key):
        value = int(self._data.get(key, 0)) + 1
        self._data[key] = value
        return value

    def expire(self, key, seconds):
        return True

    def ping(self):
        return True


if redis is None:
    redis_client = _FallbackRedisClient()
else:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=int(os.getenv("REDIS_DB", "0")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True,
        socket_connect_timeout=float(os.getenv("REDIS_CONNECT_TIMEOUT_SEC", "1.0")),
        socket_timeout=float(os.getenv("REDIS_SOCKET_TIMEOUT_SEC", "1.0")),
    )
