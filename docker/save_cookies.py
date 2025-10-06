"""Helper script to trigger the manual Weibo login flow and persist cookies."""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

from chatbot.utils.config import Config
from chatbot.weibo.monitor import WeiboMonitor


async def main() -> None:
    config = Config()
    dummy_db = SimpleNamespace(sqlite_db=None)
    monitor = WeiboMonitor(config, dummy_db, ai_handler=None)

    success = await monitor.wait_for_login()
    if not success:
        raise SystemExit("Login was not completed in time. Please retry.")

    cookies_dir = Path("/app/cookies")
    cookies_dir.mkdir(parents=True, exist_ok=True)
    cookie_file = cookies_dir / "weibo_cookies.json"
    cookie_file.write_text(json.dumps(monitor.cookies, ensure_ascii=False, indent=2))
    print(f"Saved cookies to {cookie_file}")


if __name__ == "__main__":
    asyncio.run(main())
