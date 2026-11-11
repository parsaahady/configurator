"""Async OS subprocess adapter for GStreamer (`gst-launch-1.0`)."""

import asyncio
import signal

from real_time_cam.domain.ports import AsyncProcessHandle


class AsyncioSubprocessHandle:
    """Concrete ``AsyncProcessHandle`` wrapping ``asyncio.subprocess.Process``."""

    def __init__(self, proc: asyncio.subprocess.Process) -> None:
        """Wrap an active asyncio subprocess."""
        self._proc = proc

    @property
    def returncode(self) -> int | None:
        """Return exit status, or ``None`` while still running."""
        return self._proc.returncode

    async def read_line(self) -> str | None:
        """Read next UTF-8 output line, or ``None`` at EOF."""
        if self._proc.stdout is None:
            return None
        raw = await self._proc.stdout.readline()
        if not raw:
            return None
        return raw.decode("utf-8", errors="replace")

    def send_sigint(self) -> None:
        """Send ``SIGINT`` so ``gst-launch-1.0 -e`` flushes EOS cleanly."""
        if self._proc.returncode is None:
            self._proc.send_signal(signal.SIGINT)

    def kill_process(self) -> None:
        """Send ``SIGKILL`` to terminate an unresponsive process."""
        if self._proc.returncode is None:
            self._proc.kill()

    async def wait_exit(self) -> int:
        """Await process exit and return exit status."""
        return await self._proc.wait()


async def spawn_gst_subprocess(command: tuple[str, ...]) -> AsyncProcessHandle:
    """Spawn ``gst-launch-1.0`` in a separate OS process without invoking a shell."""
    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    return AsyncioSubprocessHandle(proc)
