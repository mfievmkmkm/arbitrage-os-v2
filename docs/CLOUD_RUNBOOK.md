# Подготовка облачного OBSERVE · требования 1.3

Это runbook, не подтверждение состоявшегося деплоя. Платные сервисы не создавались.

1. Опубликовать существующую историю Git, проверить CI Linux/Windows, Postgres и docker-compose.
2. На разрешённом сервере с Docker выполнить `python scripts/diagnose_public.py` из checkout.
   Если Bybit не отдаёт public V5 JSON/WS, не обходить ограничения, не менять данные другой биржей.
   Требуется выяснить сетевую/региональную доступность совместно с оператором среды.
3. Для отдельного нового scanner deployment подготовить persistent PostgreSQL 16 volume,
   protected DATABASE_URL/CONTROL_TOKEN (либо POSTGRES_PASSWORD для compose), MODE=OBSERVE,
   ENABLED_CEX_VENUES=bybit,bingx. Биржевые ключи и кошелёк не требуются и не принимаются.
4. Docker/compose: `.env` создаёт только владелец по `.env.example`, URL-safe пароль,
   затем `docker compose up -d --build`. Не коммитить .env; API по умолчанию localhost:8080.
5. `/health` — процесс, `/ready` — доступность потоков и durable journal, `/status` — реальное
   покрытие, compatible_pairs, clock uncertainty, queue/drops/latency, outbound public requests.
   PUBLIC_READY не означает ни приёмку Gate 1A, ни готовность аккаунта к торговле.
6. Заполнить доказательный identity registry по обоим официальным каталогам и underlying sources.
   Не снимать gate ради числа сигналов. Провести observation ≥24 h с сохранением истории.
7. Проверить перезапуск scanner/DB и восстановление WS. Сначала тестовый deployment/volume;
   `scripts/compose_smoke.py` пишет явно помеченный INTEGRATION_TEST event для persistence probe.
8. Telegram — отдельный optional service; token и owner ID в protected environment. Отсутствие
   Telegram не должно останавливать scanner. Токен не передавать в Git/логи/чат.
9. Мониторинг: freshness coverage, p95, gaps, reconnects, provider refusals, journal failures,
   Postgres volume usage/backup. Дневник не удалять автоматической очисткой.
10. До приёмки 1A не начинать execution. Следующий обязательный подэтап сканера — Spot Bybit/BingX
    и DEX on-chain discovery/size quotes BNB Chain, Base, Arbitrum. Полный сканер не готов без 1B.

GitHub workflow `Public market observation (read-only)` позволяет получить независимые логи
и artifact после публикации кода. География runner может ограничивать Bybit; workflow не меняет
её автоматически и не обходит запреты. Любой такой отказ — доказательство ограничения этой среды,
а не доказательство несуществования инструмента.
