import os
import time
import threading
from contextlib import contextmanager


# Reduce concurrency to avoid yfinance/Yahoo rate limits on shared hosting (Render)
YFINANCE_MAX_CONCURRENCY = max(1, int(os.getenv("YFINANCE_MAX_CONCURRENCY", "2")))
HTTP_MAX_CONCURRENCY = max(1, int(os.getenv("HTTP_MAX_CONCURRENCY", "6")))

_YFINANCE_SEMAPHORE = threading.BoundedSemaphore(YFINANCE_MAX_CONCURRENCY)
_HTTP_SEMAPHORE = threading.BoundedSemaphore(HTTP_MAX_CONCURRENCY)

# Rate limit: minimum interval between yfinance calls (seconds)
_YF_MIN_INTERVAL = float(os.getenv("YFINANCE_MIN_INTERVAL", "0.5"))
_yf_last_call = 0.0
_yf_rate_lock = threading.Lock()


@contextmanager
def limit_yfinance():
    """Acquire semaphore + enforce minimum interval between calls."""
    global _yf_last_call
    _YFINANCE_SEMAPHORE.acquire()
    try:
        # Enforce rate limit
        with _yf_rate_lock:
            now = time.time()
            elapsed = now - _yf_last_call
            if elapsed < _YF_MIN_INTERVAL:
                time.sleep(_YF_MIN_INTERVAL - elapsed)
            _yf_last_call = time.time()
        yield
    finally:
        _YFINANCE_SEMAPHORE.release()


@contextmanager
def limit_http():
    _HTTP_SEMAPHORE.acquire()
    try:
        yield
    finally:
        _HTTP_SEMAPHORE.release()
