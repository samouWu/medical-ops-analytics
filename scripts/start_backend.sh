#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON="${ROOT_DIR}/.venv/bin/python"

if [[ ! -x "${PYTHON}" ]]; then
    echo "未找到 ${PYTHON}，请先创建虚拟环境并安装后端依赖。" >&2
    exit 1
fi

export PYTHONPATH="${ROOT_DIR}/backend${PYTHONPATH:+:${PYTHONPATH}}"
cd "${ROOT_DIR}"
exec "${PYTHON}" -m uvicorn app.main:app --host 127.0.0.1 --port 8765
