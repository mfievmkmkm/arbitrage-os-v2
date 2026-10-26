# ARBITRAGE OS — мастер-ТЗ для нового проекта

**Версия:** 1.3 · 26 октября 2026 года · ЕДИНОЕ актуальное ТЗ: Bybit + BingX + DEX (этап 1B)
**Цель:** с нуля построить самостоятельный профессиональный сканер межбиржевых арбитражных возможностей, затем независимый торговый движок с двумя стратегиями и доказуемо корректным виртуальным/реальным исполнением.
**Язык интерфейса:** русский. **Режим первой разработки:** MARKET OBSERVE → PAPER MANUAL → PAPER AUTO; все LIVE-операции запрещены до отдельной приёмки и разрешения владельца.

> Это обязательный документ для команды/агента-разработчика. Не переносить ошибочную архитектуру предыдущего бота. Использовать старые исходники только для аудита прошлых ошибок и примеров, не как основу нового приложения. Проектировать итерационно с доказуемыми результатами. «Много сигналов» не равно «много прибыльных сделок».

## Приоритет требований и контроль версий

**Этот файл v1.3 полностью заменяет master-TЗ v1.1 и включает дополнение v1.2.** После его загрузки в проект ChatGPT старая v1.1 и отдельное дополнение v1.2 должны быть удалены/отключены во избежание конфликтов. Менять уже написанный код только там, где он противоречит актуальному ТЗ; не удалять текущий новый репозиторий ради смены версии требований.

**Текущая последовательность:** Stage 0 → **1A Bybit/BingX Futures/Futures OBSERVE** → **1B DEX BNB/Base/Arbitrum + Spot Bybit/BingX OBSERVE** → Stage 2 стратегии/ограничения/PAPER A1 → Stage 3 автоматизация PAPER A2/A3/B и только позднее разрешённый LIVE. Первый большой этап «Мощный сканер» **нельзя объявлять завершённым без 1B**. Stage 1A можно принять отдельным контрольным результатом.

**Правило конфликта:** этот раздел и главы 18–21 имеют приоритет над неоднозначными формулировками прежних разделов. Прошлые имена бирж в примерах — НЕ разрешение на подключения.

## Приоритетное решение владельца от 26.10.2026 — ОБЯЗАТЕЛЬНО

**Весь текущий охват CEX ограничен ровно двумя биржами: Bybit и BingX.** Это относится к Stage 0/1A, дальнейшей разработке Spot/Futures, подключению приватных API и PAPER-исполнению, пока владелец явно не изменит решение.

- `ENABLED_CEX_VENUES = ["bybit", "bingx"]` — исходная конфигурация; никаких иных подключённых CEX.
- **Binance не подключать сейчас вообще.** Не создавать Binance WebSocket/REST-сессии, не загружать Binance-каталог, не получать Binance-котировки, не включать Binance в сканирование, тестовую готовность или торговый цикл. Binance может рассматриваться только как потенциальное будущее расширение по отдельной команде владельца.
- **MEXC, OKX, Gate.io, Bitget и остальные CEX тоже не подключать на текущем этапе.** Даже если в тексте встречаются названия других бирж, они служат примерами будущего расширения или историческими референсами каналов, но НЕ разрешением на подключение.
- Первая исполняемая стратегия-сканер — **A1 Futures/Futures исключительно между Bybit и BingX**, в обоих направлениях: `LONG Bybit / SHORT BingX` и `LONG BingX / SHORT Bybit`.
- Использовать только действительно общие и совместимые фьючерсные инструменты Bybit и BingX; уникальные монеты одной площадки учитываются в её каталоге, но не создают фиктивную арбитражную пару.
- Для дальнейших A2/B1/B4 использовать Spot/Futures **тех же Bybit и BingX**, когда будет подтверждена соответствующая поддержка. DEX-пулы и независимый on-chain мониторинг — **обязательный подэтап 1B первого большого этапа «Сканер»**, не третья CEX.
- Новый CEX-адаптер может появиться только после отдельного согласования: правка конфигурации, независимые тесты, проверка API/capabilities и явное включение. Не расширять список бирж автоматически.

**При конфликте с любыми старшими/другими формулировками этого документа этот раздел имеет приоритет.** Итог первого этапа должен однозначно показывать `active_venues = ["bybit", "bingx"]`, а не Binance или MEXC.

## 0. Конечная картина продукта

Пользователь хочет **единый Telegram-продукт для межбиржевого арбитража**, который работает круглосуточно в облаке и выполняет полный путь:

1. Автоматически обнаруживает максимальное число доступных и допустимых торговых инструментов на включённых CEX и в выбранных DEX-сетях.
2. Получает поток bid/ask в реальном времени, выявляет **любые направления спреда** и изменения basis.
3. Сопоставляет только действительно идентичные активы и совместимые контракты/сети.
4. Преобразует сырые сигналы в **исполнимые торговые возможности** для конкретного размера сделки, с комиссиями, глубиной, проскальзыванием, funding и gas.
5. По настройкам показывает возможность, запрашивает подтверждение или открывает виртуальную позицию автоматически.
6. Сопровождает позицию, следит за обеими сторонами, учётной стоимостью, маржой, funding, переводами, событиями отказа и рисками.
7. Правильно закрывает обе стороны и записывает детальный, сверяемый результат, плюс выдаёт удобные русскоязычные карточки Telegram с кнопками управления.
8. В будущем — после отдельной LIVE-приёмки — может отправлять реальные торговые ордера при ограниченных суммах и явных правах; никакого автоматического включения LIVE при развёртывании.

**Принцип продукта:** сканер работает самостоятельно без торговых API. Торговый движок не содержит собственного альтернативного «плохого сканера», а потребляет проверенные сигналы из единого сервиса. Любая техническая блокировка объясняется в диагностике, а экономические ограничения не убираются искусственно для создания видимости сделок.

## 1. Чему учимся у реальных сигнальных каналов

Референсы: Telegram **@futures_spreads7** (FUTURES–FUTURES), **@MexcDexSpreadTracker** и алерт-каналы по MEXC Futures ↔ DEX. Пример другого открытого формата: **@mexcTracker**.

У каналов заметны: непрерывный список активов; % спреда; сторона LONG/SHORT; динамика открытия и сближения; сигнал «Aligned»; CEX/DEX цены; сеть; token contract address; ликвидность DEX, объёмы, funding; депозиты и выводы; историческая частота и длительность сближения. Надписи Win/Draw/Lose и исторический PNL могут отражать **модель**, а не реально исполненные сделки.

**Нам необходимо воспроизвести полезную информативность и превзойти каналы проверкой исполнимости.** Не копировать сигналы как единственный источник и не доверять их %/PNL без собственной рыночной верификации. Telegram-каналы использовать как дополнительный поток кандидатов и регрессионный эталон обнаружения; основа — собственная рыночная инфраструктура.

## 2. Ключевая развилка стратегий: что делать сначала

Утвердить **две стратегии на уровне архитектуры и сканера**, но **первой реализовать исполнение только стратегии A**, чтобы не повторять ошибку распыления на всё сразу.

**A. Рыночно-нейтральный двухногий арбитраж / trading basis convergence:**

- A1: **CEX Futures ↔ CEX Futures**: long более дешёвого бессрочного фьючерса и short более дорогого эквивалентного бессрочного фьючерса. Вход — по реальным ask для long и bid для short. Выход — по реальным bid для закрытия long и ask для закрытия short. Прибыль возникает из совокупного PnL обеих ног, расходов и funding, а не из цифры начального спреда.
- A2: **CEX Spot ↔ CEX Futures**: обычно long spot дешёвого актива и short дорогого perp (на одной/разных биржах). Reverse-направление допустимо только при реально доступном inventory/заимствовании и учёте его затрат; голый short без актива на споте запрещён.
- A3: **DEX Spot ↔ CEX Futures**: long проверенного DEX token через on-chain swap, short эквивалентного CEX perp. Могут быть другие направления, но лишь при физически осуществимом активе/заимствовании. On-chain quote, gas, MEV, anti-honeypot и подтверждение транзакции обязательны; отображаемые цены DEX-пула недостаточны.

**B. Арбитраж фактической покупки и продажи с переводом актива:**

- B1: CEX Spot → перевод → CEX Spot.
- B2: DEX Spot → перевод в CEX → CEX Spot.
- B3: CEX Spot → вывод на кошелёк → DEX Spot.
- B4: предфинансированные биржевые балансы / inventory arbitrage — одновременная покупка и продажа на разных площадках, затем управляемая ребалансировка; это ускоренный **вариант B**, не «третья стратегия».

**Рекомендация по дорожной карте:** MVP: широкое сканирование A1/A2/A3/B1/B2/B3 (где есть достоверные данные); глубокая оценка A1; доказуемый цикл A1 в PAPER; затем A2; затем A3 и переводной B в PAPER; лишь потом реальные торги. Сигналы по B с самого начала помечаются `DISCOVERY_ONLY` или `TRANSFER_PREFLIGHT_OK`, но не `READY_TO_TRADE` до полного блока проверки перевода.

**Почему не начинаем только с B:** B проще на словах («купил → перевёл → продал»), но время перевода не фиксирует конечную цену продажи. Даже 5–10% видимого спреда могут исчезнуть, пока идёт зачисление. B4 уменьшает эту проблему, но требует уже распределённых активов, достаточного капитала и отдельной бухгалтерии.

## 3. Этап I — отдельный мощный автономный сканер (главный приоритет)

### 3.1 Функциональные требования

Сканер — запускаемый сервис `scanner` с собственным REST/Web UI/Telegram-интерфейсом и API публикации нормализованных сигналов. Его работа **не зависит** от наличия ключей торговых аккаунтов и готовности `executor`. Он обязан:

- показывать перечень включённых бирж, сетей, статусы провайдеров и **количество реально охватываемых инструментов**;
- динамически включать/выключать биржи и выбранные классы рынков, а не оставаться привязанным к нескольким монетам;
- сканировать **все активные, поддерживаемые и корректно идентифицированные символы** включённых площадок в пределах доступного API и конфигурации; не обещать буквально все существующие DEX-токены всех блокчейнов за миллисекунды;
- отслеживать спред в обе стороны: биржа X дешёвая / Y дорогая и наоборот; не хранить только одностороннее сравнение;
- строить кандидатов A1/A2/A3/B1/B2/B3 на общей структуре рынка;
- иметь отдельные экраны `Сырые спреды`, `Проверенные возможности`, `Ожидают данных`, `Отклонены`, `История`, `Диагностика`;
- для каждого сигнала показывать источник, направление, timestamp, TTL/возраст котировок, объём в USD, bid/ask, доступную глубину, комиссии и estimate net;
- обновлять карточку сигнала и убирать устаревший, фиксировать начало/пик/сжатие/время жизни спреда, не спамить в Telegram каждую секунду;
- ранжировать отдельно по видимому % спреда, прогнозной чистой экономике, исполнимому объёму, свежести, риску и технической готовности;
- выдавать объективную статистику: scanned venues/instruments/pools, pair comparisons, discoveries, vetted signals, rejects по кодам, provider errors, data staleness, ws reconnects, dropped events, queue lag, average/p95 time-to-detect;
- хранить историю **не только победителей**, но и отказов/ложных сигналов; канал как источник сравнения, не доверенный сигнал на вход.

### 3.2 Реализация максимальной скорости без тысяч REST-запросов

**Скоуп MVP: только Bybit и BingX.** Bybit использует официальные V5 public instruments/tickers/books. Для BingX использовать официальные public Swap REST + WebSocket; корректно декодировать GZIP, отвечать Ping/Pong, принимать `bookTicker`, `incrDepth`/`depth` согласно доступной спецификации, проверять freshness/sequence и лимиты подписок. Не полагаться на символьное совпадение: `BTCUSDT` и `BTC-USDT` — лишь разные форматы представления, а не доказательство совпадения underlying и контрактной спецификации. Проверить фактическую доступность всех WS тем на текущей версии API и не придумывать гарантию 200 мс для всех монет.

**CEX:**

1. При старте получить полный каталог Spot/Perpetual через официальные REST instrument endpoints; **обрабатывать пагинацию** и статусы (Trading/PreLaunch/Closed), точность, min notional, base/quote/settle, тип/размер контракта; регулярно обновлять каталог и реагировать на листинг/делистинг.
2. Для массового слежения использовать **WebSocket market-data**, а не `fetch_order_book` по очереди для каждой монеты. Сначала best bid/ask, объём первой ступени, mark/index/funding (когда применимо). Где есть широковещательный all-market ticker, использовать его; где только подписки по символам — шардирование подключений по квотам. Сохранять независимость площадок: один медленный WS не блокирует другие.
3. Хранить top-of-book каждого инструмента в **быстром оперативном состоянии**, обновлять только изменившиеся символы и немедленно пересчитывать связанные маршруты по индексу `asset_id -> venues/instruments`. Не делать `O(N^2)` сравнений всех токенов со всеми: сравнивать только корректные совпадения.
4. **Двухуровневая оценка:** широкий дешёвый фильтр по bid/ask → только shortlist перспективных маршрутов получает 10–50 уровней стакана и расчёт VWAP/impact/fees/funding; глубокие подписки перераспределяются адаптивно.
5. Сохранять историю signal events в пакетном режиме; не писать каждый тик и каждый bid в отдельную SQLite-транзакцию. Backpressure и ограничение памяти обязательны.
6. WS heartbeat/reconnect со случайным backoff, resubscribe после разрыва, snapshot + корректная обработка incremental delta/sequence; при гэпе последовательности книга немедленно становится `STALE` до resync.
7. В каждом WS-соединении исполнять лимиты биржи, ping/pong, message caps; отдельные rate limiters для REST/WS subscribe/order endpoints; уважать `429`/`Retry-After`, не обходить ограничения.

**DEX:**

1. **Картографирование (discovery):** на поддерживаемых EVM-сетях получить проверяемый реестр адресов токенов с CEX и DEX, топ-пулы по ликвидности, индексы Factory PairCreated/PoolCreated и обновления состояния известных пулов. На Solana и TON — отдельные адаптеры **после** проверки поддержки и доступности инфраструктуры.
2. DexScreener/GeckoTerminal использовать для **поиска пулов, метаданных, рыночного контекста**, не как источник гарантированной цены исполнения. Эти REST API имеют лимиты и лаг.
3. Для перспективных CEX/DEX совпадений брать свежий `slot/block` и on-chain состояние поддерживаемого AMM, рассчитывать цену **на конкретный размер** через маршрутизатор или запрашивать `indicative price`, а перед PAPER/LIVE формировать `firm executable quote`, срок её жизни, маршрутизацию, gas и отказоустойчивость; для V3/CLMM корректно учитывать тики/распределённую ликвидность, а не просто общий TVL.
4. Слежение по WS RPC (новые блоки / логи пулов) и адаптивный приоритет проверок; нельзя опрашивать все токены у DEX-агрегатора каждую секунду. Использовать rate-budget и пакетирование/кэш.
5. Реестр контрактов с chainId, tokenAddress, decimals, token tax/transfer mechanics, proof-of-asset, risk flags; строгий запрет сопоставления монет **только по тикеру**. Символы вроде `OPENAI` на разных площадках могут означать разные активы. Один факт совпадающего названия не является достаточным.
6. Безопасность DEX: невозможность продать/honeypot, transfer tax, fee-on-transfer, blacklist/freeze/pause, владелец с опасными правами, прокси/upgradability, mint/burn, trade simulation, liquidity withdrawal, router address allowlist, MEV, RPC reliability, allowance non-infinite by default, approval cost, token impersonation. Неизвестное → исследовательская карточка, не вход.
7. Для LIVE DEX требуется отдельный безопасный signer с ограничениями chain/router/token/amount, симуляцией и подтверждением транзакций. **Никогда не хранить seed/private key в GitHub, журнале, чате или .env в репозитории**.

### 3.3 Покрытие вместо невыполнимого обещания «все монеты мгновенно»

Сканировать **весь пригодный universe** каждой включённой площадки и поддерживаемых цепей. Система должна честно показывать `coverage numerator / denominator` с причиной исключений:

- total discovered → active → identified → quotes fresh → counterpart found → depth verifiable → executable candidates;
- excluded examples: unmatched asset identity, halted market, prelaunch, insufficient depth, bad chain metadata, rate-limited provider, stale quote, blocked jurisdictions, unknown trading fee;
- DEX denom: сколько пулов/токенов отслеживаем на данной сети, сколько пулов найдено, сколько покрыто on-chain/quote адаптерами. Разделять **обнаружение** и **полноту всех существующих пулов**.

Не обещать <100 мс от блока до сделки при неизвестной сети/провайдере. **Целевые SLO для внутренней обработки на нормальной машине:**

- p95 задержки `получено сообщение CEX WS → обновлён raw candidate` ≤ 250 мс **после прогрева**, измерять реально;
- p95 старости используемых CEX котировок в shortlist желательно < 1 секунды; устаревшее автоматически блокирует `READY`;
- DEX: целевой цикл реальной оценки кандидата после обновления пула — секунды, с разделением задержки chain/RPC/aggregator; невозможные сроки не маскировать;
- p95 memory and CPU monitoring; ≥ 99% обработанных событий в пределах заданного resource budget; WS реконнект/пробел последовательности задокументирован.

Фактические пороги должны конфигурироваться по venue/feed и измеряться на продакшене до закрепления SLO. **Не путать время обновления WS поставщиком с фактической end-to-end задержкой сканера.**

### 3.4 Модель данных сигнала

Каждый маршрут получает единый структурированный объект:

```
Signal {
  id, schema_version, observed_at_utc, expires_at_utc,
  strategy: A1|A2|A3|B1|B2|B3|B4,
  stage: RAW|MATCHED|VERIFIED|EXECUTABLE|BLOCKED|EXPIRED,
  source: INTERNAL_SCANNER|TELEGRAM_HINT,
  asset_id, base, quote, chain_id?, token_address?, decimals?, identity_proof,
  cheap_venue, expensive_venue,
  long_leg?, short_leg?, spot_buy_leg?, spot_sell_leg?,
  best_bid, best_ask, timestamps, orderbook_sequence, size_usd,
  executable_buy_vwap, executable_sell_vwap, max_symmetric_qty,
  raw_spread_pct, bid_ask_spread_pct,
  open_fees_usd, estimated_close_fees_usd, slippage_reserve_usd,
  funding_expected_usd, gas_usd, approval_gas_usd, transfer_cost_usd,
  estimated_net_if_closed_at_current_quotes_usd,
  scenario_net_at_target_basis_usd, estimated_transfer_time_sec?,
  liquidity_depth_usd, quote_age_ms, confidence_flags,
  eligibility_status, rejection_codes[], route_tradeability,
  first_seen_at, peak_spread_pct, convergence_history, provider_health
}
```

`raw_spread_pct` — лишь индикатор. `estimated_net_if_closed_at_current_quotes_usd` — оценка **немедленного round-trip**, может быть отрицательной при потенциальной будущей стратегии сжатия. `scenario_net_at_target_basis_usd` — гипотетическая сценарная прибыль, **не гарантированный PnL**. Переносные сделки до фактической продажи не маркировать `realized_profit`.

### 3.5 Фильтры, скоринг, сортировка

В Telegram изменяемые по каждой стратегии: минимальный/максимальный raw spread, порог экономической возможности, размер USD, минимальная глубина, max spread between source timestamps, min turnover, allowed venues/chains, max gas, fee/funding fallback policy, запреты активов/роутеров, min net at exit objective, SLA, max positions, alerts cooldown.

По умолчанию **5% — пользовательский фильтр для канальных сигналов и крупных спредов, не универсальная гарантия прибыльной торговли**. Можно настроить отдельно A1/A2/A3/B. Для узких реальных A1 spread (<5%) сканер всё равно должен видеть рынок, если пользователь включил соответствующий режим. Не смешивать `показать сигнал от 5%` и `войти только если прибыль после комиссий > 5%`.

Скоринг должен учитывать `net at target / executable volume`, `hedge validity`, `funding`, `volatility`, `liquidation buffer`, `quote quality`, `confidence`, `delay`, `historical convergence`, но не автоматически считать историческое сжатие гарантированным.

## 4. Этап II — биржи, DEX и строгая логика стратегий

### 4.1 Подключение площадок

**На текущем этапе подключаем только Bybit и BingX.** В этапе 1A — только их USDT-settled линейные бессрочные Futures, с проверкой полной реально доступной номенклатуры контрактов. В будущих этапах — Spot этих же двух бирж и DEX-источники по отдельной готовности. Binance, MEXC, OKX, Gate.io, Bitget и другие CEX не инициировать и не включать без нового решения владельца. Архитектура адаптеров должна позволять позже добавить биржу без переписывания стратегии. DEX — обязательный этап 1B: сначала BNB Smart Chain, Base и Arbitrum One с измеряемым покрытием по одной AMM/route на сеть. Ethereum mainnet добавить после отдельной оценки gas и RPC-бюджета; затем по согласованию Solana, TON и прочие сети.

Для каждого venue — `MarketDataAdapter`, `InstrumentCatalogAdapter`, `FeeAndFundingAdapter`, `PrivateAccountAdapter`, `OrderAdapter`, `TransferAdapter` (последний только где реально доступен). Все имеют capabilities matrix:

```
venue, spot_public, perp_public, native_book_depth,
ws_supported, private_balance, maker_taker_fees,
place_order, cancel_order, reduce_only, order_stream,
positions_stream, withdraw, deposit_status, networks,
min_order, limits, tick_size, contract_size, margin_mode,
api_access_status, verified_at
```

Статусы: `NOT_CONFIGURED`, `PUBLIC_READY`, `ACCOUNT_READ_READY`, `PAPER_READY`, `LIVE_ORDER_READINESS_VERIFIED`, `UNAVAILABLE`, `DEGRADED`. **Наличие public котировок никогда не означает, что эта биржа готова к торговле.** Фьючерсный API может быть недоступен конкретному аккаунту/региону; не обходить биржевые запреты.

Отдельно: fetch instrument listing с пагинацией (Bybit linear > 500), normalize native contract quantity ↔ token units, linear vs inverse, index currency, settle, leverage, position mode (one-way/hedge), min notional/step, fee tier по реальному аккаунту или с консервативным флагом public schedule. Там, где персональная fee неизвестна, сигнал не считать «точным».

Действия приватного API ограничить в соответствии с режимами. Торговые ключи не создаются/не передаются через Telegram: они задаются владельцем в защищённом хранилище Railway или другом secrets manager. Ключи с **withdrawal off по умолчанию**, allowlist IP по возможности, раздельные read-only/trade permissions. Никогда не запрашивать seed phrase через чат.

### 4.2 Стратегия A: LONG низкой цены ↔ SHORT высокой цены

**A1 Futures/Futures:**

- Проверить эквивалентность underlying, lot/contract multiplier, expiry/settlement, trading status, quoting USD equivalent, обе стороны маржи.
- Рассчитать количество `q` в базовом активе, округлить под **обе** стороны с симметричным допустимым отклонением delta; исключить ситуацию 100 монет одной стороны против 1 другой.
- На бирже `low` вход: LONG по текущему ask с учётом order-book VWAP. На `high` вход: SHORT по текущему bid с учётом VWAP.
- На каждой переоценке выход: продажа LONG по bid и выкуп SHORT по ask, плюс уже списанные/предстоящие комиссии, funding, исполненные fill, ликвидационные риски.
- Пример: LONG q по 1.00, SHORT q по 1.08; если позже LONG можно продать 1.03, а SHORT закрыть 1.04, валовой price PnL = q*(1.03−1.00)+q*(1.08−1.04) = 0.07*q. **Это не 8% зафиксированной прибыли при открытии.** Отнять 4 ордерные комиссии, funding и фактические прочие затраты.
- При одновременном движении цены обеих ног в одну сторону PnL должен корректно взаимно компенсироваться; при увеличении basis фиксировать риск потерь.
- Триггеры выхода: настраиваемый net USD/pct по обоим закрываемым стаканам; net trailing с high watermark; max holding time; stop net; max basis divergence; liquidation distance/margin health; stale data fail-safe (не закрывать слепыми ценами, использовать аварийный reconciliation).
- Нельзя переоткрыть одно и то же сочетание, пока незавершённые ордера не сверены.

**A2 Spot/Futures:**

- LONG spot по ask, SHORT perp по bid; корректные активы и qty, реально доступные spot funds + perp margin.
- Spot не имеет funding; perp funding учитывается с правильным знаком по settlement history.
- Reverse: short spot только при подтверждённом inventory/borrow, borrow fee и разрешённом исполнении; иначе `REVERSE_UNAVAILABLE`.

**A3 DEX Spot/CEX Perp:**

- DEX buying/selling не симулировать через DexScreener `priceUsd`. Использовать размерозависимый `firm quote` и актуальные gas/approval/slippage/reserves. Long spot на DEX имеет on-chain latency и MEV; хеджный futures нельзя считать атомарным с транзакцией.
- Начинать с PAPER-моделирования по настоящим quotes и зафиксированным timestamps, включая `PENDING_CHAIN_TX`, `CHAIN_CONFIRMATIONS`, `FUTURES_HEDGE_PENDING`, `PARTIAL_HEDGE`, `UNWIND`.
- Первый LIVE A3 — только после тестов с безопасными лимитами кошелька, симуляцией транзакций и явным разрешением.

### 4.3 Стратегия B: купить → перевести → продать

Шаги:

1. Проверить spot ask на источнике для запланированного размера, spot bid на назначении, token identity, chain/network, token contract, withdraw+deposit capabilities, минимумы, адрес и MEMO/tag, лимиты KYC, gas/withdrawal fee, deposit confirmation count, status maintenance.
2. Рассчитать ex ante **прогнозную** прибыль `sell_at_snapshot - buy - venue fees - network fees - estimated slippage`, учесть вероятность изменения цены за transfer ETA. Не маркировать её гарантированной.
3. PAPER BUY (с реальной глубиной/частичными fill/latency), создать единый `transfer_id`, учесть withdrawal fee в монете, отправить/смоделировать перевод, ждать confirmations, re-query реального orderbook на назначении; если цена ухудшилась — политика hold/exit/stop, а не фиктивная продажа по старому bid.
4. PAPER SELL на реальном доступном bid с глубиной/проскальзыванием/частичным исполнением, свести число купленных и переведённых токенов, остатки и комиссии. Итоговый realized PnL только после settlement.
5. LIVE вывод средств — отдельный этап с whitelisted addresses, network guards, лимитами, строгим сопоставлением адресов, operator confirmation и reconcile. API withdraw не обещать на биржах, где он отсутствует/ограничен.

B4 предфинансированный: необходим заранее имеющийся токен в месте продажи + USDT/другая котируемая валюта в месте покупки; simultaneous buy/sell устраняет главный переносной ценовой риск, но создаёт **inventory imbalance**, позже rebalance с отдельной стоимостью.

**Особенно важно:** бот должен отличать `CAPITAL_NOT_AT_VENUE`, `DEPOSIT_NETWORK_DISABLED`, `WITHDRAW_NETWORK_DISABLED`, `TOKEN_CONTRACT_UNVERIFIED`, `MEMO_REQUIRED`, `TRANSFER_FEE_EXCEEDS_EDGE`, `ETA_PRICE_RISK_TOO_HIGH` от экономически неинтересного спреда.

### 4.4 Формулы и бухгалтерия

Для фиксированного нормализованного `q`:

```
long_unrealized  = q * (exit_bid_long - actual_entry_ask_long)
short_unrealized = q * (actual_entry_bid_short - exit_ask_short)
paired_net_now   = long_unrealized + short_unrealized
                 - opening_fees - projected_closing_fees
                 + settled_funding_cashflows - other_realized_costs
                 - remaining execution reserves
```

Для обратных квартированных контрактов, разных контрактных мультипликаторов, stablecoin depeg и разных валют расчёта — отдельные проверенные конвертеры, а не слепое применение формулы выше.

Для B:

```
final_net = actual_total_sell_proceeds
          - actual_total_buy_cost
          - trading_fees
          - withdraw_fee_value
          - chain_gas_and_approval
          - rebalance_cost_if_applicable
          +/- residual_inventory_mark_to_market
```

Отдельные поля: `gross_mark`, `estimated_net_if_closed_now`, `realized_settlement`, `funding_realized`, `fees_paid`, `fees_estimated`, `remaining_inventory` и `net_reconciled`. **Не смешивать просчитанную будущую прибыль и реализованную.**

## 5. Этап III — PAPER-исполнение, затем отдельный LIVE-gate

### 5.1 Режимы

1. `OBSERVE` — только сигналы, аналитика, никакие ордера.
2. `PAPER_MANUAL` — реальный сканер формирует заявку; пользователь подтверждает; исполнитель виртуальный.
3. `PAPER_AUTO` — найденный кандидат автоматически переоценивается и исполняется на виртуальных деньгах, если проходит все условия; отказ сохраняется с причиной.
4. `LIVE_MANUAL` — только после полной приёмки и отдельного owner-auth, реальное исполнение по явному подтверждению.
5. `LIVE_AUTO` — только отдельный этап с длительным доказанным PAPER, hard kill-switch и явно разрешёнными площадками/размерами. Никогда не запускать на «fresh Railway deploy» автоматически.

Режимы не должны самопроизвольно меняться при рестарте. В Telegram отдельно включаются стратегии и биржи. Восстанавливать открытые позиции после перезапуска по журналу и источнику биржи.

### 5.2 Порядок открытия A1, принцип «не держать голую ногу»

- `SIGNAL` → `PRECHECK` → `READY` → `RESERVING_CAPITAL` → `SUBMIT_LONG_AND_SHORT` → `VERIFY_FILLS` → `OPEN_HEDGED`.
- Ордеры двух ног направлять близко по времени, **но считать неатомарными**: идемпотентные clientOrderId и order exchange ID, acknowledgement, partial fills, cancels, aborts, in-flight quantities.
- Если одна нога не исполнилась или исполнилась частично: дозахеджировать только в заданных лимитах и окне, иначе оперативно закрыть исполненную часть. Любая неполная хеджированность отражается как `UNHEDGED_EXPOSURE` и требует risk-priority.
- Если ответ API потерян, **не отправлять ордер повторно без сверки по clientOrderId и exchange positions/orders**.
- PAPER должен моделировать latency, maker/taker fees, partial fills, slippage, отказ и недоступность API, funding, order lifecycle и потерю коннекта.
- Каскадная деградация: `DEX_RPC_OUTAGE` не останавливает CEX scanner; `BINGX_PRIVATE_UNAVAILABLE` блокирует только операции, требующие приватного API BingX, а публичный сканер продолжает работу. Если Bybit недоступен, система честно показывает, что межбиржевое сравнение двух CEX временно невозможно; нельзя подменять Bybit другой биржей автоматически.

### 5.3 Закрытие и сопровождение

- Каждая позиция отдельный state machine `OPEN_HEDGED`, `EXIT_PENDING`, `PARTIAL_EXIT`, `UNWINDING`, `CLOSED_RECONCILED`, `RECOVERY_REQUIRED`.
- Отдельные Telegram-кнопки: `Обновить`, `Закрыть`, `Уменьшить`, `Увеличить`, `Причины удержания`, `Подробности`, `Назад`. Операции resize пересчитываются по новому bid/ask и лимитам, не меняют историю первоначального fill.
- Точное отображение по обеим ногам: qty native/base, entry, mark, close bid/ask, unsettled funding, fees, equity exposure, liquidation buffer, elapsed, stop/target, last market update, route status.
- Стоп и аварийные сценарии имеют приоритет над обычным тейком. При отсутствии котировки **нельзя создавать вымышленный fill**; пометить `STALE` и использовать account reconciliation.
- Каждое изменение состояния — транзакционно сохранённое событие; после restart состояние восстанавливается без повторной сделки.

## 6. Telegram-интерфейс (русский, компактный)

**Главное меню (одно основное сообщение, inline-кнопки, `Назад`):**

```
🤖 ARBITRAGE OS                 🟢 PAPER AUTO
Сканер: WS онлайн / DEX частично онлайн
Активные биржи: Bybit, BingX
Монет CEX: ... / ...    DEX пулов: ...
Возможности: сырые ... / проверенные ... / пригодные ...
Открыто позиций: 0/1 · Вирт. капитал: $250
NET реализованный: ... · Нереализованный: ...

[ 🔎 Сканер ] [ 🎯 Возможности ]
[ ⚡ Стратегии ] [ 📂 Позиции ]
[ 📓 Дневник ] [ 💼 Балансы ]
[ ⚙️ Настройки ] [ 🛡 Риски ]
[ 🩺 Диагностика ]
```

**Сканер:** кнопки `Все`, `CEX↔CEX`, `CEX↔DEX`, `Перевод`, `Проверенные`, `Почему отказ`, `Фильтры`; сортировка по NET %, глубине, времени, рейтингу и спреду. Не создавать по 100 сообщений в минуту — карточки сигналов обновлять/группировать.

**Кандидат:**

```
🔎 A1 · TOKEN/USDT · сырой спред 6.2%
LONG Bybit [ask + qty] ↔ SHORT BingX [bid + qty]
Проверено на: $100/нога · глубина: $...
Расчёт при закрытии СЕЙЧАС: -$...
NET при гипотетическом целевом сжатии: +$...
Funding: ..., fees: ..., свежесть: ... ms
Статус: VERIFIED / UNEXECUTABLE: <code>
[Подробнее] [PAPER вход] [Отклонения] [Назад]
```

Важно: в Telegram должны быть произвольные вводимые числа (не только 5 фиксированных кнопок), проверка формата и диапазонов, без скрытого сброса настроек. Примеры: размер позиций, min spread, min estimated net at exit, max gas, max slippage, max delay, min liquidity, max leverage, portfolio stop, allocation per venue, stop loss, target net.

**Позиция:** отдельное закреплённое/редактируемое сообщение на каждую позицию с кнопками управления, исчезает/архивируется после закрытия, но **в дневнике остаётся навсегда**. Уведомления о перезапуске, ошибке одной ноги, неточной цене и funding.

## 7. Дневник, статистика и ИИ

Дневник должен хранить: номер signal, route, все рыночные входные снимки, raw-vs-executable edge, решение/отказ, каждое действие исполнителя, order IDs, fill, fee, funding, gas, transfer tx, payout, PnL components, риск, время и итог.

Отдельные отчёты: прибыльные/убыточные, win rate с учётом комиссий, PnL per venue/strategy/asset, среднее время жизни, статистика сканера, комиссии vs spread, rejected candidate funnel, provider quality, paper-vs-market deviations, частота unhedged incidents, наличие manual overrides.

**ИИ — аналитик, не бесконтрольный трейдер:** читает структурированный журнал, отвечает на вопросы владельца («почему вчера ноль сделок», «какой route создаёт ложные сигналы», «почему прибыль расходится с каналом»), предлагает корректировки настроек для утверждения, находит аномалии и сломанные адаптеры. В Phase 1/2 ИИ не должен сам менять деньги/риски, подменять котировки или открывать сделки; принятие решения — **детерминированный risk/execution engine**. Логировать версии модели и каждого предложения.

## 8. Архитектура и процессы

Начать с **модульного Python 3.12 монорепозитория**, несколько независимых процессов в Linux:

```
arbitrage-os/
  apps/scanner/         # CEX WebSocket fanout, DEX discovery, event evaluation
  apps/executor/        # PAPER state machine; future LIVE adapters isolated
  apps/telegram_bot/    # UI, user settings, approvals, notifications
  apps/api/             # dashboard/status/admin API
  core/                 # normalized instruments, asset identity, quote models,
                        # route evaluator, funding/fee math, risk/limits
  adapters/cex/         # only bybit/ and bingx/ in the initial release
  adapters/dex/         # EVM pool readers, aggregators, RPC, Solana later
  strategies/           # A1 A2 A3 B1 B2 B3 B4 policy rules
  infrastructure/       # message streams, persistence, lock, secrets
  migrations/           # Postgres schema
  tests/unit/
  tests/integration/
  tests/replay/
  tests/load/
  configs/examples/     # NO secrets
  scripts/
  docs/
  Dockerfile(s), docker-compose.yml, pyproject.toml, README.md, AGENTS.md
```

**Потоки данных:** adapters WS/RPC → normalized event bus → in-memory per-instrument state → identity route index → raw spread engine → depth+fees quote verifier → signal journal and ranking → strategy policy / risk gate → paper/live executor → transaction ledger + Telegram UI. Сканер не зависим от Telegram uptime; Telegram не влияет на market data.

Использовать **PostgreSQL** для важного состояния и аудита, а не одну огромную SQLite с записью каждого тика; горячие котировки держать в памяти (Redis/Streams только если оправдано нагрузкой); истории тиков — агрегировать/сжимать и хранить с retention. Избыточный Kafka/Kubernetes на старте не нужен. Обязательно: у всех сообщений idempotency key, UTC timestamps, monotonic timing for latency, bounded queues, backpressure, structured logs, metrics / Prometheus, uptime probes, graceful shutdown, recovery replay.

Дневник биржевых сделок и event ledger не обрезать без проверенного бэкапа; tick data хранить ограниченное время. Не допускать роста SQLite до 400+ MB на томе 500 MB как в старом проекте. Secrets только через Railway Variables/secret manager, минимальные permissions, read-only sandbox by default.

## 9. Критические коды отказов

Нужна машинно-читаемая enum/JSON с кодифицированной стадией `DISCOVERY`, `IDENTITY`, `MARKET_DATA`, `DEPTH`, `NET`, `BALANCE`, `ORDER`, `TRANSFER`, `SETTLEMENT`, `RISK`, `INFRA`, `POLICY`. Примеры:

- `ASSET_IDENTITY_UNVERIFIED`, `SAME_TICKER_DIFFERENT_TOKEN`, `CONTRACT_MULTIPLIER_MISMATCH`, `INVERSE_CONTRACT_UNSUPPORTED`
- `QUOTE_STALE`, `ORDERBOOK_GAP`, `NO_COUNTERPART`, `BOOK_DEPTH_TOO_LOW`, `MIN_ORDER_NOT_MET`
- `NET_TARGET_NOT_REACHABLE`, `CLOSING_FEES_EXCEED_EDGE`, `FUNDING_UNAVAILABLE`, `FUNDS_INSUFFICIENT`, `MARGIN_TOO_LOW`, `LIQUIDATION_BUFFER_LOW`
- `DEX_QUOTE_RATE_LIMIT`, `DEX_SWAP_SIMULATION_FAILED`, `DEX_ROUTER_UNAPPROVED`, `DEX_TOKEN_TAX`, `DEX_SELL_BLOCKED`, `DEX_GAS_TOO_HIGH`, `CHAIN_REORG`
- `TRANSFER_NETWORK_MISMATCH`, `WITHDRAW_DISABLED`, `DEPOSIT_DISABLED`, `TRANSFER_ETA_HIGH`, `MEMO_MISSING`, `TRANSFER_PENDING`
- `LIVE_DISABLED`, `MODE_OBSERVE`, `MANUAL_CONFIRMATION_REQUIRED`, `VENUE_ACCOUNT_READ_ONLY`, `TRADING_API_UNAVAILABLE`, `UNHEDGED_TIMEOUT`, `RECONCILIATION_REQUIRED`, `DATA_PROVIDER_OUTAGE`.

**Встроенное объяснение причин в Telegram:** если 0 сделок, показать `raw=...`, `identifiable=...`, `depth_verified=...`, `economically_eligible=...`, `blocked_by_risk=...`, `paper_opened=0`, ТОП-10 причин. Не прятать реальные отказы за общим `NO_OPPORTUNITIES`.

## 10. Режимы бюджетов и безопасность

**Первый эксперимент:** $250 PAPER виртуального общего капитала, лимит позиции в интерфейсе около $100 номинала на каждую ногу с обязательной проверкой margin budget и комиссий; торгуемая сумма корректируется под min-order и доступные средства. Осторожный план LIVE с ~$40–50 может быть неосуществим для многих двухбиржевых маршрутов; бот обязан это прямо показывать. Никакой экономической гарантии прибыли.

- MAX open trades configurable (изначально 1), per-asset/venue/chains, max net loss/day, emergency stop, margin buffer, gas ceilings.
- No passwords/private keys in repo/chat/log. API access separated public/read-only/paper/live. Withdrawal off by default.
- Подтверждение для LIVE и особенно вывода средств отдельно; дополнительные кошельковые лимиты и allowlist.
- Разрешения бирж, региональные ограничения и KYC не обходить.
- Все финансовые суммы могут меняться в Telegram, но недопустимые значения (negative/NaN/too-large, unsafe leverage) отвергаются.

## 11. Порядок по этапам и выдаваемые результаты

### Этап 0 — чистый скелет (готовый репозиторий)
- Создать **новый GitHub-репозиторий** `arbitrage-os-v2`; старый не трогать.
- README, решения ADR, pyproject, Docker, .env.example без секретов, CI Linux+Windows, Postgres migrations, skeletal Telegram control, tests/replay fixtures, мониторинг, наблюдаемость.
- Привести API adapters capability map и актуальные официальные ссылки. Никаких вымышленных биржевых ключей и обещаний поддержки неподтверждённых API.
- Результат: `docker compose up`, `/health`, `/status`, старт `OBSERVE`, список рынков.

### Этап 1A — сканер CEX A1 (обязательный MVP)
- Native WS **Bybit + BingX** (и только они); полный реально доступный universe контрактов, корректная пагинация там, где она требуется, маршруты LONG/SHORT в обе стороны, нормализация contract sizes и fee/funding, quote age и глубокий order-book preflight. Для BingX проверить GZIP WebSocket frames, Ping/Pong, контрактные спецификации и лимиты подписок.
- Метрики coverage, latency и reasons; русское меню «Сканер», top raw/executable signals, обновление в реальном времени.
- Испытание непрерывным чтением ≥ 24 ч (или зафиксированным окном с отчётом для первой приемки), логи stale/reconnect, non-blocking.
- **Не добавлять третью CEX.** На следующем подэтапе улучшить покрытие и стабильность **только Bybit/BingX**, включая новые листинги, устойчивые WebSocket, корректную готовность и диагностику. Расширение бирж отложено до нового запроса владельца.

### Этап 1B — CEX Spot и DEX discovery/quoting
**CEX-часть этого этапа по-прежнему только Bybit/BingX (Spot); новые централизованные биржи не подключать.**

- Модуль CEX Spot **только для Bybit и BingX**; raw spread для A2/B1 без любых других CEX.
- Реестр chain/token address и пулы **BNB Smart Chain (56), Base (8453), Arbitrum One (42161)**: по одному реально работающему AMM/route на сеть, затем дополнительный агрегатор и измеряемое расширение; Ethereum mainnet (1) — после отдельной оценки газовых расходов и RPC. Обязательны on-chain pool updates, size-aware buy/sell quote preflight для top candidates и A3/B2/B3 discovery. Полная готовность большого этапа «Сканер» требует 1A + 1B, а не только Futures/Futures.
- Показывать ошибки provider/rate-limit/contract match, DEX coverage. Не обещать `100% всех DEX токенов`.

### Этап 2 — корректные стратегии и sandbox исполнителя
- Написать deterministic strategy evaluators A1/A2/A3/B1/B2/B3 со всеми входными проверками и reason codes; fee/funding/transfer math; venue capability matrix.
- PAPER state machine для A1 с обеими ногами, partial fills и bounded rollback. Виртуальный капитал и Telegram подтверждения.
- Тесты на несовпадающие тикеры, некорректную величину qty, stale book, funding change, API 429/WS gap, failover, минусовую экономику и recovery.
- **Результат:** несколько **реальных рыночных** кандидатов с прозрачными причинами решения; хотя бы один законченный synthetic REPLAY profitable, loss-making и unhedged scenario; нет принудительного fake PAPER entry.

### Этап 3 — полный PAPER lifecycle, затем B и DEX
- PAPER AUTO/ MANUAL A1 → A2 → A3, full open/mark/exit; B1/B2/B3/B4 купить-перевести-продать, ограничения transfer, time-to-credit, rebalancing.
- Подробный дневник, карточки каждой позиции, корректное возобновление после redeploy, reconcile.
- PAPER на реальном потоке ≥ 72 ч, отчёт всех кандидатов и отказов, открытых/закрытых, нарисованных vs actual prices, реализованных NET, задержек, incident rate.
- Лишь по явному запросу отдельный milestone `LIVE_MANUAL`, маленькие суммы, read-only account validation, signed plans, kill switch, acceptance checklist. `LIVE_AUTO` позже.

## 12. Критерии приёмки каждого этапа (не «просто тесты прошли»)

Разработчик должен предоставить доказательства, а не описание намерений:

**Сканер:**
- реальный список instrument IDs (кол-во по биржам/сетям, доля покрытых), снимки актуальных bid/ask и timestamps с ID источника;
- реальное пересчитывание при WS updates и обновление карточек Telegram;
- 2+ независимых CEX и несколько сотен инструментов, **если фактически доступны**; не выдумывать их в отчёте;
- количественная сводка raw candidates, top profitable-after-fee opportunities, rejection funnel;
- мониторинг p50/p95 latency, memory, missed websocket sequence, provider 429, recovery.

**PAPER:**
- trace ID на каждый сигнал → precheck → order placement → fills обеих ног → marking → closure → ledger;
- unit/integration/replay/chaos тесты + повтор с real-time read-only market data;
- если нет пригодных реальных кандидатов, показать почему и не фальсифицировать открытие ради галочки;
- PnL из фактических смоделированных fills, bid/ask и 4 fee legs, без mid-price фикции;
- журнал истории неизменен после restart; открытые позиции корректно восстановлены.

**LIVE:**
- только отдельная подписанная владельцем проверка, раздельные ключи, лимиты, explicit off by default, действия только на включённых рынках; без неё код не имеет возможности отправлять LIVE.

## 13. Что недопустимо повторить из старого проекта

1. Сканировать несколько символов вместо всех реальных поддерживаемых инструментов и писать «всё покрыто».
2. Создавать очень тяжёлый REST polling и кэшировать full CCXT raw market payload без лимита.
3. Полагаться на DexScreener price как на исполнимый swap quote.
4. Находить спред и не проверять тип актива/token address/contract multiplier.
5. Безусловно блокировать правильную стратегию устаревшим hidden toggle; режимы должны быть прозрачны.
6. Разрешать PAPER по unit-тесту, но реально не проходить в `paper.open`.
7. Маскировать реальную причину отказа под `NO_SIGNAL`, не показывать стадии.
8. Подменять отрицательную экономику якобы прибыльной за счёт исключения комиссий/funding/gas.
9. Считать всю прибыль мгновенно полученной при появлении спреда.
10. При включении LIVE не защищаться от одной исполненной ноги и повторной отправки после timeout.
11. Терять history/ledger на redeploy, держать растущую БД на крошечном томе без контрольного бэкапа.
12. Декларировать «безошибочность». Вместо этого проектировать наблюдаемое восстановление и режим safe degradation.

## 14. Приоритеты по стоимости и инфраструктуре

**Разработка:** ChatGPT **Work** для многошаговой работы с GitHub/Railway, обычный ChatGPT для проектирования и проверки, Codex позже, если станет доступен без проблем с телефонной авторизацией; доступ к Codex не является техническим требованием. GitHub — истина для кода; Railway — круглосуточный Linux runtime, не IDE и не место хранения единственной копии кода.

**Стартовая инфраструктура:** отдельный Railway project/service и PostgreSQL, с измеренным размером памяти. Для большого WS-сканера 1 GiB может не хватить; предусмотреть 2–4 GiB или масштабирование по фактической нагрузке. Не открывать новую дорогую инфраструктуру до профилирования.

**Черновой бюджет для планирования, НЕ публичная котировка провайдера:** 20–60 USD/месяц на первые сервисы/БД и мониторинг, далее 0–100+ USD/мес на RPC/платные market/aggregator API при расширении сетей и частоты. Реальная цена зависит от плана Railway, размера БД, запросов, трафика и географии. Все расходы согласовать перед включением платных источников. Торговый капитал — отдельная статья. Не покупать API/subscription «на всякий случай».

**Важно:** миллионы рынков без затрат не мониторятся «в реальном времени» одинаково. Массовый обзор — WebSockets + on-chain pool events и дешёвые индексы; полные исполнимые quotes — только на shortlist; использовать честные уровни покрытия и приоритеты.

## 15. Формат отчёта агента-разработчика после каждого шага

```
ЭТАП / ВЕРСИЯ / GitHub commit / deploy ID
Что реально написано и работает (с доказательствами)
Сколько активных бирж/символов/DEX-пулов реально покрыто
Последние market-data события и p95 delay
Сколько raw / verified / executable кандидатов за период
ТОП причин отклонения, число открытых/закрытых PAPER сделок
Потери данных/сбои и восстановление
CI Linux и Windows + replay/chaos результаты
Что блокирует следующий этап, что надо от пользователя
Точно какие настройки/секреты пользователь вносит самостоятельно
Режим LIVE: OFF
```

Не останавливаться после «я создал файл»; каждая задача должна приводить к созданным файлам, коммитам и проверенной работе. Если подключение недоступно, явно писать `NOT_CONNECTED`, не придумывать результат.

## 16. Первое поручение (скопировать в ChatGPT Work / Codex)

> Ты выступаешь ведущим архитектором и Python-разработчиком нового проекта ARBITRAGE OS. Полностью прочитай MASTER_SPEC и выполни только Этапы 0 и 1A из документа, не уходя в исполнение LIVE. Создай **новый** GitHub-репозиторий `arbitrage-os-v2` (или попроси меня создать пустой репозиторий только если инструмент технически не позволяет); старый бот не изменяй.
>
> Для первого готового релиза: отдельный постоянно работающий CEX Futures/Futures сканер **ТОЛЬКО Bybit и BingX**. Binance, MEXC и прочие CEX не подключать даже фоново. Быстрые WebSocket потоки всех реально доступных валидных линейных USDT-perp инструментов этих двух площадок, корректный каталог и нормализация, сравнение обеих сторон в двух направлениях, глубокая проверка стакана для top candidates, реальные fee/funding metadata, оценка NET без фиктивной прибыли, журнал отказов, наблюдаемость, русский Telegram UI «Сканер», Docker, Postgres и CI. Массовый сканер без trading keys; режим OBSERVE по умолчанию.
>
> Не обещай 100% всех DEX монет и безусловной прибыли. DEX 1B заложи в архитектуру, но не трать весь этап на сложный on-chain execution. Проведи real-market observation, покажи реальные counts, latency и причины отказов. Все результаты закрепи в GitHub с тестами и отчётом. Ни одного реального ордера.

## 17. Официальные технические источники для реализации

- Bybit V5 Instruments: https://bybit-exchange.github.io/docs/v5/market/instrument
- Bybit V5 Public WS ticker: https://bybit-exchange.github.io/docs/v5/websocket/public/ticker
- Bybit V5 Public WS Orderbook: https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook
- BingX USDT-M Swap public WebSocket: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-ws-market/api-reference.md
- BingX USDT-M Swap contracts, depth, book ticker (REST): https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-market/api-reference.md
- BingX Spot WS (будущий этап): https://github.com/BingX-API/api-ai-skills/blob/main/skills/spot-ws-market/SKILL.md
- DexScreener API limits: https://docs.dexscreener.com/api/reference
- 0x indicative price and firm quote: https://docs.0x.org/docs/introduction/quickstart/swap-tokens-with-0x-swap-api
- ChatGPT Work/Codex: https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex

**Конец обязательного ТЗ.**


## 18. Обязательные уточнения DEX и критериев Stage 1B (интегрировано из v1.2)

### 18.0. Жёстко фиксируем скоуп

- Единственные CEX на данном этапе: **Bybit и BingX**. Никаких Binance/MEXC/OKX/Bitget/Gate.io в действующих интеграциях, fallback, тестовых конфигурациях или по умолчанию.
- **DEX обязательно должен войти в завершённый первый большой этап «СКАНЕР»**, как подэтап 1B. Подэтап 1A (Futures/Futures) можно принять отдельно, но нельзя объявить *весь первый этап сканера* завершённым без 1B.
- Порядок: 1A Bybit↔BingX Futures/Futures → 1B Spot Bybit/BingX + DEX discovery/quote + CEX↔DEX и переносные *кандидаты* → 2 стратегия/risk/paper A1 → 3 полные PAPER-циклы A2/A3/B. Нет разрешения откладывать 1B до торгового LIVE.
- Использовать русские надписи в Telegram. Никогда не выдавать REPLAY и синтетические возможности за рыночные.

### 18.1. DEX-сети и сканируемые площадки

Начальный приоритет по практичности на небольших позициях:

1. **BNB Smart Chain (chainId=56)**.
2. **Base (chainId=8453)**.
3. **Arbitrum One (chainId=42161)**.
4. **Ethereum (chainId=1)** — поддержать в архитектуре и добавить после проверки gas-экономики, RPC бюджета и скорости; не делать Ethereum условием готовности первых трёх сетей.

Работаем не с абстрактной «DEX биржей», а с `chain + token address + pool/route + settlement asset`. Сначала реализовать по одному понятному семейству AMM (V2/V3 где поддерживается), а также 0x либо совместимый агрегатор для оценки исполнения. Подключать другие AMM и маршруты по измеренной доле необработанных возможностей. **Ни один поставщик (DexScreener/GeckoTerminal/0x) не может быть единственным способом discovery и подтверждения исполнения одновременно.**

В будущем допускаются Ethereum, Solana, TON и дополнительные сети по отдельной задаче после доказательств корректной работы текущих адаптеров. Не смешивать EVM- и не-EVM-семантику в одном адаптере.

### 18.2. Архитектура мощного DEX discovery

Сканер обязан использовать минимум два независимых уровня:

**А. Широкий дешёвый discovery:**
- индексировать известные factory события `PairCreated`/`PoolCreated`, активные пулы AMM и обновления новых блоков через доступные индексаторы/RPC;
- использовать DEX Screener / GeckoTerminal *как дополнительный источник* pool metadata и популярности, а не как единственный список рынков;
- следить за новыми пулами и листингами, вести дедупликацию по `chainId + pool address`;
- периодически проверять состояние и ликвидность pool universe. Не обещать буквального 100% охвата любой монеты любой сети;
- иметь prioritization queue: совпадения с Bybit/BingX, ликвидность, объёмы, свежесть торгов, изменение цены, обнаруженный спред, доступность quotes.

**Б. Быстрый мониторинг и проверка:**
- on-chain новые блоки и обновления пулов (event-driven), кэш точного block/slot и timestamp;
- для потенциальных маршрутов запрашивать **на конкретную сумму** (пример $50/$100/$250, выбирается настройкой) indicative buy/sell quote, учитывающий маршрут и цену исполнения; затем перед решением о PAPER-входе получать пригодный для симуляции execution quote;
- поддерживать API rate budgeting, backoff, connection health, stale flags и adaptive sampling;
- V3/CLMM не оценивать по общему TVL или одному `spot price`: учитывать тики, маршрут, фактическую доступную ликвидность;
- при деградации RPC/aggregator отключать только соответствующую сеть/маршрут с диагностикой, а не останавливать CEX Futures/Futures.

**Обязательные метрики DEX на каждую сеть:** `pools_discovered`, `pools_active`, `tokens_identified`, `tokens_matched_to_cex`, `pools_subscribed`, `pools_updated_60s`, `last_chain_block`, `block_lag`, `quote_requested`, `quote_success`, `quote_rate_limited`, `quote_unsupported`, `quote_age_ms_p50/p95`, `rpc_errors`, `memory_used`, `tradeable_routes`.

### 18.3. Строгая идентичность актива — не тикер

Сопоставлять DEX token с Bybit/BingX-perp можно **только при наличии проверенных доказательств идентичности underlying**. Для токена хранить: `chainId`, `tokenAddress`, decimals, verified issuer/source, native/wrapped/bridged variant, transfer characteristics, token risk flags, фактическое соответствие CEX underlying и contract multiplier.

`ABC` и `ABC` на двух площадках недостаточно; даже `1000ABC` и `ABC` не эквивалентны без явного multiplier. Неоднозначный match → `UNVERIFIED_ASSET_IDENTITY`, отображать в исследовательских сигналах, **запретить PAPER_AUTO/LIVE**. Не расширять реестр на основании одного совпадения имён.

### 18.4. Физически допустимые арбитражные направления

- **A1 — Futures/Futures:** `LONG Bybit / SHORT BingX` либо `LONG BingX / SHORT Bybit`. Нужны обе равные по базовому риску противоположные ноги.
- **A3 — DEX Spot ↔ CEX Futures:** реальная начальная схема — **BUY токен через DEX Swap + SHORT того же underlying на Bybit либо BingX**. Обязательны баланс для swap, газ, квота на размер, возможность затем SELL токен, допустимый контракт фьючерса, funding, риск между исполнениями. Отражать положительное/отрицательное схождение basis как сценарий, не как гарантированную прибыль.
- **Обратное направление A3:** запрещено рисовать `SHORT DEX spot`, если у стратегии нет заранее размещённого токена и разрешённой возможности немедленно его продать или проверенного borrow. Не симулировать продажу несуществующего актива. Любой такой маршрут обозначать `UNEXECUTABLE_NO_INVENTORY`.
- **B2 — DEX Spot → CEX Spot:** BUY на DEX → блокчейн-перевод по **поддерживаемой CEX сети** → дождаться зачисления → SELL по **новому** стакану. Старый bid при обнаружении — только сценарная оценка. Если нет разрешённых депозитов, неподходящая сеть, недостаточный min credit/withdrawal, token tax или высокий gas — блокировать.
- **B3 — CEX Spot → DEX Spot:** BUY CEX → withdraw в корректную chain/address → SELL DEX по новой квоте после зачисления. Без проверенной сети вывода, адреса, времени, комиссии и разрешённых операций — только исследовательский сигнал.
- **B4 — предварительно распределённые активы:** одновременный BUY на дешёвом venue и SELL из *уже существующего* запаса на дорогом; после — явная необходимость ребалансировки с полной стоимостью. Без реального запаса не переводить B4 в EXECUTABLE.

### Принципиально: 0x quote не является блокировкой цены в блокчейне

Использовать `indicative price` для широкого фильтра, `firm quote` для конкретного плана. Но даже «firm» quote **не гарантирует успешный mining, отсутствие MEV, исполнения и фактический gas**. Для PAPER учитывать задержку/ценовой дрейф между on-chain и CEX hedge; для LIVE отдельно требовать simulation и установленную политику первой ноги/аварийного закрытия.

### 18.5. Формулы: до входа и после закрытия

- Для A1/A3 оценивать полный round-trip: вход обеих ног + предполагаемый выход обеих ног + все комиссии + funding + gas + on-chain approvals + estimated slippage + risk buffer.
- Разделить строго: `raw_spread`, `executable_entry_edge`, `estimated_net_if_closed_now`, `scenario_net_at_target_spread`, `realized_net`. Сценарный ожидаемый доход при будущем сжатии — не реализованный результат.
- Для B2/B3 не называть сигнал гарантированной прибылью до подтверждённой продажи; в пути может измениться цена или зачисление. Показывать best/worst-case scenarios.
- Funding сверять с конкретной биржей, временем ближайшего settlement, прогнозом удержания, а не с одним статичным значением.

### 18.6. Статусы и приёмка сканера

**Статусы одного candidate:** `DISCOVERED` → `ASSET_MATCHED` → `PRICE_OBSERVED` → `QUOTED_AT_SIZE` → `RISK_VERIFIED` → `EXECUTABLE` либо `WATCH_ONLY`/`REJECTED`/`EXPIRED`. Сигнал в Telegram обязан показывать причину, если не готов к торговле.

**Готовность Stage 1A:** Bybit/BingX USDT-perp universe получен полностью; доля свежих stream quotes измерена; есть оба направления сравнения; нет чужих CEX feeds; есть отчёт минимум за 24 часа наблюдения с latency/false-positive/reconnect stats, либо частичный отчёт с явной пометкой что приёмка не закрыта.

**Готовность Stage 1B:** реальный on-chain discovery + мониторинг пулов **BNB/Base/Arbitrum** (по одному рабочему AMM/route на сеть), проверенный identity registry CEX↔DEX, реальные indicative/firm quotes для доступных токенов на проверочных размерах, расходы gas/approve, аудируемый журнал отказов и Telegram-карточка. Отчитаться по coverage и частоте обновления **на каждой сети отдельно**. Нельзя писать «все DEX монеты работают», если реально отслеживается 30 пулов или сломан quote provider.

Не требовать ненулевых прибыльных сделок, если рынок их не дал; но требовать фактических live-market данных и отдельно подтверждённых REPLAY-сценариев прибыль/убыток/неисполнение. Проверить случаи liquidity rug, token tax, honeypot, chain reorg, DEX quote expiry, CEX WS stale, partial fills, API 429, outage RPC, неправильно сопоставленный токен и кратное обозначение фьючерса.

### 18.7. Исключить старые ошибки и ненужное разрастание

- Нельзя при отсутствии сигналов добавлять вымышленные монеты, фальшивые ордера или скрытно включать MEXC/Binance для «показательной» статистики.
- Меньше прежних 900-секундных и других необъяснимых задержек: все TTL, thresholds, scan frequency, backoff и gating должны отображаться в настройках/диагностике; адаптивно по типу источника.
- Не запускать торговый API во время scanner Stage 1A/1B: режим `OBSERVE`, no live orders, private keys, wallet signing.
- Репозиторий/база/сервис — отдельные от старого `arbitrage-engine`. Желательно Postgres как durable state и bounded retention metrics для тиков; сохранять историю сделок и решений при деплоях.
- ИИ только анализирует **дневник и причины отказов**, не подменяет deterministic стратегии, не торгует на основании текстовой догадки, не меняет риск-параметры без разрешения.
- Для сравнения качества со старым сигнал-каналом MEXC **не делать ложное сравнение исполнения**: если MEXC не подключён, сигнал канала можно использовать как рыночный ориентир/исторический пример, но точно такой же маршрут по Bybit/BingX может не существовать.

### 18.8. Порядок работы агента прямо сейчас

1. **Не начинать новый проект ещё раз** и не удалять уже сделанное в текущем `arbitrage-os-v2`.
2. Прочитать единое мастер-ТЗ v1.3 и зафиксировать согласованные изменения в `docs/requirements_v1_3.md`.
3. Проверить, что действующая конфигурация активных CEX — только Bybit и BingX.
4. Закончить и доказательно проверить 1A, затем **обязательно** выполнить 1B с тремя приоритетными DEX-сетями до объявления «мощный сканер готов».
5. Единые измеримые отчёты: количество инструментов, пулов, покрытие, задержки, точность сопоставления, доля quote-success, причины блокировок, затраты инфраструктуры.
6. Ни одного реального ордера без отдельного утверждения владельца после PAPER-валидации.

### 18.9. Проверочные технические источники (актуализировать перед интеграцией)

- Bybit V5 catalog and pagination: https://bybit-exchange.github.io/docs/v5/market/instrument
- Bybit public orderbook delta rules: https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook
- BingX Swap market WebSocket: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-ws-market/api-reference.md
- BingX contracts/depth/funding endpoints: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-market/api-reference.md
- DEX Screener discovery and rate limits: https://docs.dexscreener.com/api/reference
- 0x Swap indicative price and quote: https://docs.0x.org/docs/introduction/quickstart/swap-tokens-with-0x-swap-api
- 0x supported chains: https://docs.0x.org/docs/introduction/supported-chains


## 19. Системный реестр подводных камней: обязательные gate-проверки

**Это проверяемые условия отказа/остановки. Ни одна проверка не может быть снята для увеличения числа «сделок».** Каждой проверке соответствуют детерминированный reason code, тест и счётчик отказов. Инциденты различать как `scanner_data_issue`, `economic_not_eligible`, `trade_execution_risk`, `infrastructure_outage`, а не сводить к одному `NO_SIGNALS`.

### 19.1. Качество потока и реальная скорость

- **Bybit и BingX имеют разные частоты push.** Не требовать единого физического интервала/«200 мс на все токены»: у BingX некоторые глубины обновляются реже, чем у Bybit. Сохранять `exchange_ts`, `recv_ts`, `normalized_ts`, `eval_ts`, `clock_offset_ms`, freshness TTL и отдельно объяснять задержку провайдера, сети и собственного кода.
- В BingX изучить конкретную версию официального WebSocket (GZIP/Ping/Pong, topics, лимиты; `bookTicker`/`depth` могут иметь разные semantics). **Не считать `lastPrice`, `markPrice`, `indexPrice` заменой исполнимых bid/ask.**
- Для Bybit `orderbook.1` — snapshot, у других глубин delta; корректно сбрасывать и восстанавливать стакан, сохранять и валидировать `u`/`seq` по спецификации **именно выбранной темы**. Обнаруженный gap → `STALE_ORDERBOOK` и запрет `EXECUTABLE` до resync.
- Для рынка без обновлений heartbeat ≠ свежая котировка; проверять exchange/source timestamp и границы приемлемой задержки. Учитывать рассинхрон часов сервера с биржей через NTP/clock-offset; если временные метки невалидны → `INVALID_MARKET_TIME`.
- На первом этапе сделать `venue_capabilities_report` на живых источниках: доступность URL/API из региона размещения, количество контрактов, частота, лимиты, запреты, ошибки, реальная доля coverage. Не угадывать возможности по устаревшей библиотеке.

### 19.2. Одноимённые токены и несовместимые контракты

- `same_symbol != same_underlying`. Обязательная проверка `instrument_type`, `underlying_asset_id`, chain/token для DEX, `multiplier`, `settle_asset`, margin mode, `1000*`-маркировки, сроков и торгового статуса. При недостатке доказательств — `UNVERIFIED_ASSET_IDENTITY`.
- Проверять единицы объёма: количество лотов, контрактов, монет и USDT — разные величины. Округлять ВНИЗ до разрешённого step, затем пересчитывать реальную экспозицию обеих ног и остаточный delta-risk. Ошибка шага не должна увеличивать позицию.
- Учитывать USDT/USDC/другие расчётные валюты, валютный риск, разные индексы цены, возможные премии и разные механизмы funding, иначе видимый спред несопоставим.

### 19.3. Исполнимость, а не красивый процент

- По каждому маршруту рассчитывать минимум 3 размера ордера, настраиваемых пользователем (пример: $50/$100/$250), и показывать реальный executable VWAP и **максимальную исполнимую сумму** при лимите проскальзывания. Если средств на нужных площадках нет — кандидат может оставаться рыночным, но `EXECUTABLE_FOR_THIS_ACCOUNT=false`.
- `raw_spread` считать по best ask/bid, но итог — только от клиринга двух ног, с учётом четырёх taker/maker fee legs, входного и выходного impact, funding и risk buffer. Указывать сценарий закрытия, срок и порог выхода отдельно от текущей нереализованной прибыли.
- Не использовать `mark`/`last` для моделирования реального fill; для PAPER — актуальные bid/ask и рассчитанная глубина, вероятностные partial fills без подделки исторических событий.
- Нельзя симулировать «ноль убытков» при отсутствующем стакане. Stale/incomplete books → нельзя подтверждать вход, выходная оценка имеет статус `UNKNOWN`, риск продолжает учитываться.
- Сигнал с raw spread 5% может иметь отрицательную чистую экономику и отрицательный ожидаемый PnL. Порог 5% — только **настраиваемый фильтр сигналов, а не условие гарантированного входа**.

### 19.4. DEX: наличие токена не означает, что он продаваемый

- Проверить buy **и sell** на одну и ту же реальную базовую сумму, независимо от сигнальной цены из пула. Honeypot, sell-only/buy-only guards, transfer tax, fee-on-transfer, rebasing, permit/blacklist, pausable, proxy upgradeability, mint, owner privileges, owner withdrawal of liquidity — отдельные risk flags.
- **DEX Spot нельзя SHORT без актива/заимствования.** Для DEX Spot + CEX Futures первый реально допустимый маршрут: `BUY DEX spot + SHORT CEX perp`; обратный разрешён только при проверенном готовом запасе токенов и корректном рисковом учёте.
- Для pool discovery: `chainId + poolAddress` уникальный ключ; для underlying: `chainId + tokenAddress` и *подтверждённая* связь с биржевым инструментом, а не общий тикер. Stablecoin peg/depeg и wrapped/bridged версии отдельно.
- DEX-транзакции: approvals, nonce management, signer policies, deadline, deadline expiry, replacement tx, dropped/failed/reverted tx, chain reorg, confirmations/finality, RPC quorum (если доступен), MEV/front-run, slippage cap, gas cap; подтверждать исполнение только on-chain receipt/logs и изменения фактических балансов.
- Для 0x API не разрешать allowance для неподходящего spender: approval только по официальным `allowanceTarget`/`issues.allowance.spender` для AllowanceHolder/Permit2; не разрешать Settler как spender. Бесконечные разрешения по умолчанию запрещены. Секретный ключ/seed никогда не хранить в репозитории.
- «Firm quote» снижает неопределённость цены, **но не делает on-chain исполнение гарантированным**. Буфер газа, TTL quote и риск между DEX swap и hedge обязательны.

### 19.5. Переводной арбитраж — отдельная экономика

- До действия проверять `withdraw_enabled`, `deposit_enabled`, адрес и memo/tag, сеть, минимальную сумму зачисления, подтверждения, fees, лимиты, withdrawal risk, address allowlist, token contract. Криптовалюта одной маркировки в разных сетях необязательно взаимозаменяема.
- `buy → transfer → sell` — **незахеджированная последовательность**; нельзя фиксировать прибыль по bid, который был до отправки. После зачисления делать новую исполнимую оценку продажи, учитывать риски цены за время пути.
- Если используются заранее распределённые балансы (B4), одновременный BUY/SELL возможен только при наличии нужного актива в месте продажи и средств в месте покупки; итоговая экономика включает стоимость будущей ребалансировки запасов, иначе стратегия постепенно перестанет работать.
- Во время `PENDING_WITHDRAWAL`/`PENDING_DEPOSIT`/`PENDING_CONFIRMATIONS` бот обязан знать местонахождение денег и запретить повторный перевод. При неизвестном статусе — `RECOVERY_REQUIRED`, не отправлять заново автоматически.
- На этапе OBSERVE **никаких API-прав на вывод и никаких приватных кошельковых ключей**. В будущем автоматический вывод средств — отдельная, повышенно опасная функция с персональным подтверждением и лимитами; нельзя считать её обычной частью первого LIVE.

### 19.6. Маржа, ликвидации и биржевые режимы

- Учитывать отдельные балансы Bybit/BingX, позиции и collateral, margin mode (isolated/cross), position mode (one-way/hedge), min notional, tick/step, reduce-only, price bands, max orders, funding timestamp, leverage limits, liquidation buffer, ADL/forced close, API ability to close. Использовать фактическое состояние аккаунта перед PAPER/LIVE планированием.
- Межбиржевой хедж не защищает от **ликвидации одной из ног**, даже если суммарный PnL выглядит почти нулевым. Размер каждой ноги и маржи проверять раздельно. Cross margin может пострадать от других позиций аккаунта.
- Ключи и trading permissions: на стадии сканера только публичные endpoints. До LIVE — сначала read-only API, затем отдельный live gate. API withdraw запрещено по умолчанию, IP whitelist и минимум полномочий обязательны. Проверять региональные/юридические ограничения площадок, не обходить их.

### 19.7. Нельзя повторять ордер после сетевой ошибки

- У каждого плана: stable `plan_id`, `client_order_id` / idempotency key, event sourcing of actions, outbox/worker lease, monotonic state transitions. На timeout после `POST order` бот **не знает**, что ордер не выполнен: сперва query by order ID + orders + positions + fills, лишь затем принимать решение.
- Если одна нога исполнилась, другая нет — видимое состояние `UNHEDGED_EXPOSURE`, лимит времени и остаточной дельты, алгоритм bounded hedge/unwind и kill switch. Отсутствие интернета, lock DB, crash Railway, ошибочный event не повод отправлять дубль.
- Перед восстановлением после перезапуска сделать reconcile с биржей по актуальным orders/positions/trades, не слепо доверять локальной SQLite/Postgres. PAPER рестарт тоже обязан сохранять неизменяемый журнал.
- Защититься от двух одновременно запущенных executors (duplicate replicas, restart overlap): лидерство/DB advisory lock, уникальный plan ID, fenced writes. Один Telegram callback не должен открывать 2 сделки из-за двойного клика.

### 19.8. Нагрузочные пределы, хранение и эксплуатация

- Ограничения WebSocket и HTTP/aggregator: токен-бакеты на конкретные endpoint/IP/account; `429` и server backoff вместо «обхода». Установить бюджет по трафику, RPC calls, индексации пулов, Postgres storage, комиссии за live operations; включать новые источники только при обоснованном покрытии.
- Scanner и executor — **разные сервисы**, падение Telegram UI не останавливает обработку сигналов; устаревшие котировки не уходят в сделки из очереди. bounded buffers, priority tiers, queue lag и dropped-events metrics.
- Postgres хранит позиции, события, решения и журнал **с сохранением на деплое**; сырые тики — в ring buffer/сжатые агрегаты с retention. Миграции с backup/restore drill, контроль диска, размер volume, мониторинг памяти/CPU/network, предупреждение перед отключением.
- Состояния `TRADING_PAUSED`, `DATA_STALE`, `RATE_LIMITED`, `INFRA_DEGRADED`, `ACCOUNT_UNAUTHORIZED` должны быть видны пользователю и раздельно от `NO_MARKET_OPPORTUNITY`. В состоянии аварии запрещены новые входы, но управление/выход по допустимой политике не должны исчезать.
- Заранее определить доминирование watch-only и подключение закрытия: polling только по расписанию и WS, не `O(N²)` запросов. На рынке без сделок всё равно должен быть дневной отчёт о coverage и топ-10 блокировках.

### 19.9. Методология тестирования: правдоподобие важнее «прошёл unit-тест»

- Разделить **REAL-LIVE-MARKET OBSERVE**, **HISTORICAL REPLAY**, **PAPER с реальными текущими котировками** и **LIVE** на уровне кода, базы, логов и Telegram. REPLAY-сигналы не могут попадать в статистику настоящей биржевой доходности.
- Проверять не только успешные кейсы, но и stale book, delayed BingX packet, неверные decimal/multiplier, недоступную ликвидность, DEX honeypot, funding discontinuity, reorg, transfer suspended, price drift, partial hedge, exchange rejected order, order timeout после фактического fill, db failure, restart/duplicate worker, liquidation pressure.
- Отдельно строить `scanner->signal->plan->paper fills->risk monitoring->closure->ledger reconcile->Telegram` с единственным trace ID и доказательными журналами. Показывать точную причину нуля сделок, не искусственно ослаблять риск для красивой статистики.
- Replay обязан воспроизводить не только прибыль и входы, но также **убыток, отсутствие входа, незакрытую позицию, частичное исполнение и перезапуск**; нельзя использовать будущие данные для решения о прошлом (look-ahead bias).

## 20. Обязательные gate-критерии: что считается законченным

### Gate 0 — Основание
- Новый независимый GitHub-репозиторий; только Bybit/BingX CEX. CI/линтер/секреты, Docker, healthchecks, состояние и миграции. Запуск без приватных API-ключей. `OBSERVE`; журнал активной конфигурации.

### Gate 1A — CEX сканер
- Сверка полного текущего `catalog` Bybit/BingX с официальными REST; отчёт denominator/covered/excluded для каждого; все реально совместимые инструменты в обе стороны (без невозможных совпадений).
- Измеренная задержка p50/p95; доля свежих котировок, WS gaps/reconnects/rate limit; хотя бы сутки доступных live наблюдений. Кандидаты реальных рынков и причины отказов. `enabled_venues = [bybit,bingx]` подтверждено по outbound requests и конфигурации.
- При отсутствии выгодного маршрута допускается **0 EXECUTABLE**; обязательно `raw/identity/depth/fees/risk` counters и REPLAY, показывающий исправность логики.

### Gate 1B — Полный СКАНЕР включает DEX
- On-chain discovery (не вручную забитые 3 токена), обновление пула, pool liquidity, независимый source validation для **BNB Chain, Base, Arbitrum**; size-aware buy/sell quotes, gas, chain/status, identity registry к Bybit/BingX perp, минимум один поддерживаемый AMM/route на каждую сеть.
- Чётко раскрыть доступное покрытие: число discovered pools, monitored, candidate, quote success, quote unsupported, stale, token risk. Все обещания «следим за всеми монетами» запрещены без denominator и измеренных ограничений.
- Ethereum mainnet — будущая отдельная задача по итогам газ/RPC бюджета; её отсутствие не мешает Gate 1B при выполнении трёх согласованных сетей.

### Gate 2 — Стратегии и PAPER A1
- Полный deterministic evaluator для A и B с отделением сценариев от реализованных доходов; PAPER A1 раздельный риск маржи, 2 fills, 4 комиссии, funding, unhedged handling, exit/reconcile; настройка из Telegram, ручной/автоматический режим.
- Серия replay profit/loss/partial/unwind/restart и реальный market read-only mode. Нельзя объявить LIVE-ready только потому, что тесты зелёные.

### Gate 3 — PAPER все маршруты
- PAPER A1/A2/A3/B и переводные сценарии с динамическим bid/ask/DEX quotes, pending/confirmations, журнал, отдельно каждая позиция в Telegram. Run ≥72 часа с настоящими котировками, честные результаты и причины нуля.
- Для каждого поддерживаемого маршрута показать минимум один **контролируемый REPLAY полный цикл**, не фальсифицируя текущие реальные сигналы. Отсутствие выгодного спреда не вынуждает бота делать минусовые сделки.

### Gate LIVE (НЕ входит в текущий проект)
- Отдельный будущий аудит ключей, региональных ограничений, прав, маржи, recovery и внешняя приемка. По умолчанию `LIVE_ENABLED=false`, подпись запрета распространяется на каждую адаптерную операцию. Даже PAPER GUI никогда не может случайно вызвать live endpoint.

## 21. Чёткие требования к отчётам, бюджету и решениям владельца

1. **Открытый список ограничений** — еженедельная матрица известных проблем, риска, вероятности, владельца решения и того, что мешает принять этап. Никогда не заявлять «без ошибок» без данных.
2. **Еженедельное качество сигналов:** `instruments_total`, `compatible_pairs`, `fresh_quote_coverage`, `raw_signals`, `size_quote_verified`, `net_eligible`, `live_tradeable_for_account`, `rejected_by_reason`, `scanner_latency_p95`, `pools_covered_by_chain`.
3. **Затраты:** расходы инфраструктуры + RPC/aggregator requests, 80/95-percentile usage, оценка добавления каждой сети. Не подключать коммерческий провайдер без разрешения владельца.
4. **Изменение скоупа:** новую CEX, стратегию, сеть, торговый риск, права на вывод или расходный сервис добавлять только как отдельную согласованную задачу. Не заменять неработающий BingX на Binance автоматически.
5. **Признак серьёзного сканера:** покрытие и частота подтверждены реальными потоками; если рынок не даёт прибыльных возможностей, это отражено как факт, а не «сканер сломан» и не повод рисовать фальшивую прибыль.
6. **Главная граница:** нет доказательства текущей исполнимости, ликвидности, совпадения актива, состояния API и бюджетного риска → `WATCH_ONLY` / `REJECTED`, а не `EXECUTABLE`.

## 22. Официальные источники для разработчика — сверять актуальность API

- Bybit V5 orderbook snapshot / delta: https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook
- Bybit V5 instrument listing: https://bybit-exchange.github.io/docs/v5/market/instrument
- BingX Swap WS reference: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-ws-market/api-reference.md
- BingX Swap REST contract, fees/funding/markets: https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-market/api-reference.md
- BingX Swap trading requirements (не использовать до этапа исполнения): https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-trade/api-reference.md
- 0x Swap API quote and required API key: https://docs.0x.org/docs/introduction/quickstart/swap-tokens-with-0x-swap-api
- 0x official allowance rules: https://docs.0x.org/docs/core-concepts/contracts
- Uniswap V3 fee-on-transfer/rebasing caveats: https://developers.uniswap.org/docs/protocols/v3/concepts/unsupported-tokens
- DEX Screener API is supplementary discovery: https://docs.dexscreener.com/api/reference
