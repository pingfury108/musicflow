import logging

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import music
from .config import settings
from .store import SerialWorker, TTLCache, TaskStore
from .swing import trigger_scan

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)

app = FastAPI(title="MusicFlow")
cache = TTLCache(ttl=settings.CACHE_TTL)
tasks = TaskStore()


def run_task(item):
    """串行 worker 的任务处理器"""
    task_id, raw = item
    tasks.update(task_id, status="downloading")
    try:
        path = music.download(raw)
        tasks.update(task_id, status="done", file=path)
        trigger_scan()
    except Exception as e:
        tasks.update(task_id, status="failed", error=str(e))


dl_queue = SerialWorker(run_task)

app.mount("/static", StaticFiles(directory="static"), name="static")


class SearchRequest(BaseModel):
    keyword: str


class DownloadRequest(BaseModel):
    token: str


@app.get("/")
def index():
    return FileResponse("static/index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "sources": settings.MUSIC_SOURCES,
        "swing": bool(settings.SWING_URL),
    }


@app.post("/api/search")
def api_search(req: SearchRequest):
    keyword = req.keyword.strip()
    if not keyword:
        raise HTTPException(400, "keyword required")
    data = []
    for token, view, raw in music.search(keyword):
        cache.put(token, raw)
        data.append(view)
    return {"data": data}


@app.post("/api/download")
def api_download(req: DownloadRequest):
    raw = cache.get(req.token)
    if not raw:
        raise HTTPException(404, "下载链接已过期，请重新搜索")
    task_id = tasks.create(raw.get("song_name") or "unknown")
    dl_queue.submit((task_id, raw))
    return {"task_id": task_id}


@app.get("/api/tasks")
def list_tasks():
    return {"data": tasks.list()}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    task = tasks.get(task_id)
    if not task:
        raise HTTPException(404, "task not found")
    return task
