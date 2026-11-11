"""Unit tests for Raspberry Pi benchmark and RTSP push CLI entrypoints."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from real_time_cam.domain.entities import EncoderBenchmarkResult, EncoderKind
from real_time_cam.presentation.pi_agent import benchmark_cli, push_cli


def test_push_cli_dry_run_prints_pipeline_without_spawning(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify --dry-run validates inputs and prints the shell command without exec."""
    exit_code = push_cli.main(
        [
            "--mediamtx-host",
            "192.168.50.10",
            "--resolution",
            "1920x1200",
            "--fps-hz",
            "30",
            "--bitrate-kbps",
            "3500",
            "--encoder",
            "software_x264",
            "--dry-run",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "rtsp://192.168.50.10:8554/cam" in captured.out
    assert "width=1920,height=1200" in captured.out
    assert "bitrate=3500" in captured.out


def test_push_cli_invokes_subprocess_and_handles_keyboard_interrupt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify push_cli delegates to subprocess.run and exits cleanly on Ctrl+C."""
    mock_run = MagicMock(
        return_value=subprocess.CompletedProcess(args=[], returncode=0)
    )
    monkeypatch.setattr(push_cli.subprocess, "run", mock_run)

    assert push_cli.main(["--mediamtx-host", "laptop.local"]) == 0
    mock_run.assert_called_once()

    monkeypatch.setattr(
        push_cli.subprocess,
        "run",
        MagicMock(side_effect=KeyboardInterrupt),
    )
    assert push_cli.main(["--mediamtx-host", "laptop.local"]) == 0


def test_benchmark_cli_writes_markdown_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify benchmark_cli runs matrix and writes Markdown report file."""
    fake_results = (
        EncoderBenchmarkResult(
            resolution_label="960x600",
            encoder_kind=EncoderKind.SOFTWARE_X264,
            is_stable=True,
            mean_cpu_percent=11.5,
            peak_temp_celsius=52.0,
            achieved_fps_hz=30.0,
            startup_latency_ms=420.0,
            note="OK",
        ),
    )

    async def fake_run_full_matrix(
        _self: object,
        options: object,
    ) -> tuple[EncoderBenchmarkResult, ...]:
        assert options is not None
        return fake_results

    monkeypatch.setattr(
        benchmark_cli.EncoderBenchmarkService,
        "run_full_matrix",
        fake_run_full_matrix,
    )
    report_path = tmp_path / "reports" / "pi4.md"
    exit_code = benchmark_cli.main(
        ["--device", "/dev/video1", "--duration-s", "1", "--output", str(report_path)]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert report_path.exists()
    assert "960x600" in report_path.read_text(encoding="utf-8")
    assert "Recommended Default Encoder" in captured.out
