import logging
import threading

import requests

from .config import settings

log = logging.getLogger(__name__)
_timer: threading.Timer | None = None
_lock = threading.Lock()
_token: str | None = None  # JWT 缓存（有效期 30 天）


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


def _login() -> str | None:
    """登录 Swing Music 获取 JWT"""
    global _token
    try:
        resp = requests.post(
            f"{settings.SWING_URL}/auth/login",
            json={"username": settings.SWING_USERNAME, "password": settings.SWING_PASSWORD},
            timeout=10,
        )
        if resp.status_code == 200:
            _token = resp.json().get("accesstoken")
            log.info("swing login ok")
        else:
            _token = None
            log.warning("swing login failed: %s", resp.status_code)
    except requests.RequestException as e:
        _token = None
        log.warning("swing login error: %s", e)
    return _token


def _post_scan(url: str, token: str | None) -> int | None:
    headers = {"Authorization": f"Bearer {token}"} if token else {}
    try:
        code = requests.post(url, json={"full_scan": False}, headers=headers, timeout=15).status_code
        if code == 405:
            # 旧版 Swing 只提供 GET /trigger-scan
            code = requests.get(url, headers=headers, timeout=15).status_code
        return code
    except requests.RequestException as e:
        log.warning("swing scan failed: %s", e)
        return None


def _do_scan():
    url = f"{settings.SWING_URL}{settings.SWING_SCAN_PATH}"
    need_auth = bool(settings.SWING_USERNAME)

    token = None
    if need_auth:
        token = _token or _login()
        if not token:
            return

    code = _post_scan(url, token)
    if code == 401 and need_auth:
        # token 失效，重新登录后重试一次
        token = _login()
        if token:
            code = _post_scan(url, token)

    log.info("swing scan: %s -> %s", url, code)
