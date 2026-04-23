from __future__ import annotations

import asyncio
from collections import defaultdict
from typing import Any


class EventBroker:
    def __init__(self) -> None:
        self._queues: dict[str, list[asyncio.Queue[dict[str, Any]]]] = defaultdict(list)

    def subscribe(self, project_id: str) -> asyncio.Queue[dict[str, Any]]:
        queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._queues[project_id].append(queue)
        return queue

    async def publish(self, project_id: str, event: dict[str, Any]) -> None:
        for queue in self._queues.get(project_id, []):
            await queue.put(event)

    def unsubscribe(self, project_id: str, queue: asyncio.Queue[dict[str, Any]]) -> None:
        if queue in self._queues.get(project_id, []):
            self._queues[project_id].remove(queue)
