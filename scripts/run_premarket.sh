#!/usr/bin/env bash
set -euo pipefail
python -m scanner.run_scan premarket "$@"
