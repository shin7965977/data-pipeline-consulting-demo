#!/usr/bin/env bash
set -e

echo "[Docker Entrypoint] Starting Platzi Pipeline Runner..."
exec python pipeline_runner.py "$@"
