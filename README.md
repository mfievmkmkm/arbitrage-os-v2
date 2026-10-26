# ARBITRAGE OS v2 · OBSERVE

Новый независимый Python 3.12 сканер A1: **только Bybit/BingX USDT linear perpetual**.
Приватных биржевых API, ордеров, PAPER и LIVE в этом релизе нет.

Фактическая готовность и ограничения: [docs/STATUS.md](docs/STATUS.md).

## Запуск

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -e ".[dev]"
.venv\Scripts\python -m apps.scanner.main --seconds 180 --report reports/observation.json
```

Без `--seconds` процесс работает до SIGINT/SIGTERM. Без PostgreSQL это явно диагностический,
недолговечный журнал. Для круглосуточного запуска используйте постоянный сервер и Postgres:

```powershell
Copy-Item .env.example .env
# В .env задайте самостоятельно случайные POSTGRES_PASSWORD и CONTROL_TOKEN.
# Пароль для compose DSN должен быть URL-safe, например длинная hex-строка.
docker compose --env-file .env up -d --build
```

Никакие биржевые ключи не нужны. Telegram необязателен: задайте `TELEGRAM_BOT_TOKEN`,
`TELEGRAM_OWNER_ID` (ID личного чата владельца) в защищённом окружении, затем:

```powershell
docker compose --env-file .env --profile telegram up -d --build
```

Боту отправьте `/start`. Кнопки: Сканер, Сырые, Проверенные, Ожидают данных,
Почему отказ, История, Диагностика, Настройки, Назад. Команды `/size 100`, `/spread 0.1`,
`/net 0.5` принимают своё число; хранение настроек требует Postgres.
Telegram не управляет торговлей и не меняет OBSERVE.

## API

По умолчанию compose публикует API только на localhost:8080.

| Endpoint | Содержание |
|---|---|
| /health | Liveness и отказ критической задачи |
| /ready | 503 без двух свежих feed и durable journal |
| /status | Реальное покрытие, latency, отказы, provider errors, очередь, CPU/RSS |
| /markets | Полный принятый каталог и нормализованные ограничения |
| /quotes | Последние bid/ask, объёмы, timestamps |
| /signals?stage=VERIFIED | Актуальные кандидаты, raw/VWAP/NET, причины |
| /history | Последние 50 журнальных событий |
| /metrics | Prometheus text |
| PATCH /settings | Разрешённые числовые настройки, Bearer CONTROL_TOKEN |

Внешняя публикация API требует защищённого reverse proxy; secrets не передаются через UI.
`/health` не доказывает доступность бирж — для этого `/status` и `/ready`.

## Проверка

```powershell
python -m ruff check .
python -m pytest --cov=core --cov=adapters --cov=apps --cov=infrastructure --cov-report=term-missing
python scripts/benchmark.py
python scripts/probe_depth.py
```

`benchmark.py` — синтетический поток, не реальные сделки. `probe_depth.py` — фактический
read-only WS стакан BingX BTC-USDT. Postgres integration требует `TEST_DATABASE_URL`;
если его нет, тест честно skipped. CI описан для Windows/Linux и отдельного Postgres.
До публикации GitHub Actions ещё не запускались.

## Идентичность и исполнимость

Равенство base даёт только RAW. Реестр `configs/identity.json` исходно пуст:
нет непроверенных автоматических подтверждений идентичности. Формат — в
`configs/examples/identity.example.json`. Не переносите шаблонные значения как доказательство.
Для каждого binding нужны доказательства underlying, единиц и settlement.

VERIFIED требует identity, совместимых спецификаций, свежих двухсторонних quotes,
глубины на общий симметричный qty, минимумов, комиссии и funding interval/rate.
VERIFIED здесь означает аналитически проверенный сценарий, **не разрешение торговли**:
`route_tradeability=MODE_OBSERVE`, executable всегда 0.

NET немедленного round-trip отличается от гипотезы будущего сжатия.
Funding по текущему rate и оценённым будущим settlement — прогноз.
Public fee не выдаётся за персональную. BingX limited-depth ts — время создания сообщения,
не гарантированный возраст исходного matching-engine стакана.

## Архитектура

`adapters/cex` → bounded events → indexed in-memory state → raw candidates → depth shortlist
→ evaluator → Postgres batch journal → API → отдельный Telegram.

Hot quotes не записываются каждый тик в БД. История содержит начало/пик/периодические снимки,
изменения причин отказа и завершение спреда. Каталоги обновляются каждый час;
недоступная площадка повторяется через 30 секунд с независимым feed второй площадки.
Автоматической подмены бирж нет. См. [DECISIONS](docs/DECISIONS.md) и [SOURCES](docs/SOURCES.md).

Внешние расширения DEX/spot/transfer/executor не реализованы; нормализованные модели и
границы адаптеров позволяют добавить их позже отдельными этапами.

## Публикация в новом GitHub

Доступный GitHub connector не умеет создавать repository. Владелец создаёт пустой private
`arbitrage-os-v2` через https://github.com/new — без README, .gitignore и license.
Не используйте старый arbitrage-engine. После создания передайте URL для публикации
подготовленного проекта через подключённый GitHub.

В архиве также есть переносимый `arbitrage-os-v2.bundle` с локальной историей. При желании
можно клонировать его, добавить remote нового repo и выполнить `git push -u origin main`.

## Дальнейшая приёмка

Нужны доступный официальный Bybit public API в разрешённом окружении, доказательный registry,
прогон с PostgreSQL и Telegram владельца, оба WS потока, длительное observation ≥24 ч,
реальные кандидаты и отказы. До этого этап 1A не считается принятым.
