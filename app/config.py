import os

DEFAULT_SOURCES = [
    "MiguMusicClient",
    "NeteaseMusicClient",
    "QQMusicClient",
    "KuwoMusicClient",
    "QianqianMusicClient",
]


def _split_env(name: str, default: list[str]) -> list[str]:
    raw = os.getenv(name, "").strip()
    return [s.strip() for s in raw.split(",") if s.strip()] or default


class Settings:
    MUSIC_DIR: str = os.getenv("MUSIC_DIR", "./music")
    SWING_URL: str = os.getenv("SWING_URL", "").rstrip("/")  # 为空则不触发扫描
    SWING_SCAN_PATH: str = os.getenv("SWING_SCAN_PATH", "/notsettings/trigger-scan")
    # Swing 开启用户系统后需要登录；留空则无鉴权调用
    SWING_USERNAME: str = os.getenv("SWING_USERNAME", "")
    SWING_PASSWORD: str = os.getenv("SWING_PASSWORD", "")
    SEARCH_SIZE: int = int(os.getenv("SEARCH_SIZE", "10"))  # 每源结果数
    CACHE_TTL: int = int(os.getenv("CACHE_TTL", "1800"))  # 搜索结果缓存秒数
    SCAN_DEBOUNCE: float = float(os.getenv("SCAN_DEBOUNCE", "5"))  # 扫描去抖秒数
    MUSIC_SOURCES: list[str] = _split_env("MUSIC_SOURCES", DEFAULT_SOURCES)


settings = Settings()
