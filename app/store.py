import queue
import threading
import time
import uuid


class TTLCache:
    """搜索结果缓存：token -> SongInfo dict"""

    def __init__(self, ttl: int):
        self.ttl = ttl
        self._data: dict[str, tuple[float, dict]] = {}
        self._lock = threading.Lock()

    def put(self, key: str, value: dict):
        with self._lock:
            self._gc()
            self._data[key] = (time.time(), value)

    def get(self, key: str) -> dict | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            ts, value = item
            if time.time() - ts > self.ttl:
                self._data.pop(key, None)
                return None
            return value

    def _gc(self):
        now = time.time()
        for k in [k for k, (ts, _) in self._data.items() if now - ts > self.ttl]:
            self._data.pop(k, None)


class SerialWorker:
    """串行任务队列：单 worker 线程逐个处理，避免并发下载"""

    def __init__(self, handler):
        self._handler = handler
        self._q: queue.Queue = queue.Queue()
        self._started = False
        self._lock = threading.Lock()

    def submit(self, item):
        with self._lock:
            if not self._started:
                threading.Thread(target=self._worker, daemon=True).start()
                self._started = True
        self._q.put(item)

    def _worker(self):
        while True:
            item = self._q.get()
            try:
                self._handler(item)
            except Exception:
                pass  # 状态由 handler 内部维护
            finally:
                self._q.task_done()


class TaskStore:
    """下载任务状态表（内存实现，重启清空）"""

    def __init__(self):
        self._tasks: dict[str, dict] = {}
        self._lock = threading.Lock()

    def create(self, title: str) -> str:
        task_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._tasks[task_id] = {
                "id": task_id,
                "title": title,
                "status": "queued",
                "file": None,
                "error": None,
                "created_at": time.time(),
            }
        return task_id

    def update(self, task_id: str, **fields):
        with self._lock:
            if task_id in self._tasks:
                self._tasks[task_id].update(fields)

    def get(self, task_id: str) -> dict | None:
        with self._lock:
            return self._tasks.get(task_id)

    def list(self, limit: int = 20) -> list[dict]:
        with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t["created_at"], reverse=True)[:limit]
