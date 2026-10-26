# Официальные источники и capabilities · 26.10.2026

| Venue | Catalog | Best bid/ask WS | Depth WS | Fees/funding | Private/order/withdraw |
|---|---|---|---|---|---|
| Bybit | V5 linear с cursor | tickers.symbol, snapshot/delta | orderbook.50.symbol | public non-VIP fee, ticker funding + catalog interval | NOT_IMPLEMENTED |
| BingX | swap/v2/quote/contracts | symbol@bookTicker, GZIP/Ping | symbol@depth50@500ms | contract takerFeeRate, premiumIndex, shortlist funding history | NOT_IMPLEMENTED |

Документированная поддержка не означает доступность в этом окружении. Фактический статус — в STATUS.md и evidence.

- https://bybit-exchange.github.io/docs/v5/market/instrument
- https://bybit-exchange.github.io/docs/v5/websocket/public/ticker
- https://bybit-exchange.github.io/docs/v5/websocket/public/orderbook
- https://www.bybit.com/en/help-center/article/Trading-Fee-Structure
- https://www.bybit.com/en/help-center/article/FAQ-USDT-Perpetual-and-Expiry-Contracts
- https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-ws-market/api-reference.md
- https://github.com/BingX-API/api-ai-skills/blob/main/skills/swap-market/api-reference.md

Для BingX используются консервативные шардирование 40 символов/соединение и 0.15 s между subscribe. Фактический полный bookTicker universe проверен; утверждение об официальном максимуме подписок/соединений без опубликованного доказательства не делается.

У публичной комиссии Bybit возможны региональные/аккаунтные отличия, поэтому сигнал несёт PUBLIC_NON_VIP_SCHEDULE, не ACCOUNT_VERIFIED.
