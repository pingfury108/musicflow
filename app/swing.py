import logging
import threading

import requests

from .config import settings

log = logging.getLogger(__name__)
_timer: threading.Timer | None = None
_lock = threading.Lock()


def trigger_scan():
    """去抖触发：短时间内多次下载只扫描一次"""
    global _timer
    if not settings.SWING_URL:
        return
    with _lock:
        if _timer:
            _timer.cancel()
        _timer = threading.Timer(settings.SCAN_DEBOUNCE, _do_scan)
        _timer.daemon = True
        _timer.start()


def _do_scan():
    url = f"{settings.SWING_URL}{settings.SWING_SCAN_PATH}"
    try:
        resp = requests.post(url, json={"full_scan": False}, timeout=15)
        log.info("swing scan: %s -> %s", url, resp.status_code)
    except requests.RequestException as e:
        log.warning("swing scan failed: %s", e)
