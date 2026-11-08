# XeroxUAV Real-Time Camera Configurator (`real-time-cam`)

Web-based, sub-second latency camera streaming and live configuration module for the **XeroxUAV** Ground Control Station (`Raspberry Pi 4` → `MediaMTX` → `Browser` via `WebRTC/WHEP`, controlled over `FastAPI` + `WebSocket`).

> **Safety First (The Golden Propeller Rule):** Propellers must remain physically **REMOVED** during all bench setup, software debugging, and laboratory testing.

## Documentation & Step-by-Step Persian Tutorial

- [Project Overview & Architecture (Persian)](docs/00-overview.md)
- [Step 00 — Repository Skeleton & Quality Toolchain (Persian)](docs/steps/00-repo-skeleton.md)

## Quick Developer Checks

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run ty check
uv run pytest
```
