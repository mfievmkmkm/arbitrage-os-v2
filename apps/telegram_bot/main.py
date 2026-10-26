"""Separate read-only Telegram control process. Scanner never imports Telegram."""

import asyncio
import html
import json
import os

from aiohttp import ClientSession

from core.reasons import explain

MENU = {
    "scanner": "🔎 Сканер",
    "raw": "Сырые спреды",
    "verified": "Проверенные",
    "waiting": "Ожидают данных",
    "rejected": "Почему отказ",
    "history": "История",
    "diagnostics": "🩺 Диагностика",
    "settings": "⚙️ Настройки",
}


def keyboard(back=False):
    if back:
        return {
            "inline_keyboard": [
                [{"text": "Обновить", "callback_data": "refresh"}, {"text": "Назад", "callback_data": "home"}]
            ]
        }
    return {"inline_keyboard": [[{"text": text, "callback_data": key}] for key, text in MENU.items()]}


def render(section, status, signals=None):
    if section in ("raw", "verified", "waiting", "rejected"):
        lines = [MENU[section] + " · OBSERVE"]
        selected = signals or []
        if section == "verified":
            selected = [x for x in selected if x["stage"] == "VERIFIED"]
        if section in ("waiting", "rejected"):
            selected = [x for x in selected if x["rejection_codes"]]
        for s in selected[:8]:
            lines += [
                f"{s['asset']} · {s['raw_spread_pct']:.3f}%",
                f"LONG {s['cheap']} → SHORT {s['expensive']}",
                f"Сейчас NET: {s['immediate_round_trip_net_usd'] or 'нет данных'}",
                f"При целевом сжатии: {s['scenario_net_at_target_basis_usd'] or 'нет данных'}",
                "; ".join(explain(code) for code in s["rejection_codes"]) or "VERIFIED · только наблюдение",
            ]
        return "\n".join(lines) if selected else lines[0] + "\nНет актуальных кандидатов."
    if section == "settings":
        return (
            "⚙️ OBSERVE\nЧисловой ввод: /size 100, /spread 0.1, /net 0.5\n"
            "Размер — USD на ногу. Изменения сохраняются в PostgreSQL.\n"
            "LIVE и PAPER недоступны на этом этапе."
        )
    lines = ["🤖 ARBITRAGE OS · OBSERVE", "Биржи: Bybit, BingX"]
    for v, h in status["coverage"].items():
        lines.append(
            f"{v}: {h['status']} · свежих {h['fresh_quotes']}/{h['active']}"
            f" · обнаружено {h['discovered']} · идентифицировано {h['identified']}"
        )
    lines += [
        f"Сырые: {status['raw_current']} · проверенные: {status['verified_current']}",
        f"p95 обработки: {status['latency_ms']['p95']} мс",
        "PAPER входы/выходы: 0/0 · LIVE OFF",
    ]
    if section == "diagnostics":
        lines.append(json.dumps(status["metrics"], ensure_ascii=False))
        for v, h in status["coverage"].items():
            if h.get("last_error"):
                lines.append(v + ": " + h["last_error"])
    return "\n".join(lines)


async def run():
    token = os.environ["TELEGRAM_BOT_TOKEN"]
    owner = int(os.environ["TELEGRAM_OWNER_ID"])
    base = os.getenv("SCANNER_URL", "http://scanner:8080").rstrip("/")
    offset, sections = 0, {}
    async with ClientSession(trust_env=True) as session:

        async def tg(method, payload):
            # Never log response URLs or exceptions: URLs contain the bot token.
            async with session.post(
                f"https://api.telegram.org/bot{token}/{method}", json=payload, timeout=40
            ) as r:
                return await r.json()

        async def get(path):
            async with session.get(base + path, timeout=5) as r:
                r.raise_for_status()
                return await r.json()

        while True:
            try:
                updates = await tg(
                    "getUpdates",
                    {"offset": offset, "timeout": 25, "allowed_updates": ["message", "callback_query"]},
                )
                for u in updates.get("result", []):
                    offset = u["update_id"] + 1
                    callback = u.get("callback_query")
                    message = callback["message"] if callback else u.get("message", {})
                    sender = callback["from"]["id"] if callback else message.get("from", {}).get("id")
                    if sender != owner or message.get("chat", {}).get("id") != owner:
                        continue
                    chat = message["chat"]["id"]
                    section = callback.get("data", "home") if callback else "home"
                    if section == "refresh":
                        section = sections.get(chat, "home")
                    sections[chat] = section
                    text = message.get("text", "") if not callback else ""
                    if text.startswith(("/size ", "/spread ", "/net ")):
                        cmd, value = text.split(maxsplit=1)
                        field = {"/size": "size", "/spread": "min_spread_pct", "/net": "min_net"}[cmd]
                        async with session.patch(
                            base + "/settings",
                            json={field: value},
                            headers={"Authorization": "Bearer " + os.getenv("CONTROL_TOKEN", "")},
                            timeout=5,
                        ) as r:
                            reply = "Сохранено" if r.status == 200 else "Не сохранено: проверьте число и БД"
                        await tg("sendMessage", {"chat_id": chat, "text": reply})
                        continue
                    status = await get("/status")
                    signals = (
                        await get("/signals") if section in ("raw", "verified", "waiting", "rejected") else []
                    )
                    content = render(section, status, signals)
                    if section == "history":
                        history = await get("/history")
                        content = "История последних событий\n" + "\n".join(
                            f"{x['asset']}: {x['stage']} · {', '.join(x['rejection_codes'])}"
                            for x in history[:15]
                        )
                    content = html.escape(content)
                    first, sep, remainder = content.partition("\n")
                    content = "<b>" + first + "</b>" + sep + remainder
                    payload = {
                        "chat_id": chat,
                        "text": content[:4000],
                        "parse_mode": "HTML",
                        "reply_markup": keyboard(section != "home"),
                    }
                    if callback:
                        await tg("answerCallbackQuery", {"callback_query_id": callback["id"]})
                        payload["message_id"] = message["message_id"]
                        await tg("editMessageText", payload)
                    else:
                        await tg("sendMessage", payload)
            except asyncio.CancelledError:
                raise
            except Exception:
                print("Telegram/scanner unavailable; retrying (credentials redacted)", flush=True)
                await asyncio.sleep(5)


def main():
    asyncio.run(run())


if __name__ == "__main__":
    main()
