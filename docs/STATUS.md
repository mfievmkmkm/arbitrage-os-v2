# ARBITRAGE OS v2 · 27.10.2026 · требования 1.3

**Продолжение существующего проекта. OBSERVE. LIVE OFF. Gate 1A НЕ ПРИНЯТ. Полный Stage 1 НЕ ГОТОВ.**

## Последний результат: GitHub runner · 27.10.2026

Запущено агентом, без ручного Run workflow владельцем. Коммит запуска `1e31fae`,
[наблюдение 40390030000](https://github.com/mfievmkmkm/arbitrage-os-v2/actions/runs/40390030000).
Workflow автоматически запускает ограниченный OBSERVE при обновлении собственного файла;
manual workflow_dispatch сохранён, права contents:read, default 180 s.

**Bybit REST: точная наблюдаемая причина отказа этого runner — блокировка страны IP.**
HTTP 403 CloudFront прямо сообщает, что доступ из страны заблокирован. Это другая наблюдаемая
среда по сравнению с предыдущей HTML-заглушкой через перехватываемый TLS внутри Work.
Выводы из одной среды не выдаются за доказательство поведения другой.

**Bybit public WS доступен:** независимый probe получил реальный `tickers.BTCUSDT` snapshot.
Он не использован как вымышленный полный каталог. Основной scanner без реального REST каталога
остаётся UNAVAILABLE по Bybit; число совместимых пар определить невозможно.

BingX: 1294 discovered, 1227 active/fresh, 67 exclusions, **521102 quote events**, 1069 Ping/Pong,
31 WS connections, quote age p95 739 ms. Обработка p50 0.0706 ms / p95 **0.1686 ms**,
последние 20000 событий; queue depth 0, RSS 62263296 bytes (~59.38 MiB).
Межбиржевой p95 НЕ ИЗМЕРЕН. RAW/VERIFIED/EXECUTABLE=0/0/0; PAPER=0/0, LIVE OFF.
Это не доказательство отсутствия рыночных возможностей.

Полный JSON каталог/quotes хранится в Actions artifact `public-observation-evidence`, ID 12682816097.
В Git сохранены status, network diagnostics, все 1227 instrument IDs и sample quotes:
[evidence/github-40390030000-summary.json](evidence/github-40390030000-summary.json).
История этого observation NON-DURABLE: persisted=0, PostgreSQL в этом job не подключался.

CI Windows/Linux/secrets/lint/Postgres/Docker прошёл для `a125d4b` (40388444274) и `1e31fae`
(40390030410); в Docker log подтверждены postgres_restart_persistence=true и journal_durable=true.
Это доказательство CI smoke, не круглосуточного production deployment.

По факту ответа добавлен `PUBLIC_API_REGION_RESTRICTED` с HTTP metadata/hash и русским объяснением.
Обычный 403 без явного сообщения о стране остаётся HTTP_403. Два отдельных HTTP regression tests
проверяют различие. Убрана неверная универсальная формулировка про TLS interception из диагностического
скрипта: TLS/географию выводим только из наблюдаемых доказательств.

**Gate 1A не принят:** нужен разрешённый runtime с доступными REST и WS обеих бирж,
доказательный identity registry и ≥24 h observation. Платный deployment не создавался,
альтернативные домены/прокси/третьи CEX не использовались. Stage 1B остаётся обязательным.

Следующий шаг: проверка доступности официальных endpoints в согласованной разрешённой среде
будущего постоянного размещения. Нельзя исправить региональный запрет снятием экономических
проверок или фиктивным каталогом.

## GitHub и сохранность истории

Repository: https://github.com/mfievmkmkm/arbitrage-os-v2 — PUBLIC, код опубликован владельцем обычным push.
GitHub connector показывает push/admin permissions. Прямой `git push -u origin main` из командной
среды завершился `could not read Username for 'https://github.com': terminal prompts disabled`.

**Первичная публикация выполнена, исходные SHA сохранены.** Ограничение connector при первоначальном переносе: он не позволяет указать исходные
commit metadata и сохранить их SHA; пересоздавать историю ради публикации запрещено владельцем.
Коммиты `dc7a92e1fb23a9007b35b30c9bdd5e1b24f881b5` и
`f8db3be24a9b4ee2050ea8c8573404e2c3159ff8` не изменены и остаются предками новых коммитов.
Force push, amend, rebase, orphan не выполнялись. Новый репозиторий/проект не создавался.

Архив содержит полный git bundle и исходники. Точные Windows CMD команды — README и
`scripts/publish_windows.cmd`. GitHub CI run 40388444274 прошёл: Windows/Linux, secrets/lint, PostgreSQL и Docker/compose restart persistence. Повторный CI 40390030410 на коммите 1e31fae также прошёл.

## Проверка секретов

Проверены reachable Git history и индекс новой версии: `.env`/private key files не отслеживаются,
токены/API-ключи/приватные ключи по проверенным шаблонам не найдены. Единственные credential-like
строки старого кода — `${POSTGRES_PASSWORD}` и известный непроизводственный CI fixture `ci-only`.
Они рассмотрены явно; blanket исключений для папок нет. Сканер проверяет high-confidence patterns
и sensitive filenames, не заявляет математической гарантии обнаружить любую строку-секрет.
Результаты: `evidence/v1_3/secret-index.json`, `secret-history.json`.

## Почему не работает Bybit — доказательства и предел вывода

Полный протокол: `evidence/v1_3/network-diagnostics.json`.

- Документированные `https://api.bybit.com/v5/market/time` и `/v5/market/instruments-info`
  возвращают HTTP 200, content-type=text/html, 195 bytes вместо биржевого JSON.
- Контрольный несуществующий `/v5/not-a-real-endpoint` возвращает ту же страницу с тем же SHA256:
  `5b131ca14aa96311d3432b0062c7443d3b0e6346ec279bd376a75f0a76bcd5d7`.
- `wss://stream.bybit.com/v5/public/linear` вместо WS upgrade 101 получает HTTP 200.
- TLS issuer наблюдаемого соединения к api.bybit.com: **OpenAI, LLC / openai.com**.
  Следовательно, TLS перехватывается управляемым шлюзом этой среды.
- Независимые urllib и aiohttp воспроизводят ошибку без кода сканера. Endpoint соответствует
  официальным V5 Integration Guidance/Instrument docs.

**Установлено:** это не ошибка JSON parser сканера и не неправильный путь V5; в перехваченном
сетевом пути приходит общая не-API страница. **Не установлено:** генерирует её сам шлюз или его
upstream и является ли upstream причина региональным запретом. Без origin/gateway logs утверждать
точную первопричину нельзя. Не выдаём сам факт OpenAI TLS interception за доказательство,
что HTML обязательно сгенерирован именно этим шлюзом.

Официальные docs указывают для части ограниченных IP 403; здесь наблюдается 200 HTML,
поэтому произвольное утверждение «регион запрещён» не делается.
Источники: https://bybit-exchange.github.io/docs/v5/guide,
https://bybit-exchange.github.io/docs/v5/market/instrument.

**Ошибка не устранена изменением сетевой политики:** таких прав/логов нет. Добавлены конкретный
`PUBLIC_API_HTML_UNAVAILABLE`, безопасные HTTP metadata и hash. Альтернативные домены, proxy rotation,
обход ограничений, подмена каталога или третья CEX не использовались.

## Новые изменения кода

- При disconnect/backpressure/пустой котировке старый VERIFIED отзывается немедленно,
  API перестаёт его отдавать, причина сохраняется в истории. Отложенные до disconnect события
  не оживляют старый поток. Очередь корректно освобождает unfinished counters на early exits.
- Сигнал не живёт дольше quotes/books TTL. Отдельные проверки empty/crossed/invalid/duplicate levels,
  quote skew, book skew, неверного времени, out-of-order пакетов.
- Bybit delta только реального top-of-book обновляет quote; mark/funding/heartbeat не освежают её.
  Unchanged fields восстанавливаются из непрерывного потока. Regression timestamps отклоняется
  до изменения cache. Глубина использует matching-engine `cts`, сохраняет `u` и cross `seq`.
- Отдельные проверки на **$50/$100/$250** плюс выбранный основной размер. Лимит проскальзывания
  `MAX_SLIPPAGE_BPS`, общий quantity grid, max symmetric qty и размер с VWAP в пределах лимита.
  Параметр — только аналитический, ордеров нет.
- Диагностика clock offset/RTT/uncertainty; ожидание shared REST limiter не выдаётся за network RTT.
  Source timestamps скрытно не исправляются. Сомнительный offset не считается точной синхронизацией.
- Метрики compatible pairs, directed routes, outbound public paths. Только Bybit/BingX endpoints.
- Журнал дополнен boot configuration и provider health; nondurable memory не выдаётся за Postgres:
  отдельный persisted=0 без DB. Причины отказов по-русски в API/Telegram.
- Единое MASTER_SPEC v1.3, requirements_v1_3.md, CLOUD_RUNBOOK. Полный Stage 1 обязательно содержит
  1B: Spot Bybit/BingX + DEX BNB Chain/Base/Arbitrum (factory discovery, pool updates, identity,
  size-aware buy/sell execution quotes, gas, token restrictions). DEX не исключён и не начат раньше Gate 1A.

## Реальное наблюдение — отдельно от тестов

`evidence/v1_3/observation-120s.json` — 120 секунд промежуточной версии:
BingX 1294 discovered, 1227 active/fresh, 316371 quote events, p95 обработки 0.2719 ms.

`evidence/v1_3/observation-final.json` — повторный 60-секундный smoke финальной версии:

| Метрика | Bybit | BingX |
|---|---:|---:|
| Обнаружено записей каталога | НЕ ПОЛУЧЕНО | 1294 |
| Активные контракты после фильтров | НЕИЗВЕСТНО | 1226 |
| Исключено status/type/maintenance/launch | НЕИЗВЕСТНО | 68 |
| Свежие котировки в конце | 0 | 1226 / 1226 |
| Соединения broad WS | 0 | 31 |
| Возраст quotes p95 | не измерен | 715 ms |
| Состояние | UNAVAILABLE | PUBLIC_READY |

Quote events **139212**, Ping/Pong **297**, event-processing p50 **0.0564 ms**, p95 **0.2345 ms**,
окно последних 20000 событий. Queue depth=0, зафиксированных dropped events нет.
RSS **52473856 bytes ≈50.04 MiB**, CPU process **14.84 s / 60 s**.
Clock midpoint BingX **+2.09 ms ±105.80 ms**, RTT **211.60 ms**; общий вызов с ожиданием limiter
около 5.15 s показан отдельно. Это не точность matching engine и не гарантированный upstream age.

**Межбиржевой p50/p95: НЕ ИЗМЕРЕН.** Каталог Bybit отсутствует, реальные совместимые пары
определить нельзя. `compatible_pairs=0` означает 0 подтверждённых пар в текущем состоянии,
не утверждение, что общих контрактов у бирж нет. Реестр identity по-прежнему пуст:
не заполнялся догадками по одним тикерам при отсутствии второго реального каталога.

RAW/VERIFIED/EXECUTABLE **0/0/0**, PAPER входы/выходы **0/0**, DEX pools=0.
Причина нуля — отсутствие Bybit и отсутствие подтверждённых маршрутов, а не доказанное
отсутствие прибыльных ситуаций на рынке. В финальном окне журнал содержит 2 отзыва провайдера
PUBLIC_API_HTML_UNAVAILABLE и boot config. Без Postgres **persisted=0** — durability не доказана.

Количество активных BingX менялось между окнами: это реальные снимки, не фиксированное покрытие.
Все instrument IDs, bid/ask и source timestamps находятся в JSON evidence.

## Проверки и облачная подготовка

`evidence/v1_3/tests.txt`: **62 passed, 1 skipped**, Linux Python 3.12, покрытие **72%**,
route evaluator **97%**. Ruff и git diff --check — pass. Тестируется реальный local HTTP/WS server,
GZIP/Ping, disconnect → invalidate → reconnect → повторный subscribe → новый quote,
разные размеры, TTL, crossing/empty/несинхронность и timestamp regressions.
Это тестовый сервер/replay, а не работа Bybit.

| Проверка | Фактический статус |
|---|---|
| Linux tests/lint | PASS локально |
| Windows tests / GitHub Actions | PASS: run 40388444274 и повтор 40390030410 |
| Реальный PostgreSQL restart test | PASS в GitHub CI; локальный тест без TEST_DATABASE_URL пропущен |
| Docker build / compose | PASS в GitHub CI: сохранность записи после restart подтверждена |
| Установка локального Postgres | Не выполнена: apt завершился ошибками setgroups/setegid/seteuid sandbox |
| Postgres migration / DB restart smoke CI | PASS в GitHub CI |
| Real Telegram | NOT_CONNECTED: token/owner ID не заданы |
| Cloud deployment | NOT_DEPLOYED, платные сервисы не создавались |
| Наблюдение ≥24 h на двух биржах | НЕ ВЫПОЛНЕНО |

CI теперь содержит Linux/Windows, secrets history scan, реальный Postgres service и отдельный
Docker/compose job с проверкой сохранённого INTEGRATION_TEST event после перезапуска контейнеров.
Manual read-only workflow сохраняет independent network diagnostics и market observation artifact.
Ephemeral CI credentials генерируются и маскируются; не являются торговыми ключами.

## Следующий конкретный шаг

Опубликовать поставленный bundle обычным Windows Git push (команды в README), сохранив исходные
SHA. Затем проверить запустившийся CI и независимый public observation workflow. Для принятия
Gate 1A нужны разрешённая среда с реально доступными Bybit REST+WS, заполнение evidence identity
registry, durable Postgres, оба реальных потока и ≥24 h статистики. После 1A — обязательный 1B.
До этих проверок нет оснований объявлять сканер готовым или переходить к торговле.

Биржевые API-ключи, seed, подпись кошелька и live orders **не используются**. LIVE: **OFF**.
