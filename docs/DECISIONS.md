# Решения · 26.10.2026

1. Новый проект `arbitrage-os-v2`; исходники предыдущего движка не использованы.
2. Только Bybit/BingX, только linear USDT perpetual. Конфигурация отвергает другие CEX и любой режим кроме OBSERVE. Приватных API, отправки ордеров, исполнителя и переводов нет.
3. WS tickers по всему активному каталогу, 40 подписок на соединение, пакетные подписки Bybit и дозированные BingX. Каталоги обновляются независимо; недоступная площадка не заменяется другой.
4. Равенство base — индекс **сырых неподтверждённых кандидатов**, не доказательство underlying. VERIFIED требует отдельного доказательного реестра. Пустой исходный реестр выбран сознательно: во время разработки каталог Bybit недоступен. Автоматическое утверждение идентичности 1233 активов по тикеру запрещено. Реестр можно расширять только с проверяемыми источниками.
5. Цены/объёмы public feed нормализованы в USDT/base и base. Поле BingX `size` не умножается повторно на WS quantities, которые выражены в базовом активе. Обёрнутые и кратные активы не очищаются от префиксов автоматически.
6. Broad bid/ask → shortlist → native depth. Bybit 50 уровней с snapshot/delta; `u` проверяется на монотонность, не на вымышленное `+1`. BingX по фактическому испытанию использует `depth50@500ms`: исходный incrDepth превышает установленный бюджет 2000 уровней. Отдельный incremental-парсер BingX проверяет +1 и покрыт replay-тестами, но в активном feed не используется.
7. `ts` ограниченного стакана BingX — время создания сообщения, не matching-engine timestamp. Это явно указано в confidence flags; точный upstream возраст не обещается. Источники времени разделены с monotonic приёмом и обработкой.
8. Байтовый GZIP decode ограничен 4 MiB; очереди, истории в RAM и стаканы ограничены. Disconnect инвалидирует котировки/книги и отбрасывает отложенные старые события. Переподключение с jitter/backoff.
9. Bybit fee — официальная public non-VIP ставка taker 0.055%, проверена 26.10.2026; это не персональная комиссия. BingX fee — из public contract metadata. UNKNOWN fee блокирует VERIFIED. Четыре комиссии учитываются; немедленный round-trip и сценарное сжатие раздельны.
10. Funding interval Bybit из каталога. BingX interval допускается из явного поля либо из трёх согласованных исторических settlements для shortlist; неизвестный interval блокирует VERIFIED. Будущий rate — оценка по текущему rate, не гарантия. Изменение интервала требует дополнительного наблюдения перед дальнейшей приёмкой.
11. Postgres пишет пакетные signal events с UUID/idempotency; периодические снимки, смены состояния и завершение спреда, а не каждый тик. Без DATABASE_URL разрешён диагностический прогон: он явно NON-DURABLE. `/ready` не проходит без Postgres и двух свежих потоков.
12. Telegram — отдельный процесс, owner-only, редактирование карточки и кнопка «Назад»; сканер работает без токена. Настройки конечных чисел проходят проверку и сохраняются в Postgres с восстановлением при старте.
13. Нет автоматического признания этапа 1A принятым: короткий прогон одной биржи, synthetic load и unit-тесты не заменяют двухбиржевую проверку и длительную работу.
14. GitHub account доступен, но операция создания repository отсутствует в доступном connector. Подготовлены локальные commits и переносимый git bundle; новый пустой private repository должен создать владелец. Существующие repositories не изменялись.

## Продолжение · 27.10.2026 · требования 1.3

15. Пользователь создал `mfievmkmkm/arbitrage-os-v2`. GitHub metadata: repository пустой,
    visibility PUBLIC, connector permissions push/admin=true. Visibility не менялась.
    Прямой push исходной истории получил `could not read Username ... terminal prompts disabled`.
    Connector create_commit не принимает исходные author/committer/timestamps, поэтому не использован
    для пересоздания коммитов с другими SHA. Поставляется git bundle + команды CMD; force push запрещён.
16. В рабочем MASTER_SPEC теперь единая v1.3. Предыдущая v1.1 остаётся в Git истории.
    Полный этап 1 = 1A + 1B (DEX BNB/Base/Arbitrum и Spot Bybit/BingX). Исполнение A/B позже.
17. Повторная диагностика Bybit: и правильные REST пути, и заведомо неверный путь дают одинаковые
    HTTP 200 text/html 195 bytes, SHA256 5b131ca14aa96311d3432b0062c7443d3b0e6346ec279bd376a75f0a76bcd5d7.
    WS вместо 101 получает 200. TLS issuer — OpenAI, LLC / openai.com: перехват в сетевом пути доказан.
    Не установлено, генерирует ли заглушку сам шлюз или его upstream; утверждать точную региональную
    блокировку Bybit без origin/gateway logs нельзя. Endpoint верный по официальным V5 docs.
18. `PUBLIC_API_HTML_UNAVAILABLE` сохраняет безопасные HTTP metadata и hash без credentials.
    Нет альтернативных доменов, proxy rotation, третьих CEX или синтетического каталога Bybit.
19. Отзыв сигналов при disconnect/backpressure/invalid quote немедленный, включая API и журнал.
    TTL сигнала не продлевает TTL источника. Empty/crossed/invalid levels/skew дают отдельные причины.
20. Bybit ticker delta восстанавливает неизменившиеся fields в пределах непрерывного соединения;
    только реальный top-of-book delta освежает quote, funding/mark/heartbeat — нет. Порядок timestamps
    проверяется до изменения cache. Book использует cts при наличии и сохраняет u + cross seq.
21. Минимум три независимые проверки размера: default $50/$100/$250, плюс выбранный основной размер.
    Лимит проскальзывания по каждой стороне, общий qty grid и максимальный объём в пределах лимита;
    параметры наблюдения не являются торговым разрешением.
22. Postgres история включает также конфигурацию boot и отказы провайдера. Память отдельно от durable
    storage; без БД persisted=0. Clock offset — diagnostic midpoint с RTT uncertainty, без скрытой
    коррекции source timestamps. Ожидание общего REST limiter исключено из сетевого RTT.
23. Подготовлены отдельные GitHub jobs для настоящего Docker/compose/Postgres restart smoke и manual
    public observation. До push это NOT_RUN. Локально Docker/Postgres отсутствуют; apt не смог понизить
    UID/GID в sandbox, установка прекращена. Никакие права/региональные ограничения не обходились.


## Автономный запуск проверки · 27.10.2026

24. В GitHub connector нет workflow_dispatch write tool. Вместо действий владельца добавлен scoped
    push trigger только для .github/workflows/observe.yml, default 180 seconds, read-only permissions.
    Первичный перенос всех исходных commits выполнен владельцем без переписывания; дальнейшие
    изменения публикуются обычными новыми дочерними commits через connector.
25. CI прошёл Windows/Linux/Postgres/Docker. Agent самостоятельно запустил и прочитал observation
    40390030000. Bybit REST ответил явным country restriction 403, при этом WS BTCUSDT доступен.
    Запрет не обходится; недоступный каталог не восстанавливается догадкой из одного символа.
26. Явный country-block → PUBLIC_API_REGION_RESTRICTED с hash/HTTP evidence; обычный 403 не
    классифицируется как географический без доказательства. Добавлены два HTTP regression cases.


## Подготовка Railway · 27.10.2026

27. Подключение подтверждено, текущие projects прочитаны без изменения. Create project
    arbitrage-os-v2 заблокирован Free-plan resource limit; повторное list подтвердило отсутствие
    частично созданного project. Не удаляем и не переиспользуем старые workloads для обхода квоты.
28. Подготовлен reviewable deployment-plan JSON и расчёт caps. До owner budget approval по §14
    не выполняются upgrade/payment, живые create-service/create-volume или accept-deploy.
29. Legacy railway.json не добавляется: свежие официальные docs рекомендуют Infrastructure as Code;
    подготовленный JSON явно не объявляется нативным IaC-файлом. При наличии доступа будет
    применяться через staged MCP mutations и проверяться describe/get-staged-changes.


## Railway после очистки владельцем · 27.10.2026

30. Владелец явно разрешил удалить оба старых сервиса и их два диска. Изменения staged через MCP;
    accept-deploy отклонён Railway из-за обязательной 2FA в dashboard. Владелец применил удаление
    на сайте; read-back подтвердил 0 services, 0 volumes, 0 pending work. GitHub repos сохранены.
31. Создание нового project по-прежнему отклонено Free-limit. Создание пустого scanner service
    в уже существующем humble-success успешно. Используем этот очищенный project, без upgrade,
    оплаты или регистрации нового аккаунта. Это заменяет первоначальный план отдельного project.
32. Новый scanner и приватный Postgres развернуты из проверенного runtime f5fc31b; оба SUCCESS.
    Volume уменьшен с предложенных 2 GB до допустимых Free 500 MB. Секреты сгенерированы при
    развёртывании, находятся только в protected variables, в Git их значений нет. Trading keys нет.
33. Реальные Bybit REST/WS и BingX REST/WS получены в постоянном регионе прежних workloads.
    Это наблюдение другой среды, а не обход блокировки GitHub runner. Identity registry остаётся
    пустым; совпадение 449 base labels не объявляется совместимыми/исполнимыми контрактами.
34. После restart только scanner API /history вернул записи старше нового CONFIG:BOOT. Это
    доказательство сохранности истории процесса в Postgres, но не cloud DB restart test или ≥24h.
    Free кредит и 500 MB не гарантируют круглосуточный месяц или достаточную ёмкость истории.


## Корректность рыночного потока · 27.10.2026

35. Bybit broad bid/ask переведён на документированный snapshot-only orderbook.1. Повторные
    snapshot с тем же u подтверждают состояние, ts и cts сохраняются раздельно. Ticker/mark/funding
    и heartbeat не освежают котировки. Quote TTL и skew не расширяются для улучшения статистики.
36. Funding Bybit периодически получает actual current public REST rate/next/interval вместо
    зависимости от изменения ставки в ticker delta. BingX interval по истории не принимается
    за новую ставку и не освежает её monotonic age. Неизвестный интервал остаётся отказом.
37. Depth warm-up reviewed pairs и 30 s hold уменьшают churn; глубина bounded 12/venue. Planned
    unsubscribe отзывает book и signal с ORDERBOOK_UNAVAILABLE, а не ложной provider outage.
38. BTC/ETH: curated reviewed native-only bindings с источниками обеих бирж и catalog evidence.
    Numeric prefixes/wrappers/другие единицы не принимаются. Реестр не заполняется массово
    символьным сравнением; DEX token-address proof этим не заменяется.
39. DB monitor показывает фактический размер database/table и рост, но не выдаёт это за свободное
    место всего volume (WAL/other files не включены). История автоматически не удаляется.

40. Реальный monitor на 812c3ab показал ~60 kB/s database growth. Повторные BLOCKED решения
    агрегируются в bounded windows: timestamps, count, per-code counts, min/max spread и последний
    полный sample. Start/end/verification state transitions не сворачиваются. Это разрешённые
    агрегаты, не обещание сохранения каждого raw tick; существующие записи не удаляются.
41. RAW TTL зависит от quotes; VERIFIED TTL дополнительно от executable books. Неизвестный или
    устаревший book оставляет BLOCKED raw visible, не выдавая оценку исполнения.
42. Фактическое суточное наблюдение проверяется по durable OBSERVATION_HEALTH snapshots каждые
    600 s, выборка по signal_id параметризована и indexed. Наличие этого механизма не означает,
    что уже накоплены сутки, полного coverage или что free credit/volume точно хватит.

43. Реальное наблюдение a574859 показало, что aggregation одного repeated fingerprint недостаточно:
    TTL создавал искусственные повторные discovery/end циклы для raw candidates, когда одна
    котировка устарела. Внутренний bounded cache теперь переживает gap, при этом API/status
    по-прежнему немедленно скрывают запись после TTL. Fresh spread ниже фильтра либо 60 s без
    новых сравнений завершает episode. Stale comparison не доказывает экономическое закрытие.
    Все отказы сохраняются в windows; VERIFIED TTL и исполнимость не ослабляются.
44. OBSERVATION_HEALTH дополнительно печатается в stdout раз в 60 s для независимого чтения
    через Railway logs, в Postgres остаётся каждые 600 s. Отчёт содержит только public market
    metrics, без environment values/DSN/credentials. Поля asset/rejection_codes сохраняют
    совместимость с Telegram history renderer.

45. 46aa2b8 уменьшил фактический рост до ~17 kB/s, но 500 MB недостаточно для суток. Только
    ASSET_IDENTITY_UNVERIFIED history теперь собирается в окна до 60 s с counts/min-max/latest
    full sample и отдельным compact timeline всех discovery/end/data-invalidated переходов.
    До 64 transitions/window; при достижении лимита window немедленно сбрасывается, без потери
    границ episodes. Graceful close сбрасывает pending windows. При hard crash возможно до
    60 s непроверенной raw history в памяти; это не журнал ордеров или принятых сделок.
    Reviewed/VERIFIED transitions и реальные provider outages не сворачиваются этим правилом.
    Существующие durable записи не удаляются и не переписываются. Политика raw aggregation
    раскрывается в каждом event, pending unverified windows видны в /status.

46. 27.10.2026: подтверждён заполненный 500 MB volume / PostgreSQL recovery loop. Потери журнала делают текущее длительное окно неприемлемым для Gate 1A. 64564f3 оказался STAGED, production работает на 46aa2b8. Не удалять новую OBSERVE БД по старому разрешению на очистку legacy-сервисов. Не увеличивать платные ресурсы без согласования. Для восстановления требуется отдельное решение о сохранении/сбросе этой истории. Остановка через ноль реплик отклонена MCP (minimum 1); не считать сервис остановленным.
