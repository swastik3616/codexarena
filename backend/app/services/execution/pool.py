from __future__ import annotations

import asyncio
from typing import Any, Dict

import docker


LANGUAGE_IMAGES: Dict[str, str] = {
    "python": "python:3.11-slim",
    "javascript": "node:20-slim",
    "typescript": "node:20-slim",
    "java": "openjdk:17-slim",
    "cpp": "gcc:12",
    "c": "gcc:12",
    "go": "golang:1.21",
    "rust": "rust:1.75-slim",
    "ruby": "ruby:3.2-slim",
    "php": "php:8.3-cli",
    "swift": "swift:5.9",
    "kotlin": "openjdk:17-slim",
    "scala": "openjdk:17-slim",
    "bash": "bash:5.2",
    "r": "r-base:4.3.2",
    "dart": "dart:stable",
    "perl": "perl:5.38",
    "haskell": "haskell:9.6.3",
}

class ContainerPool:
    def __init__(self, language: str, pool_size: int = 3):
        self.language = language
        self.pool_size = pool_size
        self._client = None
        self._idle_queue: asyncio.Queue[Any] = asyncio.Queue()
        self._started = False
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        async with self._lock:
            if self._started:
                return
            self._started = True

            # Pre-warm containers.
            for _ in range(self.pool_size):
                container = await self._create_container()
                await self._idle_queue.put(container)

    async def get_idle(self) -> Any:
        if not self._started:
            await self.start()

        try:
            return await asyncio.wait_for(self._idle_queue.get(), timeout=30)
        except asyncio.TimeoutError as e:
            raise TimeoutError("No idle containers available within 30 seconds") from e

    async def release(self, container: Any) -> None:
        """
        Marks container idle:
        - wipes /tmp contents
        - returns to idle queue for reuse
        """

        try:
            # /tmp is writable via tmpfs mount.
            container.exec_run("rm -rf /tmp/* || true")
        except Exception:
            # If wiping fails, safest behavior is to discard and replace.
            await self._discard_and_replace(container)
            return

        await self._idle_queue.put(container)

    async def recycle_on_timeout(self, container: Any) -> None:
        """
        On hard timeout we MUST NOT reuse this container.
        Kill + stop, then recreate and put a fresh container back to idle pool.
        """

        await self._discard_and_replace(container)

    async def _discard_and_replace(self, container: Any) -> None:
        try:
            container.kill()
        except Exception:
            pass
        try:
            container.stop()
        except Exception:
            pass

        # Always create a fresh warm container.
        new_container = await self._create_container()
        await self._idle_queue.put(new_container)

    async def _create_container(self) -> Any:
        """
        Creates ONE container with all the required security flags.
        """

        language_images = LANGUAGE_IMAGES
        if self.language not in language_images:
            raise ValueError(f"Unsupported language: {self.language}")

        image = language_images[self.language]

        # Start with a long-running no-op process so we can exec into it.
        command = ["sh", "-c", "while true; do sleep 3600; done"]

        def _create() -> Any:
            if self._client is None:
                self._client = docker.from_env()
            return self._client.containers.run(
                image=image,
                command=command,
                detach=True,
                network_disabled=True,
                cap_drop=["ALL"],
                security_opt=["no-new-privileges:true", "seccomp=unconfined"],
                read_only=True,
                tmpfs={"/tmp": "size=50m,exec"},
                mem_limit="128m",
                cpu_period=100000,
                cpu_quota=50000,
                pids_limit=50,
                user="1000:1000",
                ulimits=[{"name": "nofile", "soft": 64, "hard": 64}],
            )

        container = await asyncio.to_thread(_create)

        # Ensure /tmp is writable by the requested user.
        def _chown_tmp() -> None:
            try:
                container.exec_run("mkdir -p /tmp/submission && chmod 1777 /tmp && chown 1000:1000 /tmp || true")
            except Exception:
                pass

        await asyncio.to_thread(_chown_tmp)

        return container


LANGUAGE_POOLS: dict[str, ContainerPool] = {
    "python": ContainerPool("python", 3),
    "javascript": ContainerPool("javascript", 3),
    "typescript": ContainerPool("typescript", 2),
    "java": ContainerPool("java", 2),
    "cpp": ContainerPool("cpp", 2),
    "c": ContainerPool("c", 2),
    "go": ContainerPool("go", 2),
    "rust": ContainerPool("rust", 2),
    "ruby": ContainerPool("ruby", 2),
    "php": ContainerPool("php", 2),
    "swift": ContainerPool("swift", 2),
    "kotlin": ContainerPool("kotlin", 2),
    "scala": ContainerPool("scala", 2),
    "bash": ContainerPool("bash", 2),
    "r": ContainerPool("r", 2),
    "dart": ContainerPool("dart", 2),
    "perl": ContainerPool("perl", 2),
    "haskell": ContainerPool("haskell", 2),
}


async def start_all_pools() -> None:
    """
    Start all configured language pools at service startup.

    In environments where Docker or specific language images are unavailable,
    failures are swallowed to keep API startup resilient.
    """

    tasks: list[asyncio.Task[Any]] = []
    for pool in LANGUAGE_POOLS.values():
        tasks.append(asyncio.create_task(pool.start()))
    results = await asyncio.gather(*tasks, return_exceptions=True)
    _ = results


