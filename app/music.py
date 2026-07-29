import logging
import os
import threading
import uuid

from musicdl import musicdl
from musicdl.modules.utils import SongInfo

from .config import settings

log = logging.getLogger(__name__)

_lock = threading.Lock()
_client: musicdl.MusicClient | None = None


def get_client() -> musicdl.MusicClient:
    """懒加载单例，避免启动时初始化所有源"""
    global _client
    if _client is None:
        with _lock:
            if _client is None:
                init_cfg = {
                    s: {
                        "work_dir": settings.MUSIC_DIR,
                        "search_size_per_source": settings.SEARCH_SIZE,
                        "disable_print": True,
                    }
                    for s in settings.MUSIC_SOURCES
                }
                _client = musicdl.MusicClient(
                    music_sources=settings.MUSIC_SOURCES,
                    init_music_clients_cfg=init_cfg,
                )
    return _client


def search(keyword: str) -> list[tuple[str, dict, dict]]:
    """多源搜索，返回 [(token, 前端展示dict, SongInfo序列化dict)]"""
    results = get_client().search(keyword=keyword) or {}
    # musicdl 会在 work_dir 留 search_results.pkl，顺手清掉
    try:
        os.remove(os.path.join(settings.MUSIC_DIR, "search_results.pkl"))
    except OSError:
        pass
    items = []
    for source, songs in results.items():
        for song in songs:
            token = uuid.uuid4().hex
            view = {
                "token": token,
                "title": song.song_name,
                "artist": song.singers,
                "album": song.album,
                "source": source.removesuffix("MusicClient"),
                "ext": (song.ext or "").removeprefix("."),
                "size": song.file_size,
                "duration": song.duration,
                "cover_url": song.cover_url,
            }
            items.append((token, view, song.todict()))
    return items


def download(song_dict: dict) -> str:
    """下载单曲，musicdl 自动写入 ID3/封面/歌词，返回文件路径"""
    song_info = SongInfo.fromdict(song_dict)
    song_info.work_dir = settings.MUSIC_DIR
    song_info._save_path = None  # 让 save_path 按新 work_dir 重新计算
    downloaded = get_client().download(song_infos=[song_info])
    if not downloaded:
        raise RuntimeError(f"下载失败: {song_dict.get('song_name')}")
    path = downloaded[0].save_path
    log.info("downloaded: %s", path)
    return path
