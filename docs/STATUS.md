# ARBITRAGE OS v2 · статус на 26.10.2026

**Версия 0.1.0 · OBSERVE · LIVE OFF · Stage 0/1A: код реализован, приёмка НЕ завершена.**

GitHub: NOT_PUBLISHED — инструмент подключённого GitHub не предоставляет создание репозитория.
Deploy ID: NOT_DEPLOYED. Круглосуточный сервис не запускался; временные observation-процессы остановлены.
Локальная история поставляется в git bundle. Старый arbitrage-engine не изменялся.

## Реально реализовано

- Native public Bybit/BingX adapters; полный каталог, Bybit pagination/cursor loop guard,
  фильтрация типа/settlement/status/launch/maintenance; регулярный refresh.
- Только 2 разрешённых venue, OBSERVE-only config; подписки WS всех активных контрактов,
  шардирование, GZIP и Ping/Pong, heartbeat, jitter/backoff, независимые соединения.
- Индексы base для неподтверждённых RAW и asset_id для подтверждённых underlying;
  два направления; quote TTL/skew; доказательный identity gate без ticker-only VERIFIED.
- Native 50-level shortlist, Bybit snapshot/delta, BingX limited snapshots;
  отдельный parser BingX incremental с fail-closed на gap.
- Общий симметричный quantity grid, min qty/notional, notional cap, VWAP четырёх сторон,
  четыре комиссии, текущий round-trip, гипотеза NET при target basis, funding signs/settlements.
- История состояний, пика спреда, отказов и истечения; bounded queue/batch Postgres journal;
  явный nondurable режим диагностики без БД, сохранение/восстановление числовых настроек.
- HTTP API, health/readiness, Prometheus metrics, CPU/RSS, различение event-processing и
  detection latency; независимый owner-only русский Telegram, кнопки/Назад/ручные числа.
- Docker/compose, Postgres migration, Linux/Windows CI definition, unit/replay, HTTP/WS integration,
  backpressure, outage isolation, disconnect invalidation, cold funding metadata test, synthetic load.

## Фактическое наблюдение

Последнее окно **180 s**, закончено 26.10.2026; источник результатов —
[evidence/observation-final.json](evidence/observation-final.json), включая полный список instrument IDs,
constraints, bid/ask и timestamps. Ранее было отдельное окно 90 s.

| Показатель | Bybit | BingX |
|---|---:|---:|
| Обнаружено записей | неизвестно: API недоступен | 1294 |
| Активно после фильтров | неизвестно | 1234 |
| Исключено status/launch/maintenance/типом | неизвестно | 60 |
| Свежие WS quotes на конце окна | 0 | 1234 / 1234 |
| WS соединения на конце окна | 0 | 31 |
| Подтверждённые identity bindings | 0 | 0 |
| Статус | UNAVAILABLE / NON_JSON_RESPONSE | PUBLIC_READY |

Bybit вернул HTTP 200 с HTML «Site Unavailable» вместо JSON. Это не пустой каталог
и не доказательство отсутствия рынков. Причина ограничения доступа этим ответом не установлена;
ограничения не обходились, другая биржа не использовалась.

BingX: **507451 quote events**, 1044 Ping/Pong, queue_depth=0 на конце окна,
зафиксированных dropped events/reconnects в успешном broad feed нет.
Шесть ошибок каталога относятся к независимым попыткам получить недоступный Bybit.

- p50 внутренней обработки события: **0.0558 ms**; p95 **0.2559 ms**.
- Это окно последних 20000 событий и метрика WS receive → обработанное событие.
- **Реальный time-to-detect/p95 межбиржевого кандидата: НЕ ИЗМЕРЕН**, 0 сравнений.
- Индикатор возраста BingX quotes p95: **659 ms** по source timestamps/локальным часам;
  не гарантирует отсутствие upstream задержки и clock offset.
- RSS на конце: **52486144 bytes ≈ 50.05 MiB**.
- CPU process time: **55.52 s / 180 s** наблюдения; это не CPU p95 и не 24-часовой профиль.

Реальные RAW/VERIFIED/EXECUTABLE: **0 / 0 / 0**. PAPER входы/выходы **0/0**.
Не было межбиржевых маршрутов, поэтому нет фиктивного NET или экономических отказов.
1234 BingX инструментам в этом прогоне не найден контрагент: каталог Bybit недоступен.

Счётчик активных BingX изменился с 1233 в первом окне до 1234 во втором; это независимые
реальные снимки каталога, не фиксированное обещание количества контрактов.

## Стакан и нагрузка — отдельные доказательства

[evidence/depth-probe.json](evidence/depth-probe.json): пять реальных 50-level снимков
BingX BTC-USDT, без ордеров. Это однобиржевая проверка протокола, не арбитражная возможность.
Первый probe incrDepth был отклонён внутренним лимитом BOOK_TOO_LARGE; активный адаптер
переведён на ограниченную documented depth50 snapshot тему. См. DECISIONS.md.

[evidence/load.json](evidence/load.json): **SYNTHETIC_LOAD_NOT_REAL_MARKET**,
1200 общих искусственных активов, 40000 событий и оба направления. Скорость и p95
даны в JSON для последней версии. Синтетические цены/asset IDs не используются в production.
Это не гарантированная производительность внешнего провайдера и не реальные сделки.

## Проверки

[evidence/tests.txt](evidence/tests.txt): **47 passed, 1 skipped**, Python 3.12/Linux.
Общее покрытие проверенного кода **70%**, evaluator **97%**, identity **100%**.
Ruff: pass. Пропущен только настоящий Postgres restart integration: TEST_DATABASE_URL не задан.
Локальный настоящий HTTP/WS сервер проверяет GZIP/Ping, native subscribe, глубину,
HTTP 200 HTML, 429, API TTL/auth, отказ провайдера, инвалидирование очереди при disconnect.

**GitHub CI Linux/Windows: NOT_RUN** — workflow подготовлен, но репозиторий ещё не создан.
Docker build/compose и реальный PostgreSQL здесь **NOT_RUN**: Docker/сервер Postgres отсутствуют.
Telegram render проверен тестом; реальный бот **NOT_CONNECTED**: токен/owner ID не заданы.
У окна observation `journal.durable=false`: это не доказательство долговечной истории.

## Что ещё блокирует приёмку 0/1A

1. Новый пустой private GitHub repo `arbitrage-os-v2`, публикация локальных commits, зелёные Linux/Windows CI.
2. Официальный public Bybit API в разрешённом рабочем окружении и проверка обоих реальных потоков.
3. Доказательный cross-venue identity registry. Сейчас он **пуст**: никакие 1234 ticker-only совпадения
   не будут автоматически объявлены проверенными. Нужна проверка underlying/specification на двух каталогах.
4. Реальный Postgres, restart/persistence integration и compose smoke; реальный Telegram владельца.
5. Настоящие межбиржевые RAW/VERIFIED snapshots, реальные rejection funnel и measured time-to-detect.
6. Расширенная проверка reconnect/resubscribe и листинга/делистинга на двух реальных venues,
   подтверждение subscription budgets. Длительное окно ≥24 h и resource/profile отчёт ещё не выполнены.
7. Числовые настройки уже меняются через UI; динамическое включение/выключение venues без перезапуска,
   более полная пагинация UI/сортировки и автоматическая верификация identity — следующие доработки.

**Следующая конкретная задача:** опубликовать новый repo, запустить этот OBSERVE-код с PostgreSQL
в окружении с доступом к обеим официальным API, завершить identity registry и собрать двухбиржевое
наблюдение. До этого не начинать Stage 1B, PAPER AUTO, DEX/transfer/LIVE.

## Действие владельца и секреты

Создать https://github.com/new → Repository name `arbitrage-os-v2`, Private,
не добавлять README/.gitignore/license. Передать только ссылку репозитория.
Эта ручная операция нужна из-за отсутствия API создания repo, а не из-за торгового разрешения.

Для будущего запуска владелец задаёт в защищённом окружении DATABASE_URL (либо
POSTGRES_PASSWORD для compose), CONTROL_TOKEN, необязательно TELEGRAM_BOT_TOKEN и
TELEGRAM_OWNER_ID. В чат и GitHub секреты не передавать. Биржевые ключи не нужны.

Режим LIVE: **OFF**. Нет кода отправки торговых ордеров.
