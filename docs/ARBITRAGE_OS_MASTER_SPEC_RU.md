# ARBITRAGE OS — мастер-ТЗ для нового проекта

**Версия:** 1.1 · 26 октября 2026 года · старт только Bybit + BingX  
**Цель:** с нуля построить самостоятельный профессиональный сканер межбиржевых арбитражных возможностей, затем независимый торговый движок с двумя стратегиями и доказуемо корректным виртуальным/реальным исполнением.  
**Язык интерфейса:** русский. **Режим первой разработки:** MARKET OBSERVE → PAPER MANUAL → PAPER AUTO; все LIVE-операции запрещены до отдельной приёмки и разрешения владельца.

> Это обязательный документ для команды/агента-разработчика. Не переносить ошибочную архитектуру предыдущего бота. Использовать старые исходники только для аудита прошлых ошибок и примеров, не как основу нового приложения. Проектировать итерационно с доказуемыми результатами. «Много сигналов» не равно «много прибыльных сделок».

## Приоритетное решение владельца от 26.10.2026 — ОБЯЗАТЕЛЬНО

**Весь текущий стартовый охват CEX ограничен ровно двумя биржами: Bybit и BingX.** Это относится к Stage 0/1A, дальнейшей разработке Spot/Futures, подключению приватных API и PAPER-исполнению, пока владелец явно не изменит решение.

- `ENABLED_CEX_VENUES = ["bybit", "bingx"]` — исходная конфигурация; никаких иных подключённых CEX.
- **Binance не подключать сейчас вообще.** Не создавать Binance WebSocket/REST-сессии, не загружать Binance-каталог, не получать Binance-котировки, не включать Binance в сканирование, тестовую готовность или торговый цикл. Binance может рассматриваться только как потенциальное будущее расширение по отдельной команде владельца.
- **MEXC, OKX, Gate.io, Bitget и остальные CEX тоже не подключать на текущем этапе.** Даже если в тексте встречаются названия других бирж, они служат примерами будущего расширения или историческими референсами каналов, но НЕ разрешением на подключение.
- Первая исполняемая стратегия-сканер — **A1 Futures/Futures исключительно между Bybit и BingX**, в обоих направлениях: `LONG Bybit / SHORT BingX` и `LONG BingX / SHORT Bybit`.
- Использовать только действительно общие и совместимые фьючерсные инструменты Bybit и BingX; уникальные монеты одной площадки учитываются в её каталоге, но не создают фиктивную арбитражную пару.
- Для дальнейших A2/B1/B4 использовать Spot/Futures **тех же Bybit и BingX**, когда будет подтверждена соответствующая поддержка. DEX-пулы и независимый on-chain мониторинг — отдельный будущий этап, не третья CEX.
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

**На текущем этапе подключаем только Bybit и BingX.** В этапе 1A — только их USDT-settled линейные бессрочные Futures, с проверкой полной реально доступной номенклатуры контрактов. В будущих этапах — Spot этих же двух бирж и DEX-источники по отдельной готовности. Binance, MEXC, OKX, Gate.io, Bitget и другие CEX не инициировать и не включать без нового решения владельца. Архитектура адаптеров должна позволять позже добавить биржу без переписывания стратегии. DEX после согласования: сначала EVM BSC и Ethereum (по одному основному AMM/агрегатору с измеряемым доступом), далее Base/Arbitrum, только затем Solana, TON и прочие сети.

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
- Реестр chain/token address and pools, BSC+Ethereum DEX/aggregator на конфигурируемом токеновом universe из совпадений с CEX; native pool updates, firm quote preflight для top candidates и A3/B2/B3 discovery.
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
