"""Check Splento for sessions in Denmark that need a photographer, and send
new ones to Telegram.

Settings come from environment variables (GitHub Actions secrets):
  SPLENTO_USERNAME, SPLENTO_PASSWORD, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

Testing without logging in or sending anything:
  python watcher.py --html saved_page.html --dry-run
"""

import argparse
import datetime
import html
import json
import os
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup

BASE_URL = "https://newadmin.splento.com"
STATE_FILE = Path(__file__).with_name("seen.json")
DENMARK = re.compile(r"(,\s*DK\s*$)|\b(Denmark|Danmark)\b", re.IGNORECASE)


def env(name: str) -> str:
    # Secrets pasted into GitHub often pick up a stray space or line break.
    return os.environ[name].strip()


def fetch_dashboard(username: str, password: str) -> str:
    s = requests.Session()
    s.headers["User-Agent"] = "Mozilla/5.0 (splento-watcher)"
    login_page = s.get(f"{BASE_URL}/login", timeout=30)
    login_page.raise_for_status()
    token = BeautifulSoup(login_page.text, "html.parser").find("input", {"name": "_token"})
    if token is None:
        raise RuntimeError("Login form not found (did the Splento login page change?)")
    r = s.post(
        f"{BASE_URL}/login",
        data={"_token": token["value"], "username": username, "password": password},
        timeout=30,
    )
    r.raise_for_status()
    dashboard = s.get(f"{BASE_URL}/", timeout=30)
    dashboard.raise_for_status()
    if 'data-id="awaitingPhotographers"' not in dashboard.text:
        raise RuntimeError("Login failed or the dashboard changed: 'Sessions awaiting photographers' not found")
    return dashboard.text


def parse_sessions(page: str) -> list[dict]:
    soup = BeautifulSoup(page, "html.parser")
    panel = soup.find("section", {"data-id": "awaitingPhotographers"})
    if panel is None:
        raise RuntimeError("'Sessions awaiting photographers' panel not found")
    sessions = []
    for li in panel.find_all("li"):
        link = li.find("a", href=True)
        if link is None:
            continue
        date = li.find(class_="dashboardPanelDate")
        small = li.find("small")
        address = ""
        if small:
            # The address is the text between the map marker and the next <br>.
            lines = [t.strip() for t in small.get_text("\n").split("\n") if t.strip()]
            address = lines[0] if lines else ""
        sessions.append({
            "id": link["href"].rstrip("/").split("/")[-1],
            "title": link.get_text(" ", strip=True),
            "date": date.get_text(strip=True) if date else "",
            "address": address,
            "url": link["href"],
        })
    return sessions


def is_denmark(session: dict) -> bool:
    return bool(DENMARK.search(session["address"]) or DENMARK.search(session["title"]))


def load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return {"open_ids": [], "updated": ""}


def save_state(open_ids: list[str]) -> None:
    # "updated" changes at most once a day, so the repo gets a commit at least
    # daily and GitHub doesn't pause the schedule for inactivity.
    state = {"open_ids": sorted(open_ids), "updated": datetime.date.today().isoformat()}
    STATE_FILE.write_text(json.dumps(state, indent=2) + "\n")


def format_message(new: list[dict]) -> str:
    header = "📸 <b>New Splento job in Denmark</b>" if len(new) == 1 else f"📸 <b>{len(new)} new Splento jobs in Denmark</b>"
    parts = [header]
    for s in new:
        parts.append(
            f'\n<a href="{html.escape(s["url"])}">{html.escape(s["title"])}</a>\n'
            f'🗓 {html.escape(s["date"])}\n'
            f'📍 {html.escape(s["address"])}'
        )
    return "\n".join(parts)


def send_telegram(token: str, chat_id: str, text: str) -> None:
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text, "parse_mode": "HTML", "disable_web_page_preview": True},
        timeout=30,
    )
    if not r.ok:
        raise RuntimeError(f"Telegram error {r.status_code}: {r.text}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="read the dashboard from a saved HTML file instead of logging in")
    ap.add_argument("--dry-run", action="store_true", help="print the message instead of sending it, and don't save state")
    ap.add_argument("--test-message", action="store_true", help="send a test message to Telegram and exit")
    args = ap.parse_args()

    if args.test_message:
        send_telegram(env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID"),
                      "✅ Splento watcher is connected. You'll get a message here when a Denmark job appears.")
        print("Test message sent.")
        return 0

    if args.html:
        page = Path(args.html).read_text(encoding="utf-8")
    else:
        page = fetch_dashboard(env("SPLENTO_USERNAME"), env("SPLENTO_PASSWORD"))

    sessions = parse_sessions(page)
    dk = [s for s in sessions if is_denmark(s)]
    previous = set(load_state()["open_ids"])
    # A job that disappears and later comes back (e.g. a photographer dropped
    # out) counts as new again.
    new = [s for s in dk if s["id"] not in previous]

    # Only counts are printed: Actions logs may be public.
    print(f"Awaiting photographers: {len(sessions)} total, {len(dk)} in Denmark, {len(new)} new")

    if new:
        message = format_message(new)
        if args.dry_run:
            print("--- message ---\n" + message)
        else:
            send_telegram(env("TELEGRAM_BOT_TOKEN"), env("TELEGRAM_CHAT_ID"), message)

    if not args.dry_run:
        save_state([s["id"] for s in dk])
    return 0


if __name__ == "__main__":
    sys.exit(main())
