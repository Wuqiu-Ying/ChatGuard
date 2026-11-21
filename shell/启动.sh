#!/usr/bin/env bash
cd "$(dirname "$0")" || exit 1
PY=""
for c in python3 python; do
  if command -v "$c" >/dev/null 2>&1; then PY="$c"; break; fi
done
if [ -z "$PY" ]; then
  echo "没有找到 Python 3，请先安装：https://www.python.org/downloads/"
  exit 1
fi
echo "正在启动 ChatGuard，浏览器会自动打开..."
exec "$PY" api.py --open
