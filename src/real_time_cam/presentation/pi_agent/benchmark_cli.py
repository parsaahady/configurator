"""CLI entrypoint to benchmark x264enc vs v4l2h264enc on Raspberry Pi 4."""

import argparse
import asyncio
from pathlib import Path
from typing import Final

from real_time_cam.application.encoder_benchmark import (
    BenchmarkDependencies,
    BenchmarkRunOptions,
    EncoderBenchmarkService,
    format_benchmark_markdown_report,
)
from real_time_cam.domain.constants import DEFAULT_CAMERA_DEVICE_PATH
from real_time_cam.infrastructure.encoders.registry import (
    create_default_encoder_registry,
)
from real_time_cam.infrastructure.gstreamer.pipeline_builder import GstPipelineBuilder
from real_time_cam.infrastructure.gstreamer.subprocess_runner import (
    spawn_gst_subprocess,
)
from real_time_cam.infrastructure.system.pi_metrics import LinuxSystemMetricsReader

DEFAULT_REPORT_PATH: Final[Path] = Path("benchmarks/latest_pi4_report.md")
DEFAULT_CLI_DURATION_S: Final[float] = 10.0


def build_benchmark_arg_parser() -> argparse.ArgumentParser:
    """Create CLI argument parser for the Raspberry Pi encoder benchmark."""
    parser = argparse.ArgumentParser(
        description="Benchmark x264enc vs v4l2h264enc on Arducam B0495 (/dev/video1)."
    )
    parser.add_argument(
        "--device",
        default=DEFAULT_CAMERA_DEVICE_PATH,
        help="V4L2 camera device node (default: /dev/video1).",
    )
    parser.add_argument(
        "--duration-s",
        type=float,
        default=DEFAULT_CLI_DURATION_S,
        help="Measurement duration in seconds per configuration (default: 10).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_REPORT_PATH,
        help="Path to write Markdown report.",
    )
    return parser


async def run_benchmark_cli_async(args: argparse.Namespace) -> str:
    """Execute the 4-way benchmark matrix and write the Markdown report."""
    registry = create_default_encoder_registry()
    deps = BenchmarkDependencies(
        encoder_lookup=registry,
        pipeline_builder=GstPipelineBuilder(registry=registry),
        metrics_reader=LinuxSystemMetricsReader(),
        spawner=spawn_gst_subprocess,
    )
    service = EncoderBenchmarkService(deps=deps)
    options = BenchmarkRunOptions(
        device_path=args.device,
        duration_s=args.duration_s,
    )
    results = await service.run_full_matrix(options=options)
    report_markdown = format_benchmark_markdown_report(results)
    output_path: Path = args.output
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(report_markdown, encoding="utf-8")
    return report_markdown


def main(argv: list[str] | None = None) -> int:
    """CLI main entry point for ``xerox-cam-benchmark``."""
    parser = build_benchmark_arg_parser()
    parsed_args = parser.parse_args(argv)
    report = asyncio.run(run_benchmark_cli_async(parsed_args))
    print(report)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
