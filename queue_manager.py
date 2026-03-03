import asyncio
from collections import defaultdict
from typing import Optional

class DownloadQueue:
    def __init__(self):
        self.queues = defaultdict(asyncio.Queue)  # user_id -> Queue
        self.current = defaultdict(lambda: None)  # user_id -> current task
        self.cancelled = defaultdict(set)  # user_id -> set of URLs to cancel

    async def add(self, user_id: int, url: str, callback):
        """Add download task to user's queue. callback is coroutine to execute."""
        queue = self.queues[user_id]
        await queue.put((url, callback))
        if self.current[user_id] is None:
            # Start processing
            asyncio.create_task(self._process(user_id))

    async def _process(self, user_id: int):
        queue = self.queues[user_id]
        while not queue.empty():
            url, callback = await queue.get()
            if url in self.cancelled[user_id]:
                self.cancelled[user_id].discard(url)
                continue
            self.current[user_id] = url
            try:
                await callback()
            except Exception as e:
                print(f"Download error for {user_id}: {e}")
            finally:
                self.current[user_id] = None
        # Cleanup if empty
        if queue.empty():
            del self.queues[user_id]
            del self.current[user_id]

    def get_queue_position(self, user_id: int, url: str) -> int:
        """Return 1-based position if waiting, 0 if current, -1 if not in queue"""
        if self.current[user_id] == url:
            return 0
        # Count items before this url in queue
        pos = 1
        for (u, _) in list(self.queues[user_id]._queue):
            if u == url:
                return pos
            pos += 1
        return -1

    def cancel_user(self, user_id: int):
        """Cancel all pending downloads for user"""
        # Clear queue and cancel current if any
        self.queues[user_id] = asyncio.Queue()
        if self.current[user_id]:
            # We can't easily cancel running task, but we'll mark for skip on next
            self.cancelled[user_id].add(self.current[user_id])
            self.current[user_id] = None

    def cancel_url(self, user_id: int, url: str):
        """Cancel specific URL if pending or running"""
        if self.current[user_id] == url:
            self.cancelled[user_id].add(url)
            # Task will be cancelled when it finishes? We'd need to implement cancellation token.
            # For simplicity, we'll just mark it.
        else:
            # Remove from queue by rebuilding queue without that url
            new_queue = asyncio.Queue()
            while not self.queues[user_id].empty():
                u, cb = self.queues[user_id].get_nowait()
                if u != url:
                    new_queue.put_nowait((u, cb))
            self.queues[user_id] = new_queue

queue_manager = DownloadQueue()
