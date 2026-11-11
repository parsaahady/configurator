"""Linux ``/proc`` and ``/sys`` adapter implementing ``SystemMetricsPort``."""

from pathlib import Path
from typing import Final

from real_time_cam.domain.ports import CpuTickSnapshot

DEFAULT_PROC_STAT_PATH: Final[Path] = Path("/proc/stat")
DEFAULT_THERMAL_TEMP_PATH: Final[Path] = Path("/sys/class/thermal/thermal_zone0/temp")
MILLIDEGREES_PER_CELSIUS: Final[float] = 1000.0
PERCENT_SCALE: Final[float] = 100.0
MIN_CPU_STAT_COLUMNS: Final[int] = 5
IDLE_COLUMN_INDEX: Final[int] = 3
IOWAIT_COLUMN_INDEX: Final[int] = 4


def parse_proc_stat_cpu_line(stat_text: str) -> CpuTickSnapshot | None:
    """Extract aggregate ``total_ticks`` and ``idle_ticks`` from ``/proc/stat`` text."""
    for raw_line in stat_text.splitlines():
        parts = raw_line.split()
        if not parts or parts[0] != "cpu":
            continue
        if len(parts) < MIN_CPU_STAT_COLUMNS:
            return None
        numeric_columns = [int(token) for token in parts[1:]]
        idle_ticks = numeric_columns[IDLE_COLUMN_INDEX] + (
            numeric_columns[IOWAIT_COLUMN_INDEX]
            if len(numeric_columns) > IOWAIT_COLUMN_INDEX
            else 0
        )
        return CpuTickSnapshot(
            total_ticks=sum(numeric_columns),
            idle_ticks=idle_ticks,
        )
    return None


def compute_cpu_load_percent(
    previous: CpuTickSnapshot,
    current: CpuTickSnapshot,
) -> float:
    """Compute system-wide CPU utilization percentage `[0.0, 100.0]` between samples."""
    total_delta = current.total_ticks - previous.total_ticks
    if total_delta <= 0:
        return 0.0
    idle_delta = max(0, current.idle_ticks - previous.idle_ticks)
    busy_ratio = max(0.0, min(1.0, (total_delta - idle_delta) / total_delta))
    return round(busy_ratio * PERCENT_SCALE, 1)


class LinuxSystemMetricsReader:
    """Reads CPU tick snapshots and SoC temperature from Linux virtual filesystems."""

    def __init__(
        self,
        proc_stat_path: Path = DEFAULT_PROC_STAT_PATH,
        thermal_temp_path: Path = DEFAULT_THERMAL_TEMP_PATH,
    ) -> None:
        """Initialize reader with injectable virtual file paths for testing."""
        self._proc_stat_path = proc_stat_path
        self._thermal_temp_path = thermal_temp_path

    def read_cpu_snapshot(self) -> CpuTickSnapshot | None:
        """Read current aggregate CPU tick counters, or ``None`` if unavailable."""
        try:
            stat_text = self._proc_stat_path.read_text(encoding="utf-8")
        except OSError:
            return None
        try:
            return parse_proc_stat_cpu_line(stat_text)
        except ValueError:
            return None

    def read_cpu_temp_celsius(self) -> float | None:
        """Read SoC temperature in degrees Celsius, or ``None`` on non-Pi hosts."""
        try:
            raw_millidegrees = self._thermal_temp_path.read_text(
                encoding="utf-8"
            ).strip()
            return round(int(raw_millidegrees) / MILLIDEGREES_PER_CELSIUS, 1)
        except (OSError, ValueError):
            return None
