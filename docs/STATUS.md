# ARBITRAGE OS v2 · 27.10.2026 · требования 1.3

**Продолжение существующего проекта. OBSERVE. LIVE OFF. Gate 1A НЕ ПРИНЯТ. Полный Stage 1 НЕ ГОТОВ.**

## Экстренная пауза записи · 27.10.2026

По поручению владельца scanner остановлен без удаления данных: Railway deployment 19effc0f SUCCESS, временный HTTP процесс отвечает PAUSED; прежний scanner deployment завершён. Предыдущая попытка redeploy повторно запустила сканер: исправлена новым применением конфигурации. Для возобновления нужно вернуть startCommand `python -m apps.scanner.main` и применить конфигурацию после исправлений и проверок. Railway DISK_USAGE_GB=0.610025472 при объёме нового тома 500 MB: метрика может включать предыдущий том, подтверждения нет; не считать её объёмом или свободным местом нового тома. Последний снимок до паузы: база 15285271 bytes, journal persisted 3056, dropped 0, failures 0, но это не полный volume. Новый том не удалялся. Размер WAL, свободное место, миграции, защита при сбое, тесты восстановления и 30–60-минутная проверка объёма НЕ выполнены. Gate 1A не принят.

## Авария хранения · 27.10.2026 · повторная проверка

Gate 1A НЕ ПРИНЯТ. PostgreSQL runtime logs: PANIC / No space left on device,
recovery loop. Railway DISK_USAGE_GB current=0.495476736 на volume 500 MB.
Scanner uptime 44794 s: journal persisted=136914, dropped=677236, failures=69972,
pending=5000, last_write_error=CannotConnectNowError, healthy=false.
Это неполная история с потерями, НЕ доказательство успешного суточного наблюдения.

Read-back Railway: running deployment 2776a66a-4cfc-499a-a22f-2726acc29f43,
source 46aa2b8; исправление 64564f3 остаётся STAGED, patch
054bb354-e5c9-4124-aadd-6b0f5be69989. Его экономия диска в облаке НЕ проверена.
Попытка безопасно остановить scanner через regions.numReplicas=0 отклонена MCP
валидацией (minimum 1), остановка НЕ выполнена. Статус SUCCESS контейнера БД
не означает готовность PostgreSQL. История и volume не удалялись; тариф не менялся.

Восстановление без оплаты: сначала остановить scanner, затем получить отдельное
разрешение на сброс именно новой OBSERVE БД (предыдущее удаление касалось старых
сервисов). Если сохранение истории обязательно — сначала согласовать доступную
ёмкость для восстановления/экспорта; при recovery loop SQL export сейчас не доказан.
После восстановления применить исправление, добавить остановку при отказах durable
журнала и ранний storage budget с запасом на WAL, проверить фактический размер всего
volume и скорость роста, только потом начать новое непрерывное окно ≥24h.

## Минутные агрегаты только непроверенных underlying · 27.10.2026

46aa2b8: все четыре CI jobs SUCCESS; actual Railway SUCCESS, 180 s / 587228 quote events.
Рост DB после исправления lifecycle ~17 kB/s, что всё ещё не обеспечивает 24h на Free.
Evidence: evidence/railway-cache-fix-2026-10-27.json. Поэтому только непроверенные underlying
получают 60 s windows с per-code counts, min/max spread, последним полным sample и timeline
каждого discovery/end/data invalidation. По 64 transitions максимум, затем ранний flush.
Никаких удалений существующей истории. Reviewed/VERIFIED events остаются отдельными.
До flush или hard crash raw window может быть только в памяти до ~60 s; это явно не tick
replay и не исполнение. Graceful shutdown сохраняет pending windows. Проверки локально:
79 passed, 1 skipped, Ruff pass. Новая фактическая проверка роста после деплоя ещё впереди.

## Устранение ложных повторных discovery · 27.10.2026

Aggregation a574859 прошла Linux/Windows/Postgres/Docker CI 40400973144 и развернулась
SUCCESS (24ef2d23-987c-4db1-aae7-8bac2c5faa65). В первом измерении рост уменьшился примерно
с 60 до 32 kB/s, но 500 MB всё ещё не хватает на сутки. Найдена дополнительная причина:
TTL удалял raw state, а следующий тик живой биржи повторно создавал его со stale второй стороной.
Новое исправление сохраняет bounded внутренний state во время gap; отображение/счётчики
current по-прежнему фильтруются немедленным quote TTL. Только свежие обе котировки могут
доказать уход спреда ниже фильтра. 60 s без сравнений убирают cache state. Это не расширение TTL
и не разрешение VERIFIED на stale данных. Новая версия локально: 78 passed, 1 skipped, Ruff pass.
Верификация следующего runtime ещё впереди. Public OBSERVATION_HEALTH печатается раз в 60 s,
в durable DB сохраняется раз в 600 s; никаких секретов в отчёте нет.

## Промежуточная рыночная проверка новой версии · 27.10.2026

Runtime 812c3ab развернут (Railway deployment 17d74855-2bda-454c-a5e5-84c3e2742ca7 SUCCESS).
GitHub CI 40399402656: Linux/Windows/Postgres/Docker SUCCESS, включая реальные storage SQL и
Docker DB restart persistence. Новое фактическое окно 187 s: 620496 quote events, queue=0,
dropped=0, Bybit/BingX quote connections 21/25 без reconnect; depth отдельно 12/12.
Bybit quotes p95 3853 ms вместо прежних 185702 ms; fresh 505/811, BingX 993/993 и p95 668 ms.
Funding usable Bybit 811/811; BingX 16/993, остальные 977 требуют подтверждения интервала.
Compatible pairs=2, directed routes=4 (BTC/ETH). RAW=21, VERIFIED=0, EXECUTABLE=0.
Полное evidence: evidence/railway-feed-fix-2026-10-27.json. Это не 24 h и не полная приёмка.

**Найден эксплуатационный блокер:** фактический DB growth около 59–60 kB/s; Free 500 MB
недостаточно для суток такого журнала. Следующее исправление агрегирует повторные BLOCKED
обновления в окна до ~10 s с count/причинами/min-max spread/временем/последним полным sample.
Discovery, terminal events, VERIFIED transitions/revocations остаются отдельными. История
не удаляется; это агрегаты отклонённых наблюдений, не tick-by-tick replay.
RAW TTL опирается на две свежие котировки; старый/отсутствующий book запрещает VERIFIED,
но не скрывает свежий BLOCKED raw candidate. VERIFIED TTL по-прежнему ограничен quotes/books.

Для последующего суточного аудита сохраняется OBSERVATION_HEALTH каждые 600 s в Postgres;
/history?signal_id=INFRA:observation-health&limit=200 читает до 200 последних снимков.
Счётчики journal events и evaluated updates раздельны. Новые локальные тесты: 76 passed,
1 skipped, Ruff pass. Новое сжатие пока требует отдельного CI/деплоя и измерения реального роста.

## Обновление потоков и диагностики · 27.10.2026 · до нового деплоя

Подготовлен новый runtime: broad Bybit `orderbook.1` snapshot вместо ticker-delta; `ts` подтверждает
реальный полный снимок, `cts` хранится отдельно. Повторный snapshot с тем же u допустим; heartbeat
не меняет quote. TTL остаётся 2 s, max skew 1000 ms: медленные/тихие рынки могут отсеиваться.
Funding Bybit проверяется публичным REST tickers каждые ~30 s, без использования REST bid/ask
вместо WS. Отказы funding разложены на missing/stale/interval/settlement/invalid; добавлен /funding.

Depth shortlist удерживает подписки минимум 30 s, ограничен 12 на биржу, греет reviewed пары.
Плановая смена depth не называется аварией провайдера. Метрики quotes/depth раздельны.
Реестр содержит только два reviewed native underlying: BTC и ETH; прочие labels не повышаются
по совпадению символа. Источники и реальные catalog rows: evidence/identity-native-2026-10-27.json.

Локально 72 passed, 1 skipped (Postgres integration без TEST_DATABASE_URL), Ruff pass. Synthetic
load отдельно от рынка: 40000 events / 1200 assets, ~13460 events/s, p95 3.57 ms. Это не реальные
рыночные сигналы и не доказательство мощности ограниченного Railway контейнера.
Добавлены pg_database_size/pg_total_relation_size/growth через private DB и operational readiness
при ошибке записи; эти SQL ещё должны пройти real Postgres CI и cloud verification.

Новая версия ещё не считается проверенной на рынке до успешного CI, deploy и нового evidence.
Предыдущий runtime/реальное observation ниже сохраняются как историческое доказательство.

## Текущий Railway результат · 27.10.2026 · 01:41 Екатеринбург

После явного разрешения владельца удалены два старых сервиса и их два диска; удаление с 2FA
применено владельцем в dashboard и подтверждено read-back (0 services/volumes/pending).
Create нового project всё ещё отклоняется Free-limit, но create-service в очищенном
`humble-success` успешен. Платный тариф/платёж не включались.

**Scanner и приватный Postgres: SUCCESS, по одной running replica.** Runtime f5fc31b,
новый persistent volume 500 MB, /health=200. /ready=true означает только техническую
готовность OBSERVATION_ONLY + durable journal, не принятие 1A.

Доступ: https://arbitrage-os-v2-scanner-production.up.railway.app/status
Evidence: [railway-2026-10-27.json](evidence/railway-2026-10-27.json).

**Bybit REST и WS работают в этой фактической среде** на прежнем регионе workloads
`europe-west4-drams3a`. Используются официальные endpoints; прокси, альтернативных доменов,
ротации регионов и третьих CEX нет. Это не меняет доказанный country-block GitHub runner.

| Снимок после restart, uptime 190 s | Bybit | BingX |
|---|---:|---:|
| Записей каталога | 919 | 1294 |
| Активных контрактов | 811 | 996 |
| Исключено status/type/maintenance/launch | 108 | 298 |
| Получены bid/ask | 811 | 996 |
| Свежие по TTL в этом снимке | 242 | 996 |
| Возраст quotes p95 | 185702 ms | 766 ms |
| Свежих shortlist depth books | 9 | 5 |

449 совпадений base labels — **не подтверждённые пары**: identity registry пуст, совместимых
пар 0 подтверждено. 532781 quote events, 610976 directed comparisons/prechecks, 45345 candidate
updates, 1170 raw discoveries с повторными обнаружениями (не уникальные возможности).
RAW current=9, VERIFIED=0, EXECUTABLE=0, PAPER/LIVE orders=0.

Обработка WS p50=0.0507 ms/p95=0.3978 ms; сравнения/prechecks p50=0.0616 ms/p95=0.5007 ms,
окно последних 20000 событий. Это внутренняя задержка, не RTT и не время до исполнимой сделки.
Quote p95 Bybit включает давно не обновлённые bid/ask: эти записи не считаются свежими и
не получают ложного timestamp от heartbeat/funding. Полнота свежих данных ещё недостаточна.
RSS=141836288 bytes (~135.3 MiB), CPU=76.396 s/190 s, queue=1, journal dropped=0/failures=0.
Postgres persisted=4966 в текущем процессе; pending=3, это не общий row count всей БД.

Отказы (journal events, категории пересекаются): ASSET_IDENTITY_UNVERIFIED=3614,
FUNDING_UNAVAILABLE=2995, QUOTE_TIMESTAMP_SKEW=2180, ORDERBOOK_UNAVAILABLE=1923,
QUOTE_STALE=1334, ORDERBOOK_TIMESTAMP_SKEW=839, DATA_PROVIDER_OUTAGE=210.
Последний счётчик включает отзывы при изменении depth subscriptions, не доказывает 210
аварий broad-feed. Нужна дальнейшая детализация churn и полноты funding.

После restart только scanner /history вернул 12 записей старше нового CONFIG:BOOT.
История процесса сохранена в Postgres. Cloud DB restart не выполнялся; CI DB restart
проверялся отдельно. Free даёт $1/month usage и 500 MB volume, непрерывный месяц и достаточная
ёмкость истории этим не гарантируются. Автоочистка истории не настроена.

**Gate 1A не принят. Следующий шаг:** доказательный identity registry; полнота fresh bid/ask,
funding и стаканов; устранение причин реальных отказов; контроль роста БД/потребления credit;
затем ≥24h наблюдения с обоими потоками. После 1A обязателен 1B: Spot Bybit/BingX и DEX
BNB Chain, Base, Arbitrum. Telegram не подключён, торговые ключи/ордера запрещены.

Далее приведены исторические результаты предыдущих сред и первоначальные планы.

## Исторически: первоначальный блокер создания проекта

Railway подключён, список проектов проверен. Создание отдельного project `arbitrage-os-v2`
отклонено платформой: **Free plan resource provision limit exceeded**. Повторная проверка:
нового project нет, деплой/стадирование не начались, старые сервисы не менялись.

Готов reviewable plan `configs/deployment/railway-observe-plan.json`: scanner + отдельный
Postgres 16/2 GB volume, OBSERVE, bybit/bingx, protected variables, healthcheck и resource caps.
Runtime source — f5fc31b, прошедший GitHub CI. Сам план не применён.

Стоимость по текущим официальным тарифам: Hobby от $5/month с $5 included usage;
CPU/RAM/storage при всех предложенных caps непрерывно — ~$27.80/month плюс egress,
фактическая стоимость обычно отличается. Это не настроенный billing limit и не включает
старые workload расходы. Нужны согласование платного тарифа/бюджета и обновление entitlement
аккаунта; автоматический upgrade не выполнен. См. CLOUD_RUNBOOK.md и MASTER_SPEC §14.

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
| Cloud deployment | SUCCESS на Free; см. текущий Railway результат в начале документа |
| Наблюдение ≥24 h на двух биржах | НЕ ВЫПОЛНЕНО |

CI теперь содержит Linux/Windows, secrets history scan, реальный Postgres service и отдельный
Docker/compose job с проверкой сохранённого INTEGRATION_TEST event после перезапуска контейнеров.
Manual read-only workflow сохраняет independent network diagnostics и market observation artifact.
Ephemeral CI credentials генерируются и маскируются; не являются торговыми ключами.

## Исторически: шаг перед первоначальной публикацией

Опубликовать поставленный bundle обычным Windows Git push (команды в README), сохранив исходные
SHA. Затем проверить запустившийся CI и независимый public observation workflow. Для принятия
Gate 1A нужны разрешённая среда с реально доступными Bybit REST+WS, заполнение evidence identity
registry, durable Postgres, оба реальных потока и ≥24 h статистики. После 1A — обязательный 1B.
До этих проверок нет оснований объявлять сканер готовым или переходить к торговле.

Биржевые API-ключи, seed, подпись кошелька и live orders **не используются**. LIVE: **OFF**.
