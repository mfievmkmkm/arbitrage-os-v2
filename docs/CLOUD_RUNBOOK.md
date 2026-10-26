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


## Исторически: первоначально предложенная конфигурация Railway

План: `configs/deployment/railway-observe-plan.json`. Это описание для операций через Railway MCP,
а не автоматически применяемый railway.json/terraform import. Новые legacy railway.json не
добавлялись: официальная документация помечает Config as Code deprecated.

Проверен подключённый workspace. Попытка создать отдельный `arbitrage-os-v2` отклонена Railway:
`Free plan resource provision limit exceeded. Please upgrade to provision more resources!`
Повторная инвентаризация подтвердила: проекта нет, staged resources/containers/volumes не создавались.
Старые `soothing-flow` и `humble-success` не менялись. У последних workloads регион
`europe-west4-drams3a`; он записан только как предложение постоянного размещения, не proxy/fallback.
Доступ Bybit из будущего runtime пока НЕ ПРОВЕРЕН и не обещается.

Подготовлены scanner (0.75 vCPU, 0.5 GB RAM), отдельный Postgres 16 (0.25 vCPU, 0.25 GB RAM),
2 GB volume, private DB connection, pinned проверенный runtime commit f5fc31b, /health,
1 replica, OBSERVE, только bybit/bingx. Новые секреты будут сгенерированы только при разрешённом
развёртывании и записаны защищёнными переменными; в плане их нет. Trading keys не нужны.

Тарифы проверены по https://docs.railway.com/pricing/plans:
Hobby $5/month с $5 included usage; RAM $10/GB/month, CPU $20/vCPU/month,
storage $0.15/GB/month, egress $0.05/GB. При непрерывном использовании всех предложенных CPU/RAM
лимитов: 1 vCPU * $20 + 0.75 GB * $10 + 2 GB * $0.15 = примерно $27.80/month до egress.
Реальный счёт определяется фактическим потреблением и действующим планом, не суммой RAM caps.
Это не установленный billing hard limit. Глобальный workspace лимит не менялся, чтобы не
повлиять на старые services. Стоимость прежних ресурсов не включена.

До платного запуска владелец должен согласовать тариф/бюджет по §14 MASTER_SPEC.
Апгрейд, платежи, accept-deploy и provisioning без такого разрешения не выполнялись.
После согласования agent создаёт отдельный project, stage services/source/env/volume,
сверяет весь patch, затем запускает уже разрешённое развёртывание и проверяет фактический результат.


## Применённый запуск на Free · 27.10.2026

Первоначальный план выше заменён конфигурацией APPLIED_DEPLOYMENT_RECORD в
`configs/deployment/railway-observe-plan.json`. После разрешённого удаления старых services и
volumes используем очищенный `humble-success` / production. Пустые projects сохранены; попытка
нового project всё ещё отклоняется, а создание services внутри существующего прошло успешно.

Scanner и Postgres: terminal SUCCESS, одна running replica каждого. Scanner root Dockerfile,
commit f5fc31b, /health; DB postgres:16-alpine, private postgres hostname, без public domain/TCP.
Limits scanner 0.75 vCPU/0.5 GB; DB 0.25 vCPU/0.25 GB; новый persistent volume 500 MB.
Сгенерированы CONTROL_TOKEN и POSTGRES_PASSWORD; значения не публикуются. Telegram не подключён.

Проверены /health, /ready, /status, /markets, /quotes, /signals, /history. Реальные каталоги и
потоки обеих бирж получены. История старого процесса доступна после restart scanner. DB в облаке
не перезапускалась. Evidence: `docs/evidence/railway-2026-10-27.json`.

Free включает $1 usage/month по официальным docs; подписка не повышалась, платёж не выполнялся.
Нет обещания беспрерывного месяца: это зависит от остатка credit и реального расхода. 500 MB
не являются доказательством ёмкости на 24 часа: отдельно нужны контроль заполнения/роста БД и
согласование увеличения, если потребуется. Автоматическое стирание истории не включалось.
Любой переход на платный план всё ещё требует отдельного согласования владельцем.

Следующий блокер 1A: evidence-backed identity registry, полнота/свежесть обоих потоков, покрытие
funding/depth, восстановление WS и ≥24h фактического наблюдения. /ready=true обозначает лишь
техническое OBSERVATION_ONLY + подключённый durable journal, не приёмку Gate 1A. Затем обязателен 1B.
