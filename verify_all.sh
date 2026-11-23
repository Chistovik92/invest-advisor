#!/usr/bin/env bash
set -euo pipefail

echo "=== 1. Проверка синтаксиса Python ==="
python3 -m compileall backend/app backend/tests

echo "=== 2. Запуск pytest (unit, API, проверка всех 18 платформ) ==="
PYTHONPATH=backend pytest backend/tests -v --tb=short

echo "=== 3. Проверка конфигурации Docker Compose ==="
docker compose config -q

if [ -d "client-kmp" ] && command -v gradle >/dev/null 2>&1; then
  echo "=== 4. Запуск тестов и компиляции Kotlin Multiplatform ==="
  (cd client-kmp && gradle desktopTest compileKotlinDesktop)
fi

echo "=== Все проверки успешно пройдены ==="
