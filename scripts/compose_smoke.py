"""Real Docker/Postgres acceptance, executed by CI or owner, never mocked."""

import json
import subprocess
import time
import urllib.request


def docker(*args):
    return subprocess.check_output(["docker", "compose", *args], text=True)


def wait_health():
    deadline = time.monotonic() + 90
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=3) as response:
                if json.load(response).get("alive"):
                    return
        except (OSError, ValueError):
            pass
        time.sleep(1)
    raise RuntimeError("Scanner health did not recover")


def main():
    wait_health()
    code = """import asyncio,os,json
from infrastructure.journal import Journal
async def run():
 j=Journal(os.environ["DATABASE_URL"])
 await j.connect()
 j.append({"id":"COMPOSE_DURABILITY_PROBE","asset":"TEST","stage":"BLOCKED",
           "data_mode":"INTEGRATION_TEST","rejection_codes":[]})
 stop=asyncio.Event();stop.set()
 await j.run(stop)
 await j.close()
asyncio.run(run())"""
    docker("exec", "-T", "scanner", "python", "-c", code)
    docker("restart", "postgres", "scanner")
    wait_health()
    verify = """import asyncio,os,json
from infrastructure.journal import Journal
async def run():
 j=Journal(os.environ["DATABASE_URL"])
 await j.connect()
 rows=await j.history(200)
 assert any(r["id"]=="COMPOSE_DURABILITY_PROBE" for r in rows)
 await j.close()
 print(json.dumps({"postgres_restart_persistence":True,"mode":"INTEGRATION_TEST"}))
asyncio.run(run())"""
    print(docker("exec", "-T", "scanner", "python", "-c", verify))
    with urllib.request.urlopen("http://127.0.0.1:8080/status", timeout=5) as response:
        status = json.load(response)
    assert status["mode"] == "OBSERVE" and not status["live_enabled"]
    assert status["active_venues"] == ["bybit", "bingx"]
    assert status["journal"]["durable"]
    print(json.dumps({"docker_health": True, "journal_durable": True, "trading": "DISABLED"}))


if __name__ == "__main__":
    main()
