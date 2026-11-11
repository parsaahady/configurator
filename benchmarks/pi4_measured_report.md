# Raspberry Pi 4 (XeroxUAV) — Measured H.264 Encoder Benchmark

- **Host:** `xerox@XeroxUAV` (Raspberry Pi 4, `Debian GNU/Linux 13 (trixie)`, `aarch64`, `Python 3.13.5`)
- **Camera:** Arducam B0495 USB 3.0 Global Shutter (`/dev/video1`, raw `YUY2` on blue USB 3.0 port)
- **GStreamer:** `1.26.2`
- **Target Bitrate / Rate:** `2000 kbps` @ `30 Hz` (`12 s` per configuration)

| Resolution | Encoder | Stable | FPS (Hz) | CPU (%) | Peak Temp (°C) | First Metrics (ms) | Note |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | :--- |
| `960x600` | `software_x264` | PASS | 30.4 | 15.4 | 40.4 | 1703 | OK |
| `960x600` | `hardware_v4l2` | PASS | 30.6 | 3.9 | 40.9 | 1526 | OK |
| `1920x1200` | `software_x264` | PASS | 30.4 | 35.2 | 43.8 | 1520 | OK |
| `1920x1200` | `hardware_v4l2` | FAIL | 0.0 | 3.8 | 41.9 | 0 | `v4l2h264enc0: Failed to process frame.` (BCM2711 1080p height ceiling) |

## Engineering Decision

- **Default encoder:** `software_x264` (`x264enc` with `tune=zerolatency`, `speed-preset=ultrafast`, `sliced-threads=true`, `profile=baseline`) at `960x600 @ 30 Hz`, `2000 kbps`.
- **Rationale:** `software_x264` succeeds cleanly at both `960x600` (`15.4%` CPU) and `1920x1200` (`35.2%` CPU), whereas Raspberry Pi 4's `bcm2835-codec` hardware block (`hardware_v4l2`) hits its physical `1080 px` height limit at `1920x1200`. Meanwhile, `hardware_v4l2` remains available as a swappable strategy whenever ultra-low CPU (`3.9%`) at `960x600` is prioritized alongside heavy onboard AI workloads.
