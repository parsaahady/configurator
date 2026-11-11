# Raspberry Pi 4 Camera H.264 Encoder Benchmarks

Run the automated 4-way benchmark (`960x600` & `1920x1200` × `software_x264` & `hardware_v4l2`) directly on the Raspberry Pi 4 (`Debian 13 trixie`, `aarch64`) with the Arducam B0495 attached at `/dev/video1`:

> **Safety Reminder:** Ensure propellers are physically **OFF** before powering the companion computer on the airframe.

```bash
uv sync --dev
uv run xerox-cam-benchmark --device /dev/video1 --duration-s 15 --output benchmarks/latest_pi4_report.md
```

The command measures achieved FPS (`fpsdisplaysink`), system-wide CPU utilization (`/proc/stat`), SoC temperature (`/sys/class/thermal/thermal_zone0/temp`), and time-to-first-metrics without network interference (`video-sink=fakesink`).
