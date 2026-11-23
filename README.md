# InvestAdvisor — мультиброкерный ребалансировщик портфеля РФ

Единый помощник для ведения портфеля (ИИС + внешние брокеры) на российском рынке:
сбор позиций из всех доступных платформ, расчёт точных лотов для ребалансировки,
контроль маржинального долга, «подушки» TMON и сигналы на выход из «хвостов».

Репозиторий: https://github.com/Chistovik92/invest-advisor

> 📖 **Подробная инструкция** (установка, настройка токенов, загрузка отчётов,
> QUIK-мост, API, Telegram-бот, частые проблемы) — в файле
> [ИНСТРУКЦИЯ.md](ИНСТРУКЦИЯ.md).

## Возможности

- **18 платформ** под одним API: Т-Инвестиции, БКС, Финам, Алор (REST API) и
  14 брокеров без открытого REST-API через импорт отчётов (HTML/XLSX/CSV) или
  синхронизацию из QUIK (Сбер, ВТБ, Альфа, Газпромбанк, ПСБ, РСХБ, Райффайзен,
  Совкомбанк, Ренессанс, Уралсиб, АТОН, Цифра Брокер, МКБ, Финуслуги).
- **Ребалансировка**: жадный подбор целых лотов под целевые веса классов активов
  и отдельных инструментов, с учётом заморозки покупок и погашения маржи в первую очередь.
- **Telegram-бот** (`/status`, `/buy`, `/tails`) и плановые проверки каждые 30 минут.
- **Кроссплатформенный клиент** (Kotlin Multiplatform + Compose Multiplatform M3E):
  Android, Windows (MSI/EXE), Linux (DEB/RPM/AppImage — Fedora, Simply Linux,
  РЕД ОС, Ubuntu, Debian).

## Структура проекта

```
invest-advisor/
├── backend/                 # FastAPI + асинхронные провайдеры брокеров
│   ├── app/
│   │   ├── main.py          # REST API и старт планировщика/бота
│   │   ├── config.py        # настройки из .env + YAML-конфиг портфеля
│   │   ├── models.py        # Pydantic-модели
│   │   ├── rebalancer.py    # движок ребалансировки
│   │   ├── telegram_bot.py  # aiogram-бот
│   │   └── providers/
│   │       ├── base.py          # абстрактный интерфейс провайдера
│   │       ├── tinvest.py       # Т-Инвестиции (REST)
│   │       ├── bcs.py           # БКС Trade API (REST)
│   │       ├── finam.py         # Финам Trade API (REST)
│   │       ├── alor.py          # Алор OpenAPI (REST)
│   │       ├── native_parsers.py# парсеры родных отчётов (HTML/XLSX/CSV)
│   │       ├── report_import.py # импорт/QUIK-брокеры
│   │       └── registry.py      # реестр всех 18 платформ
│   ├── tests/               # pytest: ребалансер, API, связность, все платформы
│   ├── config.yaml          # целевые веса и «хвосты»
│   ├── requirements.txt
│   └── Dockerfile
├── client-kmp/              # Kotlin Multiplatform + Compose Multiplatform
│   └── composeApp/
│       ├── src/commonMain/  # общий UI (M3E) и API-клиент
│       ├── src/androidMain/ # Android (MainActivity)
│       ├── src/desktopMain/ # Windows/Linux (Main)
│       └── src/commonTest/  # тесты моделей
├── tools/quik_bridge.lua    # Lua-скрипт QUIK для синхронизации портфеля
├── .github/workflows/       # CI (тесты) и сборка инсталляторов
├── docker-compose.yml
├── verify_all.sh
└── .env.example
```

## Быстрый старт (backend)

```bash
cd backend
pip install -r requirements.txt --extra-index-url https://opensource.tbank.ru/api/v4/projects/238/packages/pypi/simple
cp ../.env.example .env        # заполните TINVEST_TOKEN и пр.
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8085
```

Либо через Docker:

```bash
cp .env.example .env           # заполните токены
docker compose up --build
```

Документация API — по адресу http://localhost:8085/docs.

## Настройка конфигурации портфеля

Целевые веса, список инструментов и «хвосты» на выход задаются в `backend/config.yaml`
(также доступны через `GET/POST /api/config`). Основные секции:

- `portfolio_targets.asset_classes` — веса классов (акции / длинные ОФЗ / короткие и флоатеры / валютные).
- `portfolio_targets.stocks` — ядро акций с целевыми долями (флаг `freeze_buy` запрещает докупку).
- `portfolio_targets.bonds_to_buy` — облигации для докупки.
- `portfolio_targets.exit_candidates` — «хвосты» с целевым PnL для выхода.

## Импорт отчётов и QUIK-мост

Для брокеров без REST-API отчёт загружается через `POST /api/import-report/{broker_id}`
(принимает `.html`, `.xlsx`, `.csv`). Либо запустите `tools/quik_bridge.lua` внутри QUIK —
он раз в минуту шлёт позиции на `POST /api/quik-bridge/{broker_id}`.

## Сборка клиента

```bash
cd client-kmp
gradle assembleRelease          # Android APK
gradle packageMsi packageExe     # Windows
gradle packageDeb packageRpm packageAppImage  # Linux
```

## Полная проверка

```bash
bash verify_all.sh
```

запускает компиляцию, pytest (все 18 платформ) и проверку Docker Compose.
