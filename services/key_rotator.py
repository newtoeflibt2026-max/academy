import random, time, threading
from config import settings

class KeyRotator:
    def __init__(self, keys: list[str], rpm: int = 15):
        self.keys = keys
        self.rpm = rpm
        self.usage = {k: {"count": 0, "reset_at": time.time() + 60} for k in keys}
        self.lock = threading.Lock()

    def get_key(self) -> str:
        with self.lock:
            now = time.time()
            for k in self.keys:
                if self.usage[k]["reset_at"] <= now:
                    self.usage[k] = {"count": 0, "reset_at": now + 60}
                if self.usage[k]["count"] < self.rpm:
                    self.usage[k]["count"] += 1
                    return k
            # كل المفاتيح مستنفذة — نستنى
            time.sleep(1)
            return self.get_key()

writing_keys = KeyRotator(settings.GEMINI_WRITING_KEYS) if settings.GEMINI_WRITING_KEYS else None
speaking_keys = KeyRotator(settings.GEMINI_SPEAKING_KEYS) if settings.GEMINI_SPEAKING_KEYS else None
