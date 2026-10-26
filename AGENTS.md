# ARBITRAGE OS

Read docs/ARBITRAGE_OS_MASTER_SPEC_RU.md fully and docs/STATUS.md before edits.
Only Bybit and BingX USDT linear perpetual, OBSERVE. No other CEX connections, no order/private API.
Do not modify the old arbitrage-engine. Update dated STATUS and DECISIONS.
Do not turn symbol matching into identity proof. Unknown fees/funding/depth fail closed.
Report real-market evidence separately from synthetic replay/load and tests.
Run `python -m ruff check .` and `python -m pytest` before committing.
Never put credentials, private keys, Telegram tokens or .env in Git or logs.
