"""Unit tests for Raspberry Pi Linux CPU load and temperature readers (mocked fs)."""

from pathlib import Path

from real_time_cam.infrastructure.system.pi_metrics import (
    CpuTickSnapshot,
    LinuxSystemMetricsReader,
    compute_cpu_load_percent,
    parse_proc_stat_cpu_line,
)

EXPECTED_CPU_LOAD_PERCENT: float = 50.0
EXPECTED_TEMP_CELSIUS: float = 54.3


def test_parse_proc_stat_cpu_line_and_load_calculation() -> None:
    """Verify /proc/stat parsing and delta CPU % math."""
    sample_one = "intr 123\ncpu  100 0 50 850 0 0 0 0\ncpu0 25 0 10 215\n"
    sample_two = "cpu  160 0 90 950 0 0 0 0\n"

    snap_one = parse_proc_stat_cpu_line(sample_one)
    snap_two = parse_proc_stat_cpu_line(sample_two)

    assert snap_one == CpuTickSnapshot(total_ticks=1000, idle_ticks=850)
    assert snap_two == CpuTickSnapshot(total_ticks=1200, idle_ticks=950)
    assert compute_cpu_load_percent(snap_one, snap_two) == EXPECTED_CPU_LOAD_PERCENT


def test_parse_proc_stat_handles_short_and_missing_lines() -> None:
    """Verify malformed /proc/stat inputs return None or 0.0 safely."""
    assert parse_proc_stat_cpu_line("cpu 1 2\n") is None
    assert parse_proc_stat_cpu_line("mem 100 200\n") is None
    snap = CpuTickSnapshot(total_ticks=500, idle_ticks=400)
    assert compute_cpu_load_percent(snap, snap) == 0.0
    short_snap = parse_proc_stat_cpu_line("cpu 10 20 30 40\n")
    assert short_snap == CpuTickSnapshot(total_ticks=100, idle_ticks=40)


def test_linux_system_metrics_reader_with_mock_files(tmp_path: Path) -> None:
    """Verify reader parses temp/CPU and handles missing or corrupt files."""
    stat_file = tmp_path / "stat"
    temp_file = tmp_path / "temp"
    stat_file.write_text("cpu  200 10 40 750 0 0 0 0\n", encoding="utf-8")
    temp_file.write_text("54321\n", encoding="utf-8")

    reader = LinuxSystemMetricsReader(
        proc_stat_path=stat_file,
        thermal_temp_path=temp_file,
    )
    assert reader.read_cpu_snapshot() == CpuTickSnapshot(
        total_ticks=1000, idle_ticks=750
    )
    assert reader.read_cpu_temp_celsius() == EXPECTED_TEMP_CELSIUS

    stat_file.write_text("cpu bad_int 1 2 3 4\n", encoding="utf-8")
    temp_file.write_text("not_a_number\n", encoding="utf-8")
    assert reader.read_cpu_snapshot() is None
    assert reader.read_cpu_temp_celsius() is None

    missing_reader = LinuxSystemMetricsReader(
        proc_stat_path=tmp_path / "missing_stat",
        thermal_temp_path=tmp_path / "missing_temp",
    )
    assert missing_reader.read_cpu_snapshot() is None
    assert missing_reader.read_cpu_temp_celsius() is None
