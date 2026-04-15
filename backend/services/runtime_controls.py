import os
import threading
from contextlib import contextmanager


YFINANCE_MAX_CONCURRENCY = max(1, int(os.getenv("YFINANCE_MAX_CONCURRENCY", "4")))
HTTP_MAX_CONCURRENCY = max(1, int(os.getenv("HTTP_MAX_CONCURRENCY", "8")))

_YFINANCE_SEMAPHORE = threading.BoundedSemaphore(YFINANCE_MAX_CONCURRENCY)
_HTTP_SEMAPHORE = threading.BoundedSemaphore(HTTP_MAX_CONCURRENCY)


@contextmanager
def limit_yfinance():
    _YFINANCE_SEMAPHORE.acquire()
    try:
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
